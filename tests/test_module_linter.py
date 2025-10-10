from __future__ import annotations

from pathlib import Path

from tools.module_linter import lint_module


def test_module_linter_accepts_reference_module():
    issues = lint_module(Path("modules"), "cardiometabolic_intensive")
    assert issues == []


def test_module_linter_accepts_asthma_v2():
    issues = lint_module(Path("modules"), "asthma_v2")
    assert issues == []


def test_module_linter_accepts_copd_v2():
    issues = lint_module(Path("modules"), "copd_v2")
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


def test_module_linter_requires_sources_for_probabilistic_state(tmp_path: Path):
    module_text = """
name: invalid_prob
description: Missing state sources
version: 0.1.0
gmf_version: 2
sources: [aaaai_asthma_stats]
categories: {}
states:
  start:
    type: start
    transitions:
      - to: branch
  branch:
    type: decision
    transitions:
      - probability: 0.5
        to: end
      - probability: 0.5
        to: end
  end:
    type: terminal
"""
    (tmp_path / "invalid_prob.yaml").write_text(module_text)

    issues = lint_module(tmp_path, "invalid_prob")

    assert any("defines probabilities/delays without sources" in issue for issue in issues)


def test_module_linter_detects_missing_parameter_reference(tmp_path: Path):
    module_text = """
name: invalid_parameter
description: References missing parameter
version: 0.1.0
gmf_version: 2
sources: [aaaai_asthma_stats]
categories: {}
states:
  start:
    type: start
    transitions:
      - to: decision
  decision:
    type: decision
    sources: [aaaai_asthma_stats]
    distributed_transition:
      - transition: end
        distribution:
          use: asthma.nonexistent_parameter
      - transition: end
        distribution: 0.0
  end:
    type: terminal
"""
    (tmp_path / "invalid_parameter.yaml").write_text(module_text)

    issues = lint_module(tmp_path, "invalid_parameter")

    assert issues, "expected linter to flag missing parameter"
    assert any("nonexistent_parameter" in issue for issue in issues)
