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
            "value_set_oids": ["2.16.840.1.113883.3.526.3.1567"],
            "umls_cuis": ["C0020538"],
        },
        "modules": [],
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
            "value_set_oids": ["2.16.840.1.113883.3.526.3.1567"],
            "umls_cuis": ["C0020538"],
        },
        "modules": ["cardiometabolic_intensive"],
    },
    "pediatric_asthma": {
        "metadata": {"description": "Pediatric asthma cohort with immunization catch-up"},
        "age_dist": {"0-18": 0.9, "19-40": 0.1, "41-65": 0.0, "66-120": 0.0},
        "gender_dist": {"male": 0.53, "female": 0.46, "other": 0.01},
        "race_dist": {
            "White": 0.42,
            "Black": 0.18,
            "Asian": 0.09,
            "Hispanic": 0.26,
            "Native American": 0.02,
            "Other": 0.03,
        },
        "terminology": {
            "icd10_codes": ["J45.40"],
            "loinc_codes": ["2019-8", "44261-6", "11557-6", "19868-9"],
            "rxnorm_cuis": ["859038", "856641", "435", "312615"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1170.3"],
            "umls_cuis": ["C0004096"],
        },
        "modules": ["pediatric_asthma_management"],
    },
    "pediatric": {
        "metadata": {"description": "Pediatric asthma cohort with immunization catch-up"},
        "age_dist": {"0-18": 0.9, "19-40": 0.1, "41-65": 0.0, "66-120": 0.0},
        "gender_dist": {"male": 0.53, "female": 0.46, "other": 0.01},
        "race_dist": {
            "White": 0.42,
            "Black": 0.18,
            "Asian": 0.09,
            "Hispanic": 0.26,
            "Native American": 0.02,
            "Other": 0.03,
        },
        "terminology": {
            "icd10_codes": ["J45.40"],
            "loinc_codes": ["2019-8", "44261-6", "11557-6", "19868-9"],
            "rxnorm_cuis": ["859038", "856641", "435", "312615"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1170.3"],
            "umls_cuis": ["C0004096"],
        },
        "modules": ["pediatric_asthma_management"],
    },
    "prenatal_care": {
        "metadata": {"description": "Prenatal cohort with gestational diabetes screening"},
        "age_dist": {"0-18": 0.02, "19-40": 0.85, "41-65": 0.13, "66-120": 0.0},
        "gender_dist": {"male": 0.0, "female": 0.99, "other": 0.01},
        "race_dist": {
            "White": 0.46,
            "Black": 0.19,
            "Asian": 0.07,
            "Hispanic": 0.24,
            "Native American": 0.02,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["Z34.03", "O24.419"],
            "loinc_codes": ["14771-0", "8480-6", "56052-8", "14779-1"],
            "rxnorm_cuis": ["7052", "316048"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1096.53"],
            "umls_cuis": ["C0022876"],
        },
        "modules": ["prenatal_care_management"],
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
