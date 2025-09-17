"""Built-in lifecycle scenario templates."""
from __future__ import annotations

from copy import deepcopy
from typing import Dict, List

DEFAULT_SCENARIOS: Dict[str, Dict[str, object]] = {
    "general": {
        "metadata": {"description": "Balanced demographic distribution"},
        "age_dist": {"0-18": 0.22, "19-40": 0.33, "41-65": 0.28, "66-120": 0.17},
        "gender_dist": {"male": 0.49, "female": 0.49, "other": 0.02},
        "race_dist": {
            "White": 0.60,
            "Black": 0.12,
            "Asian": 0.06,
            "Hispanic": 0.16,
            "Native American": 0.02,
            "Other": 0.04,
        },
        "terminology": {
            "icd10_codes": ["E11.9", "I10", "J45.909"],
            "loinc_codes": ["2345-7", "2951-2", "718-7"],
            "rxnorm_cuis": ["860975", "197361", "617320"],
        },
    },
    "cardiometabolic": {
        "metadata": {"description": "Older population with cardiometabolic burden"},
        "age_dist": {"0-18": 0.05, "19-40": 0.18, "41-65": 0.42, "66-120": 0.35},
        "gender_dist": {"male": 0.52, "female": 0.46, "other": 0.02},
        "race_dist": {
            "White": 0.55,
            "Black": 0.20,
            "Asian": 0.05,
            "Hispanic": 0.14,
            "Native American": 0.02,
            "Other": 0.04,
        },
        "smoking_dist": {"Never": 0.35, "Former": 0.45, "Current": 0.20},
        "terminology": {
            "icd10_codes": ["E11.9", "I10"],
            "loinc_codes": ["2345-7", "2951-2"],
            "rxnorm_cuis": ["860975", "197361"],
        },
    },
    "pediatric": {
        "metadata": {"description": "Pediatric-focused clinic population"},
        "age_dist": {"0-18": 0.85, "19-40": 0.15, "41-65": 0.0, "66-120": 0.0},
        "gender_dist": {"male": 0.51, "female": 0.48, "other": 0.01},
        "race_dist": {
            "White": 0.45,
            "Black": 0.15,
            "Asian": 0.08,
            "Hispanic": 0.26,
            "Native American": 0.02,
            "Other": 0.04,
        },
        "terminology": {
            "icd10_codes": ["J45.909"],
            "loinc_codes": ["718-7"],
            "rxnorm_cuis": ["617320"],
        },
    },
}


def list_scenarios() -> List[str]:
    """Return the names of available built-in scenarios."""

    return sorted(DEFAULT_SCENARIOS.keys())


def get_scenario(name: str) -> Dict[str, object]:
    """Fetch a deep copy of a scenario configuration."""

    if name not in DEFAULT_SCENARIOS:
        raise KeyError(f"Scenario '{name}' is not defined")
    return deepcopy(DEFAULT_SCENARIOS[name])
