"""Scenario loading utilities."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .scenarios import get_scenario
from ..terminology import (
    filter_by_code,
    load_icd10_conditions,
    load_loinc_labs,
    load_rxnorm_medications,
    load_snomed_conditions,
    load_umls_concepts,
    load_vsac_value_sets,
)

DEPRECATED_SCENARIO_KEYS = {
    "simulate_migration",
    "migration_strategy",
    "migration_settings",
    "migration_report",
}


def _ensure_no_deprecated_keys(payload: Any, *, context: str, path: str = "") -> None:
    """Raise a ValueError if migration-era keys still appear in scenario data."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            current_path = f"{path}.{key}" if path else key
            if key in DEPRECATED_SCENARIO_KEYS:
                raise ValueError(
                    f"{context} includes deprecated migration key '{current_path}'. "
                    "Remove migration settings before loading the scenario."
                )
            _ensure_no_deprecated_keys(value, context=context, path=current_path)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            current_path = f"{path}[{index}]" if path else f"[{index}]"
            _ensure_no_deprecated_keys(item, context=context, path=current_path)


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

    value_set_oids = terminology.get("value_set_oids")
    if value_set_oids:
        members = load_vsac_value_sets(root_override)
        if members:
            grouped = {}
            wanted = set(value_set_oids)
            for member in members:
                if member.value_set_oid not in wanted:
                    continue
                grouped.setdefault(member.value_set_oid, []).append(member)
            if grouped:
                payload["vsac"] = grouped

    umls_cuis = terminology.get("umls_cuis")
    if umls_cuis:
        concepts = load_umls_concepts(root_override)
        if concepts:
            lookup = {concept.cui: concept for concept in concepts if concept.cui}
            selected = [lookup[cui] for cui in umls_cuis if cui in lookup]
            if selected:
                payload["umls"] = selected

    scenario["terminology_details"] = payload
    scenario.setdefault("modules", scenario.get("modules", []))
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
        _ensure_no_deprecated_keys(
            scenario,
            context=f"Scenario '{scenario_name}' definition",
        )

    if overrides_path:
        override_path = Path(overrides_path)
        if not override_path.exists():
            raise FileNotFoundError(f"Scenario override file not found: {overrides_path}")
        with override_path.open("r", encoding="utf-8") as handle:
            overrides = yaml.safe_load(handle) or {}
        _ensure_no_deprecated_keys(
            overrides,
            context=f"Scenario override '{overrides_path}'",
        )
        merged = deepcopy(scenario)
        merged.update(overrides)
        _ensure_no_deprecated_keys(
            merged,
            context="Merged scenario configuration",
        )
        return _attach_terminology_payload(merged)

    return _attach_terminology_payload(scenario)
