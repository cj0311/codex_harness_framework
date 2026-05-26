#!/usr/bin/env python3
"""Run lightweight project verification when a Codex turn stops."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VERIFY_ORDER = ("lint", "build", "test")


def _package_scripts(root: Path) -> dict:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    scripts = package.get("scripts", {})
    return scripts if isinstance(scripts, dict) else {}


def _run(command: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=180)


def main() -> int:
    root = Path.cwd()
    scripts = _package_scripts(root)
    commands = [["npm", "run", name] for name in VERIFY_ORDER if name in scripts]

    if not commands:
        return 0

    failures = []
    for command in commands:
        result = _run(command, root)
        if result.returncode != 0:
            failures.append(
                {
                    "command": " ".join(command),
                    "exitCode": result.returncode,
                    "stderr": result.stderr[-2000:],
                    "stdout": result.stdout[-2000:],
                }
            )

    if failures:
        print(json.dumps({"verificationFailures": failures}, ensure_ascii=False), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
