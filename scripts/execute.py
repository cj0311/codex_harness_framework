#!/usr/bin/env python3
"""
Codex Harness Step Executor.

Runs each phase step in an isolated `codex exec` session, records state in JSON,
and commits completed work step by step.

Usage:
    python scripts/execute.py <phase-dir> [--push]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@contextlib.contextmanager
def progress_indicator(label: str):
    """Terminal progress indicator that exposes elapsed time after completion."""
    frames = "|/-\\"
    stop = threading.Event()
    t0 = time.monotonic()

    def _animate():
        idx = 0
        while not stop.wait(0.12):
            sec = int(time.monotonic() - t0)
            sys.stderr.write(f"\r{frames[idx % len(frames)]} {label} [{sec}s]")
            sys.stderr.flush()
            idx += 1
        sys.stderr.write("\r" + " " * (len(label) + 20) + "\r")
        sys.stderr.flush()

    th = threading.Thread(target=_animate, daemon=True)
    th.start()
    info = types.SimpleNamespace(elapsed=0.0)
    try:
        yield info
    finally:
        stop.set()
        th.join()
        info.elapsed = time.monotonic() - t0


class StepExecutor:
    """Execute step files inside a phase directory with Codex CLI."""

    MAX_RETRIES = 3
    CIRCUIT_BREAKER_THRESHOLD = 3
    FEAT_MSG = "feat({phase}): step {num} - {name}"
    CHORE_MSG = "chore({phase}): step {num} output"
    TZ = timezone(timedelta(hours=9))

    def __init__(self, phase_dir_name: str, *, auto_push: bool = False):
        self._root = str(ROOT)
        self._phases_dir = ROOT / "phases"
        self._phase_dir = self._phases_dir / phase_dir_name
        self._phase_dir_name = phase_dir_name
        self._top_index_file = self._phases_dir / "index.json"
        self._auto_push = auto_push

        if not self._phase_dir.is_dir():
            print(f"ERROR: {self._phase_dir} not found")
            sys.exit(1)

        self._index_file = self._phase_dir / "index.json"
        if not self._index_file.exists():
            print(f"ERROR: {self._index_file} not found")
            sys.exit(1)

        idx = self._read_json(self._index_file)
        self._project = idx.get("project", "project")
        self._phase_name = idx.get("phase", phase_dir_name)
        self._total = len(idx["steps"])

    def run(self):
        self._print_header()
        self._check_blockers()
        self._checkout_branch()
        guardrails = self._load_guardrails()
        self._ensure_created_at()
        self._execute_all_steps(guardrails)
        self._finalize()

    # --- timestamps ---

    def _stamp(self) -> str:
        return datetime.now(self.TZ).strftime("%Y-%m-%dT%H:%M:%S%z")

    # --- JSON I/O ---

    @staticmethod
    def _read_json(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(p: Path, data: dict):
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- git ---

    def _run_git(self, *args) -> subprocess.CompletedProcess:
        cmd = ["git"] + list(args)
        return subprocess.run(cmd, cwd=self._root, capture_output=True, text=True)

    def _branch_name(self) -> str:
        return f"codex/{self._phase_name}"

    def _checkout_branch(self):
        branch = self._branch_name()

        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if r.returncode != 0:
            print("  ERROR: git을 사용할 수 없거나 git repo가 아닙니다.")
            print(f"  {r.stderr.strip()}")
            sys.exit(1)

        if r.stdout.strip() == branch:
            return

        r = self._run_git("rev-parse", "--verify", branch)
        r = self._run_git("checkout", branch) if r.returncode == 0 else self._run_git("checkout", "-b", branch)

        if r.returncode != 0:
            print(f"  ERROR: 브랜치 '{branch}' checkout 실패.")
            print(f"  {r.stderr.strip()}")
            print("  Hint: 변경사항을 stash하거나 commit한 후 다시 시도하세요.")
            sys.exit(1)

        print(f"  Branch: {branch}")

    def _commit_step(self, step_num: int, step_name: str):
        output_rel = f"phases/{self._phase_dir_name}/step{step_num}-output.json"
        index_rel = f"phases/{self._phase_dir_name}/index.json"

        self._run_git("add", "-A")
        self._run_git("reset", "HEAD", "--", output_rel)
        self._run_git("reset", "HEAD", "--", index_rel)

        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.FEAT_MSG.format(phase=self._phase_name, num=step_num, name=step_name)
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  Commit: {msg}")
            else:
                print(f"  WARN: 코드 커밋 실패: {r.stderr.strip()}")

        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = self.CHORE_MSG.format(phase=self._phase_name, num=step_num)
            r = self._run_git("commit", "-m", msg)
            if r.returncode != 0:
                print(f"  WARN: housekeeping 커밋 실패: {r.stderr.strip()}")

    # --- top-level index ---

    def _update_top_index(self, status: str):
        if not self._top_index_file.exists():
            return
        top = self._read_json(self._top_index_file)
        ts = self._stamp()
        for phase in top.get("phases", []):
            if phase.get("dir") == self._phase_dir_name:
                phase["status"] = status
                ts_key = {"completed": "completed_at", "error": "failed_at", "blocked": "blocked_at"}.get(status)
                if ts_key:
                    phase[ts_key] = ts
                break
        self._write_json(self._top_index_file, top)

    # --- guardrails & context ---

    def _load_guardrails(self) -> str:
        sections = []
        agents_md = ROOT / "AGENTS.md"
        if agents_md.exists():
            sections.append(f"## 프로젝트 규칙 (AGENTS.md)\n\n{agents_md.read_text(encoding='utf-8')}")
        docs_dir = ROOT / "docs"
        if docs_dir.is_dir():
            for doc in sorted(docs_dir.glob("*.md")):
                sections.append(f"## {doc.stem}\n\n{doc.read_text(encoding='utf-8')}")
        return "\n\n---\n\n".join(sections) if sections else ""

    @staticmethod
    def _build_step_context(index: dict) -> str:
        lines = [
            f"- Step {s['step']} ({s['name']}): {s['summary']}"
            for s in index["steps"]
            if s["status"] == "completed" and s.get("summary")
        ]
        if not lines:
            return ""
        return "## 이전 Step 산출물\n\n" + "\n".join(lines) + "\n\n"

    def _build_preamble(self, guardrails: str, step_context: str, prev_error: Optional[str] = None) -> str:
        retry_section = ""
        if prev_error:
            retry_section = (
                "\n## 이전 시도 실패\n\n"
                "아래 에러를 먼저 해석하고, 같은 실패를 반복하지 않도록 원인을 수정하라.\n\n"
                f"{prev_error}\n\n---\n\n"
            )
        return (
            f"당신은 {self._project} 프로젝트의 Codex 개발자입니다. 아래 step을 수행하세요.\n\n"
            f"{guardrails}\n\n---\n\n"
            f"{step_context}{retry_section}"
            "## 작업 규칙\n\n"
            "1. 이전 step에서 작성된 코드를 확인하고 일관성을 유지하라.\n"
            "2. 이 step에 명시된 작업만 수행하라. 추가 기능이나 파일을 만들지 마라.\n"
            "3. 새 기능 또는 동작 변경은 테스트를 먼저 작성하거나 같은 변경 안에 테스트를 포함하라.\n"
            "4. 기존 테스트를 깨뜨리지 마라.\n"
            "5. AC(Acceptance Criteria) 검증을 직접 실행하라.\n"
            f"6. /phases/{self._phase_dir_name}/index.json의 해당 step status를 업데이트하라:\n"
            "   - AC 통과 -> \"completed\" + \"summary\" 필드에 이 step의 산출물을 한 줄로 요약\n"
            f"   - {self.MAX_RETRIES}회 수정 시도 후에도 실패 -> \"error\" + \"error_message\" 기록\n"
            "   - 사용자 개입이 필요한 경우 (API 키, 인증, 수동 설정 등) -> \"blocked\" + \"blocked_reason\" 기록 후 즉시 중단\n"
            "7. 커밋은 하지 마라. scripts/execute.py가 step 완료 후 변경사항을 커밋한다.\n\n"
            "---\n\n"
        )

    # --- Codex invocation ---

    def _invoke_codex(self, step: dict, preamble: str) -> dict:
        step_num, step_name = step["step"], step["name"]
        step_file = self._phase_dir / f"step{step_num}.md"

        if not step_file.exists():
            print(f"  ERROR: {step_file} not found")
            sys.exit(1)

        prompt = preamble + step_file.read_text(encoding="utf-8")
        final_message_path = self._phase_dir / f"step{step_num}-final.md"
        cmd = [
            "codex",
            "--ask-for-approval",
            "never",
            "exec",
            "--sandbox",
            "workspace-write",
            "--json",
            "-o",
            str(final_message_path),
            "-",
        ]
        result = subprocess.run(
            cmd,
            input=prompt,
            cwd=self._root,
            capture_output=True,
            text=True,
            timeout=1800,
        )

        if result.returncode != 0:
            print(f"\n  WARN: Codex가 비정상 종료됨 (code {result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")

        final_message = final_message_path.read_text(encoding="utf-8") if final_message_path.exists() else ""
        output = {
            "step": step_num,
            "name": step_name,
            "command": cmd,
            "exitCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "finalMessage": final_message,
        }
        out_path = self._phase_dir / f"step{step_num}-output.json"
        self._write_json(out_path, output)

        return output

    # --- header & validation ---

    def _print_header(self):
        print(f"\n{'=' * 60}")
        print("  Codex Harness Step Executor")
        print(f"  Phase: {self._phase_name} | Steps: {self._total}")
        if self._auto_push:
            print("  Auto-push: enabled")
        print(f"{'=' * 60}")

    def _check_blockers(self):
        index = self._read_json(self._index_file)
        for s in reversed(index["steps"]):
            if s["status"] == "error":
                print(f"\n  Step {s['step']} ({s['name']}) failed.")
                print(f"  Error: {s.get('error_message', 'unknown')}")
                print("  Fix and reset status to 'pending' to retry.")
                sys.exit(1)
            if s["status"] == "blocked":
                print(f"\n  Step {s['step']} ({s['name']}) blocked.")
                print(f"  Reason: {s.get('blocked_reason', 'unknown')}")
                print("  Resolve and reset status to 'pending' to retry.")
                sys.exit(2)
            if s["status"] != "pending":
                break

    def _ensure_created_at(self):
        index = self._read_json(self._index_file)
        if "created_at" not in index:
            index["created_at"] = self._stamp()
            self._write_json(self._index_file, index)

    # --- failure handling ---

    @staticmethod
    def _normalize_error(error: str) -> str:
        normalized = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}", "<timestamp>", error)
        normalized = re.sub(r"\b\d+\b", "<n>", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized[:500]

    @staticmethod
    def _derive_error(step: dict, codex_output: dict) -> str:
        if step.get("error_message"):
            return step["error_message"]
        if codex_output.get("exitCode", 0) != 0:
            stderr = (codex_output.get("stderr") or "").strip()
            return f"Codex exited with {codex_output['exitCode']}: {stderr[:1000] or 'no stderr'}"
        return "Step did not update status"

    # --- execution loop ---

    def _execute_single_step(self, step: dict, guardrails: str) -> bool:
        step_num, step_name = step["step"], step["name"]
        done = sum(1 for s in self._read_json(self._index_file)["steps"] if s["status"] == "completed")
        prev_error = None
        repeated_errors: dict[str, int] = {}

        for attempt in range(1, self.MAX_RETRIES + 1):
            index = self._read_json(self._index_file)
            step_context = self._build_step_context(index)
            preamble = self._build_preamble(guardrails, step_context, prev_error)

            tag = f"Step {step_num + 1}/{self._total} ({done} done): {step_name}"
            if attempt > 1:
                tag += f" [retry {attempt}/{self.MAX_RETRIES}]"

            with progress_indicator(tag) as pi:
                codex_output = self._invoke_codex(step, preamble)
                elapsed = int(pi.elapsed)

            index = self._read_json(self._index_file)
            current_step = next((s for s in index["steps"] if s["step"] == step_num), step)
            status = current_step.get("status", "pending")
            ts = self._stamp()

            if status == "completed":
                current_step["completed_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                print(f"  OK Step {step_num}: {step_name} [{elapsed}s]")
                return True

            if status == "blocked":
                current_step["blocked_at"] = ts
                self._write_json(self._index_file, index)
                reason = current_step.get("blocked_reason", "")
                print(f"  BLOCKED Step {step_num}: {step_name} [{elapsed}s]")
                print(f"    Reason: {reason}")
                self._update_top_index("blocked")
                sys.exit(2)

            err_msg = self._derive_error(current_step, codex_output)
            normalized = self._normalize_error(err_msg)
            repeated_errors[normalized] = repeated_errors.get(normalized, 0) + 1

            if repeated_errors[normalized] >= self.CIRCUIT_BREAKER_THRESHOLD:
                current_step["status"] = "error"
                current_step["error_message"] = (
                    f"[circuit breaker] Same error repeated {self.CIRCUIT_BREAKER_THRESHOLD} times: {err_msg}"
                )
                current_step["failed_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                print(f"  ERROR Step {step_num}: repeated failure circuit breaker [{elapsed}s]")
                self._update_top_index("error")
                sys.exit(1)

            if attempt < self.MAX_RETRIES:
                current_step["status"] = "pending"
                current_step.pop("error_message", None)
                self._write_json(self._index_file, index)
                prev_error = err_msg
                print(f"  RETRY Step {step_num}: retry {attempt}/{self.MAX_RETRIES} - {err_msg}")
            else:
                current_step["status"] = "error"
                current_step["error_message"] = f"[{self.MAX_RETRIES}회 시도 후 실패] {err_msg}"
                current_step["failed_at"] = ts
                self._write_json(self._index_file, index)
                self._commit_step(step_num, step_name)
                print(f"  ERROR Step {step_num}: {step_name} failed after {self.MAX_RETRIES} attempts [{elapsed}s]")
                print(f"    Error: {err_msg}")
                self._update_top_index("error")
                sys.exit(1)

        return False

    def _execute_all_steps(self, guardrails: str):
        while True:
            index = self._read_json(self._index_file)
            pending = next((s for s in index["steps"] if s["status"] == "pending"), None)
            if pending is None:
                print("\n  All steps completed.")
                return

            step_num = pending["step"]
            for s in index["steps"]:
                if s["step"] == step_num and "started_at" not in s:
                    s["started_at"] = self._stamp()
                    self._write_json(self._index_file, index)
                    break

            self._execute_single_step(pending, guardrails)

    def _finalize(self):
        index = self._read_json(self._index_file)
        index["completed_at"] = self._stamp()
        self._write_json(self._index_file, index)
        self._update_top_index("completed")

        self._run_git("add", "-A")
        if self._run_git("diff", "--cached", "--quiet").returncode != 0:
            msg = f"chore({self._phase_name}): mark phase completed"
            r = self._run_git("commit", "-m", msg)
            if r.returncode == 0:
                print(f"  OK {msg}")

        if self._auto_push:
            branch = self._branch_name()
            r = self._run_git("push", "-u", "origin", branch)
            if r.returncode != 0:
                print(f"\n  ERROR: git push 실패: {r.stderr.strip()}")
                sys.exit(1)
            print(f"  OK Pushed to origin/{branch}")

        print(f"\n{'=' * 60}")
        print(f"  Phase '{self._phase_name}' completed.")
        print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Codex Harness Step Executor")
    parser.add_argument("phase_dir", help="Phase directory name (e.g. 0-mvp)")
    parser.add_argument("--push", action="store_true", help="Push branch after completion")
    args = parser.parse_args()

    StepExecutor(args.phase_dir, auto_push=args.push).run()


if __name__ == "__main__":
    main()
