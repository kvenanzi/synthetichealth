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
    "oncology_survivorship": {
        "metadata": {"description": "Breast cancer survivorship with endocrine therapy"},
        "age_dist": {"0-18": 0.0, "19-40": 0.25, "41-65": 0.5, "66-120": 0.25},
        "gender_dist": {"male": 0.02, "female": 0.97, "other": 0.01},
        "race_dist": {
            "White": 0.58,
            "Black": 0.18,
            "Asian": 0.08,
            "Hispanic": 0.13,
            "Native American": 0.01,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["C50.912", "Z85.3"],
            "loinc_codes": ["33717-0", "24627-2"],
            "rxnorm_cuis": ["4179", "310362", "310940", "197943"],
            "value_set_oids": ["2.16.840.1.113883.3.526.3.1029"],
            "umls_cuis": ["C0006142"],
        },
        "modules": ["oncology_survivorship"],
    },
    "ckd_dialysis": {
        "metadata": {"description": "Advanced CKD cohort preparing for dialysis"},
        "age_dist": {"0-18": 0.0, "19-40": 0.2, "41-65": 0.45, "66-120": 0.35},
        "gender_dist": {"male": 0.52, "female": 0.47, "other": 0.01},
        "race_dist": {
            "White": 0.48,
            "Black": 0.28,
            "Asian": 0.1,
            "Hispanic": 0.1,
            "Native American": 0.02,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["N18.4", "N18.6", "D63.1"],
            "loinc_codes": ["33914-3", "2160-0", "77145-4", "2951-2"],
            "rxnorm_cuis": ["111419", "861007"],
            "value_set_oids": ["2.16.840.1.113883.3.464.1003.118.12.1035"],
            "umls_cuis": ["C1561643"],
        },
        "modules": ["ckd_dialysis_planning"],
    },
    "copd_home_oxygen": {
        "metadata": {"description": "Severe COPD with home oxygen therapy"},
        "age_dist": {"0-18": 0.0, "19-40": 0.1, "41-65": 0.35, "66-120": 0.55},
        "gender_dist": {"male": 0.52, "female": 0.47, "other": 0.01},
        "race_dist": {
            "White": 0.6,
            "Black": 0.18,
            "Asian": 0.05,
            "Hispanic": 0.13,
            "Native American": 0.02,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["J44.1", "Z99.81"],
            "loinc_codes": ["19868-9", "8277-6", "2708-6"],
            "rxnorm_cuis": ["896443", "197361", "435", "865098", "18600"],
            "value_set_oids": ["2.16.840.1.113883.3.117.1.7.1.276"],
            "umls_cuis": ["C0024117"],
        },
        "modules": ["copd_home_oxygen"],
    },
    "mental_health_integrated": {
        "metadata": {"description": "Collaborative mental health care with telehealth"},
        "age_dist": {"0-18": 0.05, "19-40": 0.45, "41-65": 0.4, "66-120": 0.1},
        "gender_dist": {"male": 0.45, "female": 0.53, "other": 0.02},
        "race_dist": {
            "White": 0.5,
            "Black": 0.2,
            "Asian": 0.08,
            "Hispanic": 0.16,
            "Native American": 0.02,
            "Other": 0.04,
        },
        "terminology": {
            "icd10_codes": ["F33.1", "F41.1"],
            "loinc_codes": ["44261-6", "69730-0"],
            "rxnorm_cuis": ["312961", "310798"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1222.180"],
            "umls_cuis": ["C0024517"],
        },
        "modules": ["mental_health_integrated_care"],
    },
    "geriatric_polypharmacy": {
        "metadata": {"description": "Geriatric multimorbidity cohort with fall risk management"},
        "age_dist": {"0-18": 0.0, "19-40": 0.05, "41-65": 0.2, "66-120": 0.75},
        "gender_dist": {"male": 0.35, "female": 0.63, "other": 0.02},
        "race_dist": {
            "White": 0.62,
            "Black": 0.2,
            "Asian": 0.05,
            "Hispanic": 0.1,
            "Native American": 0.01,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["I50.32", "N18.30", "M17.11"],
            "loinc_codes": ["718-7", "2160-0", "10998-3"],
            "rxnorm_cuis": ["200371", "856874", "7052"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1047.18"],
            "umls_cuis": ["C0018802"],
        },
        "modules": ["geriatric_polypharmacy"],
    },
    "sepsis_survivorship": {
        "metadata": {"description": "Post-sepsis survivorship with readmission prevention"},
        "age_dist": {"0-18": 0.02, "19-40": 0.25, "41-65": 0.4, "66-120": 0.33},
        "gender_dist": {"male": 0.52, "female": 0.47, "other": 0.01},
        "race_dist": {
            "White": 0.54,
            "Black": 0.22,
            "Asian": 0.08,
            "Hispanic": 0.13,
            "Native American": 0.01,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["A41.9"],
            "loinc_codes": ["6690-2", "1975-2", "2160-0", "8302-2"],
            "rxnorm_cuis": ["245155", "727367"],
            "value_set_oids": ["2.16.840.1.113762.1.4.1046.63"],
            "umls_cuis": ["C0036690"],
        },
        "modules": ["sepsis_survivorship"],
    },
    "hiv_prep": {
        "metadata": {"description": "HIV chronic care and PrEP prevention cohorts"},
        "age_dist": {"0-18": 0.05, "19-40": 0.5, "41-65": 0.4, "66-120": 0.05},
        "gender_dist": {"male": 0.55, "female": 0.43, "other": 0.02},
        "race_dist": {
            "White": 0.42,
            "Black": 0.28,
            "Asian": 0.09,
            "Hispanic": 0.18,
            "Native American": 0.01,
            "Other": 0.02,
        },
        "terminology": {
            "icd10_codes": ["B20", "Z20.6"],
            "loinc_codes": ["25836-8", "56888-1", "14682-9"],
            "rxnorm_cuis": ["1996631", "818054", "213293"],
            "value_set_oids": ["2.16.840.1.113883.3.464.1003.110.12.1078", "2.16.840.1.113883.3.464.1003.110.12.1079"],
            "umls_cuis": ["C0019693"],
        },
        "modules": ["hiv_prep_management"],
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
