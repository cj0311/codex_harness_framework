#!/usr/bin/env python3
"""
Generate phase plans with Codex.

This is the Codex replacement for the old Claude custom command. It reads the
project docs and asks `codex exec` to create `phases/` planning files.

Usage:
    python scripts/harness.py <task-name> [--project <name>] [--model <model>]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_prompt(task_name: str, project_name: str | None = None) -> str:
    docs = []
    for path in sorted((ROOT / "docs").glob("*.md")):
        rel_path = path.relative_to(ROOT).as_posix()
        docs.append(f"## {rel_path}\n\n{path.read_text(encoding='utf-8')}")

    agents = _read_optional(ROOT / "AGENTS.md")
    project = project_name or "{AGENTS.md의 프로젝트명}"
    return f"""당신은 Codex Harness의 phase 설계자입니다.

아래 프로젝트 규칙과 문서를 읽고 `{task_name}` 구현 계획을 여러 step 파일로 생성하세요.

## 프로젝트명
{project}

## AGENTS.md

{agents}

---

{chr(10).join(docs)}

---

## 생성할 파일

1. `phases/index.json`
   - 없으면 생성한다.
   - 있으면 `phases` 배열에 `{task_name}` 항목만 추가한다. 중복 추가하지 않는다.

2. `phases/{task_name}/index.json`
   - `project`, `phase`, `steps`를 포함한다.
   - step은 5~10개 사이로 작게 나눈다.
   - 모든 step의 초기 status는 `"pending"`이다.
   - `created_at`, `started_at`, `completed_at`, `failed_at`, `blocked_at`은 넣지 않는다.

3. `phases/{task_name}/stepN.md`
   - 각 step은 독립적인 `codex exec` 세션에서 실행될 수 있을 만큼 자기완결적으로 작성한다.
   - 반드시 포함할 섹션:
     - `# Step N: <name>`
     - `## 읽어야 할 파일`
     - `## 작업`
     - `## Acceptance Criteria`
     - `## 검증 절차`
     - `## 금지사항`

## 설계 원칙

1. Scope 최소화: 하나의 step에서 하나의 레이어 또는 모듈만 다룬다.
2. 자기완결성: 이전 대화나 암묵적 맥락을 참조하지 않는다.
3. 사전 준비 강제: 읽어야 할 문서와 관련 파일 경로를 명시한다.
4. 시그니처 수준 지시: 인터페이스는 제시하되 세부 구현은 Codex 재량에 맡긴다.
5. AC는 실행 가능한 커맨드로 작성한다.
6. 금지사항은 "X를 하지 마라. 이유: Y" 형식으로 구체화한다.
7. step name은 kebab-case slug를 사용한다.

## 상태 업데이트 규칙

각 step 파일의 검증 절차에는 다음 규칙을 포함한다.

- 성공: `phases/{task_name}/index.json`의 해당 step을 `"completed"`로 바꾸고 `"summary"`를 한 줄로 기록한다.
- 실패: 같은 에러를 5회 반복하거나 AC를 통과하지 못하면 `"error"`와 `"error_message"`를 기록한다.
- 사용자 개입 필요: `"blocked"`와 `"blocked_reason"`을 기록하고 중단한다.

계획 파일만 생성하고 구현 코드는 작성하지 마세요.
"""


def run_codex(prompt: str, *, model: str | None = None) -> subprocess.CompletedProcess:
    command = [
        "codex",
        "--ask-for-approval",
        "never",
    ]
    if model:
        command.extend(["--model", model])
    command.extend(["exec", "--sandbox", "workspace-write", "-"])
    return subprocess.run(command, input=prompt, cwd=ROOT, capture_output=True, text=True, timeout=1800)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Codex Harness phase files")
    parser.add_argument("task_name", help="Phase directory name, e.g. 0-mvp")
    parser.add_argument("--project", help="Project name to write into phase index")
    parser.add_argument("--model", help="Optional Codex model override")
    parser.add_argument("--print-prompt", action="store_true", help="Print the generated prompt instead of running Codex")
    args = parser.parse_args()

    prompt = build_prompt(args.task_name, args.project)
    if args.print_prompt:
        print(prompt)
        return 0

    result = run_codex(prompt, model=args.model)
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
