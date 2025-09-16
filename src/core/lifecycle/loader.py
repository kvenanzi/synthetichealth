"""Scenario loading utilities."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional

import yaml

from .scenarios import get_scenario


def load_scenario_config(
    scenario_name: Optional[str], overrides_path: Optional[str] = None
) -> Dict[str, object]:
    """Load a lifecycle scenario definition, optionally applying YAML overrides."""

    scenario: Dict[str, object] = {}
    if scenario_name:
        try:
            scenario = get_scenario(scenario_name)
        except KeyError as exc:
            raise ValueError(f"Scenario '{scenario_name}' is not defined") from exc

    if overrides_path:
        override_path = Path(overrides_path)
        if not override_path.exists():
            raise FileNotFoundError(f"Scenario override file not found: {overrides_path}")
        with override_path.open("r", encoding="utf-8") as handle:
            overrides = yaml.safe_load(handle) or {}
        merged = deepcopy(scenario)
        merged.update(overrides)
        return merged

    return scenario
