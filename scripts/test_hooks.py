"""Tests for Codex hook scripts."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent


def _load_hook(name: str):
    path = ROOT / ".codex" / "hooks" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_blocks_dangerous_bash_command(capsys):
    hook = _load_hook("pre_tool_use")
    event = {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}}

    with patch("sys.stdin", io.StringIO(json.dumps(event))):
        assert hook.main() == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    decision = payload["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "Dangerous" in decision["permissionDecisionReason"]


def test_blocks_production_patch_without_tests(capsys):
    hook = _load_hook("pre_tool_use")
    patch_text = """*** Begin Patch
*** Update File: src/app.ts
@@
+export const value = 1;
*** End Patch
"""
    event = {"tool_name": "apply_patch", "tool_input": {"command": patch_text}}

    with patch("sys.stdin", io.StringIO(json.dumps(event))):
        assert hook.main() == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    decision = payload["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "TDD guard" in decision["permissionDecisionReason"]


def test_allows_patch_with_test_file(capsys):
    hook = _load_hook("pre_tool_use")
    patch_text = """*** Begin Patch
*** Update File: src/app.ts
@@
+export const value = 1;
*** Add File: src/app.test.ts
+import { value } from "./app";
*** End Patch
"""
    event = {"tool_name": "apply_patch", "tool_input": {"command": patch_text}}

    with patch("sys.stdin", io.StringIO(json.dumps(event))):
        assert hook.main() == 0

    captured = capsys.readouterr()
    assert captured.out == ""


def test_stop_verify_no_package_is_noop(tmp_path):
    hook = _load_hook("stop_verify")

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        assert hook.main() == 0
