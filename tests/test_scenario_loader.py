import tempfile
from pathlib import Path

import pytest

from src.core.lifecycle.loader import load_scenario_config
from src.core.lifecycle.scenarios import DEFAULT_SCENARIOS


def test_load_default_scenario_general():
    scenario = load_scenario_config("general")
    assert scenario["age_dist"]["19-40"] > 0
    assert scenario["gender_dist"]["male"] > 0


def test_scenario_override(tmp_path: Path):
    override_path = tmp_path / "override.yaml"
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


def test_unknown_override_file(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        load_scenario_config("general", missing.as_posix())

