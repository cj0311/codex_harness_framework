#!/usr/bin/env python3
"""Codex PreToolUse guardrails for dangerous commands and TDD discipline."""

from __future__ import annotations

import json
import re
import sys
from pathlib import PurePosixPath


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DANGEROUS_COMMANDS = [
    r"\brm\s+-rf\b",
    r"\brmdir\s+/s\b",
    r"\bdel\s+/[fsq]\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+push\b[^\n]*\s--force(?:-with-lease)?\b",
    r"\bgit\s+clean\s+-fdx\b",
    r"\bDROP\s+TABLE\b",
]

PRODUCTION_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs", ".java", ".kt", ".cs"}
TEST_MARKERS = (
    "/test/",
    "/tests/",
    "/__tests__/",
    ".test.",
    ".spec.",
    "_test.",
    "test_",
)
PRODUCTION_DIRS = ("app/", "src/", "components/", "lib/", "services/", "server/", "pages/")


def _load_event() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def _command_from_event(event: dict) -> str:
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    if isinstance(tool_input, str):
        return tool_input
    return ""


def _changed_files_from_patch(command: str) -> set[str]:
    files: set[str] = set()
    patterns = [
        r"^\*\*\* (?:Add|Update|Delete) File: (.+)$",
        r"^\+\+\+ b/(.+)$",
        r"^--- a/(.+)$",
    ]
    for line in command.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                files.add(match.group(1).strip().replace("\\", "/"))
    return files


def _is_test_file(path: str) -> bool:
    normalized = "/" + path.replace("\\", "/").lower()
    return any(marker in normalized for marker in TEST_MARKERS)


def _is_production_code(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    suffix = PurePosixPath(normalized).suffix
    return suffix in PRODUCTION_SUFFIXES and normalized.startswith(PRODUCTION_DIRS) and not _is_test_file(normalized)


def _check_dangerous_shell(command: str) -> str | None:
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return f"Dangerous shell command blocked by Codex hook: {pattern}"
    return None


def _check_tdd(command: str) -> str | None:
    changed_files = _changed_files_from_patch(command)
    if not changed_files:
        return None

    production_files = [path for path in changed_files if _is_production_code(path)]
    test_files = [path for path in changed_files if _is_test_file(path)]
    if production_files and not test_files:
        return (
            "TDD guard blocked production code changes without a test file in the same patch. "
            "Add or update a relevant test first, or include the test change with the implementation."
        )
    return None


def main() -> int:
    event = _load_event()
    tool_name = event.get("tool_name", "")
    command = _command_from_event(event)

    if tool_name == "Bash":
        reason = _check_dangerous_shell(command)
        if reason:
            _deny(reason)
            return 0

    if tool_name in {"apply_patch", "Edit", "Write"}:
        reason = _check_tdd(command)
        if reason:
            _deny(reason)
            return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
