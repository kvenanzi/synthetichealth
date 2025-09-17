"""Scenario loading utilities."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional

import yaml

from .scenarios import get_scenario
from ..terminology import (
    filter_by_code,
    load_icd10_conditions,
    load_loinc_labs,
    load_rxnorm_medications,
    load_snomed_conditions,
)


def _attach_terminology_payload(scenario: Dict[str, object]) -> Dict[str, object]:
    terminology = scenario.get("terminology") or {}
    if not terminology:
        scenario.pop("terminology_details", None)
        return scenario

    root_override = scenario.get("terminology_root")
    payload: Dict[str, object] = {}

    icd_codes = terminology.get("icd10_codes")
    if icd_codes:
        payload["icd10"] = filter_by_code(load_icd10_conditions(root_override), icd_codes)

    snomed_ids = terminology.get("snomed_ids")
    if snomed_ids:
        payload["snomed"] = filter_by_code(load_snomed_conditions(root_override), snomed_ids)

    loinc_codes = terminology.get("loinc_codes")
    if loinc_codes:
        payload["loinc"] = filter_by_code(load_loinc_labs(root_override), loinc_codes)

    rxnorm_cuis = terminology.get("rxnorm_cuis")
    if rxnorm_cuis:
        payload["rxnorm"] = filter_by_code(load_rxnorm_medications(root_override), rxnorm_cuis)

    scenario["terminology_details"] = payload
    return scenario


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
        return _attach_terminology_payload(merged)

    return _attach_terminology_payload(scenario)
