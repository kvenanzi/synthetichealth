import tempfile
from pathlib import Path

from src.core.lifecycle.loader import load_scenario_config


def test_load_default_scenario_general():
    scenario = load_scenario_config("general")
    assert scenario["age_dist"]["19-40"] > 0
    assert scenario["gender_dist"]["male"] > 0


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


def test_unknown_override_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        missing = Path(tmpdir) / "missing.yaml"
        try:
            load_scenario_config("general", missing.as_posix())
        except FileNotFoundError:
            return
        raise AssertionError("Expected FileNotFoundError for missing override file")

