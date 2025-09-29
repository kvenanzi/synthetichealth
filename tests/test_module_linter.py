from __future__ import annotations

from pathlib import Path

from tools.module_linter import lint_module


def test_module_linter_accepts_reference_module():
    issues = lint_module(Path("modules"), "cardiometabolic_intensive")
    assert issues == []


def test_module_linter_detects_missing_codes(tmp_path: Path):
    module_text = """
name: invalid
description: Missing codes
categories: {}
states:
  start:
    type: start
    transitions:
      - to: problem
  problem:
    type: condition_onset
    conditions:
      - name: Test Condition
    transitions:
      - to: end
  end:
    type: terminal
"""
    (tmp_path / "invalid.yaml").write_text(module_text)

    issues = lint_module(tmp_path, "invalid")

    assert issues, "expected linter to report issues"
    assert any("missing icd10/snomed" in issue for issue in issues)
