import sys
import tempfile
from pathlib import Path

import pytest

# Ensure repository root is available for in-module imports during direct execution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core.lifecycle.loader import load_scenario_config


def test_load_default_scenario_general():
    scenario = load_scenario_config("general")
    assert scenario["age_dist"]["19-40"] > 0
    assert scenario["gender_dist"]["male"] > 0
    terminology = scenario.get("terminology_details")
    assert terminology and "icd10" in terminology
    assert "modules" in scenario
    icd_codes = {entry.code for entry in terminology["icd10"]}
    assert "I10" in icd_codes  # normalized ICD-10 starts at chapter A; scenario falls back to essential hypertension
    assert "vsac" in terminology
    assert "umls" in terminology
    vsac_sets = terminology["vsac"]
    assert "2.16.840.1.113883.3.526.3.1567" in vsac_sets
    assert terminology["umls"][0].cui == "C0020538"


def test_scenario_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        override_path = Path(tmpdir) / "override.yaml"
        override_path.write_text(
            """
age_dist:
  0-18: 1.0
metadata:
  description: Custom mix
            """,
            encoding="utf-8",
        )

        scenario = load_scenario_config("general", override_path.as_posix())
        assert scenario["age_dist"]["0-18"] == 1.0
        assert scenario["metadata"]["description"] == "Custom mix"
        assert scenario["terminology_details"]["loinc"]
        assert scenario["terminology_details"]["vsac"]


def test_unknown_override_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        missing = Path(tmpdir) / "missing.yaml"
        try:
            load_scenario_config("general", missing.as_posix())
        except FileNotFoundError:
            return
        raise AssertionError("Expected FileNotFoundError for missing override file")


def test_override_with_deprecated_migration_key_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        override_path = Path(tmpdir) / "override.yaml"
        override_path.write_text(
            """
simulate_migration: true
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError) as excinfo:
            load_scenario_config("general", override_path.as_posix())

        assert "simulate_migration" in str(excinfo.value)
        assert "deprecated migration key" in str(excinfo.value)
