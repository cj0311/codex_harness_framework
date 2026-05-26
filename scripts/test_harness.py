"""Tests for phase plan generation wrapper."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import harness


def test_build_prompt_includes_task_name(tmp_path):
    with patch.object(harness, "ROOT", tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Project rules", encoding="utf-8")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "PRD.md").write_text("# PRD", encoding="utf-8")

        prompt = harness.build_prompt("0-mvp", "Demo")

    assert "0-mvp" in prompt
    assert "Demo" in prompt
    assert "# Project rules" in prompt
    assert "# PRD" in prompt


def test_run_codex_uses_exec_stdin(tmp_path):
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    with patch.object(harness, "ROOT", tmp_path):
        with patch("subprocess.run", return_value=completed) as mock_run:
            result = harness.run_codex("PROMPT", model="gpt-test")

    command = mock_run.call_args[0][0]
    assert command[:3] == ["codex", "--ask-for-approval", "never"]
    assert "--model" in command
    assert "exec" in command
    assert command[-1] == "-"
    assert mock_run.call_args.kwargs["input"] == "PROMPT"
    assert result.returncode == 0
