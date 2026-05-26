#!/usr/bin/env python3
"""Run a Codex review with this harness project's checklist."""

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


REVIEW_PROMPT = """이 프로젝트의 변경 사항을 리뷰하라.

먼저 다음 문서들을 읽어라:
- `/AGENTS.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`

그런 다음 변경된 파일들을 확인하고, 아래 체크리스트로 검증하라:

1. 아키텍처 준수: ARCHITECTURE.md에 정의된 디렉토리 구조를 따르고 있는가?
2. 기술 스택 준수: ADR에 정의된 기술 선택을 벗어나지 않았는가?
3. 테스트 존재: 새로운 기능에 대한 테스트가 작성되어 있는가?
4. CRITICAL 규칙: AGENTS.md의 CRITICAL 규칙을 위반하지 않았는가?
5. 빌드 가능: 빌드/테스트 명령어가 에러 없이 통과하는가?

위반 사항이 있으면 심각도순으로 파일/라인과 수정 방안을 구체적으로 제시하라.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Codex review with harness checklist")
    parser.add_argument("--base", help="Review against a base branch")
    parser.add_argument("--commit", help="Review a specific commit")
    parser.add_argument("--uncommitted", action="store_true", help="Review uncommitted changes")
    args = parser.parse_args()

    command = ["codex", "review"]
    if args.base:
        command.extend(["--base", args.base])
    if args.commit:
        command.extend(["--commit", args.commit])
    if args.uncommitted or not (args.base or args.commit):
        command.append("--uncommitted")
    command.append("-")

    result = subprocess.run(command, input=REVIEW_PROMPT, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
