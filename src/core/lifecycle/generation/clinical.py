"""Lifecycle clinical generation helpers extracted from synthetic_patient_generator."""
from __future__ import annotations

import calendar
import difflib
import random
import re
import string
import uuid
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple

from faker import Faker

from ..constants import (
    AGE_BINS,
    AGE_BIN_LABELS,
    CONDITION_STATUSES,
    ENCOUNTER_REASONS,
    ENCOUNTER_TYPES,
)
from ...terminology_catalogs import (
    CONDITIONS as CONDITION_TERMS,
    MEDICATIONS as FALLBACK_MEDICATION_TERMS,
    IMMUNIZATIONS as IMMUNIZATION_TERMS,
    ALLERGENS as FALLBACK_ALLERGEN_TERMS,
    PROCEDURES as PROCEDURE_TERMS,
)
from ...terminology.loaders import (
    load_allergen_entries,
    load_allergy_reaction_entries,
    load_icd10_conditions,
    load_lab_test_entries,
    load_medication_entries,
    load_snomed_conditions,
    load_snomed_icd10_crosswalk,
)


class LazyMapping(Mapping):
    """Deferred dictionary that loads data on first access."""

    def __init__(self, loader):
        self._loader = loader
        self._data: Optional[Dict[str, Any]] = None

    def _ensure(self) -> Dict[str, Any]:
        if self._data is None:
            self._data = dict(self._loader())
        return self._data

    def __getitem__(self, key: str) -> Any:
        return self._ensure()[key]

    def __iter__(self):
        return iter(self._ensure())

    def __len__(self) -> int:
        return len(self._ensure())

    def __contains__(self, key: object) -> bool:
        return key in self._ensure()

    def keys(self):
        return self._ensure().keys()

    def items(self):
        return self._ensure().items()

    def values(self):
        return self._ensure().values()

    def get(self, key: str, default: Any = None) -> Any:
        return self._ensure().get(key, default)

    def __repr__(self) -> str:
        if self._data is None:
            return f"<LazyMapping loader={self._loader.__name__}>"
        return repr(self._data)


class LazySequence(Sequence):
    """Deferred sequence that materializes to a list on first access."""

    def __init__(self, loader):
        self._loader = loader
        self._data: Optional[List[Any]] = None

    def _ensure(self) -> List[Any]:
        if self._data is None:
            result = self._loader()
            if isinstance(result, list):
                self._data = result
            else:
                self._data = list(result)
        return self._data

    def __getitem__(self, index: int) -> Any:
        return self._ensure()[index]

    def __len__(self) -> int:
        return len(self._ensure())

    def __iter__(self):
        return iter(self._ensure())

    def __contains__(self, value: object) -> bool:
        return value in self._ensure()

    def __repr__(self) -> str:
        if self._data is None:
            return f"<LazySequence loader={self._loader.__name__}>"
        return repr(self._data)


CURATED_CONDITION_ENTRIES = {entry["display"]: entry for entry in CONDITION_TERMS}
CURATED_CONDITION_LOOKUP = {
    re.sub(r"[^a-z0-9]+", " ", entry["display"].lower()).strip(): entry
    for entry in CONDITION_TERMS
}

ICD10_CATEGORY_LABELS = {
    "infectious_disease": "Certain infectious and parasitic diseases",
    "oncology": "Neoplasms",
    "hematologic": "Diseases of the blood and immune mechanism",
    "endocrine": "Endocrine, nutritional and metabolic diseases",
    "mental_health": "Mental, behavioral and neurodevelopmental disorders",
    "neurology": "Diseases of the nervous system",
    "ophthalmology_otology": "Diseases of the eye and adnexa; ear and mastoid process",
    "cardiovascular": "Diseases of the circulatory system",
    "respiratory": "Diseases of the respiratory system",
    "gastroenterology": "Diseases of the digestive system",
    "dermatology": "Diseases of the skin and subcutaneous tissue",
    "musculoskeletal": "Diseases of the musculoskeletal system and connective tissue",
    "genitourinary": "Diseases of the genitourinary system",
    "obstetrics": "Pregnancy, childbirth and the puerperium",
    "perinatal": "Certain conditions originating in the perinatal period",
    "congenital": "Congenital malformations, deformations and chromosomal abnormalities",
    "symptoms": "Symptoms, signs and abnormal clinical findings",
    "injury": "Injury, poisoning and certain other consequences of external causes",
    "factors_influencing": "Factors influencing health status and contact with health services",
    "transport": "External causes - transport",
    "external_causes": "External causes of morbidity",
    "misc": "Other conditions",
}

CATEGORY_BASE_PREVALENCE = {
    "infectious_disease": 0.08,
    "oncology": 0.035,
    "hematologic": 0.05,
    "endocrine": 0.12,
    "mental_health": 0.16,
    "neurology": 0.07,
    "ophthalmology_otology": 0.05,
    "cardiovascular": 0.2,
    "respiratory": 0.12,
    "gastroenterology": 0.1,
    "dermatology": 0.06,
    "musculoskeletal": 0.14,
    "genitourinary": 0.08,
    "obstetrics": 0.06,
    "perinatal": 0.02,
    "congenital": 0.03,
    "symptoms": 0.05,
    "injury": 0.07,
    "factors_influencing": 0.04,
    "transport": 0.0,
    "external_causes": 0.0,
    "misc": 0.03,
}

CATEGORY_AGE_WEIGHTS = {
    "infectious_disease": {"0-18": 0.25, "19-40": 0.35, "41-65": 0.25, "66-120": 0.15},
    "oncology": {"0-18": 0.02, "19-40": 0.08, "41-65": 0.3, "66-120": 0.6},
    "hematologic": {"0-18": 0.08, "19-40": 0.22, "41-65": 0.35, "66-120": 0.35},
    "endocrine": {"0-18": 0.05, "19-40": 0.35, "41-65": 0.4, "66-120": 0.2},
    "mental_health": {"0-18": 0.22, "19-40": 0.4, "41-65": 0.25, "66-120": 0.13},
    "neurology": {"0-18": 0.05, "19-40": 0.15, "41-65": 0.4, "66-120": 0.4},
    "ophthalmology_otology": {"0-18": 0.05, "19-40": 0.2, "41-65": 0.35, "66-120": 0.4},
    "cardiovascular": {"0-18": 0.01, "19-40": 0.09, "41-65": 0.35, "66-120": 0.55},
    "respiratory": {"0-18": 0.25, "19-40": 0.35, "41-65": 0.25, "66-120": 0.15},
    "gastroenterology": {"0-18": 0.1, "19-40": 0.35, "41-65": 0.35, "66-120": 0.2},
    "dermatology": {"0-18": 0.2, "19-40": 0.4, "41-65": 0.25, "66-120": 0.15},
    "musculoskeletal": {"0-18": 0.05, "19-40": 0.25, "41-65": 0.35, "66-120": 0.35},
    "genitourinary": {"0-18": 0.05, "19-40": 0.35, "41-65": 0.35, "66-120": 0.25},
    "obstetrics": {"0-18": 0.02, "19-40": 0.9, "41-65": 0.08, "66-120": 0.0},
    "perinatal": {"0-18": 1.0, "19-40": 0.0, "41-65": 0.0, "66-120": 0.0},
    "congenital": {"0-18": 0.7, "19-40": 0.2, "41-65": 0.08, "66-120": 0.02},
    "symptoms": {"0-18": 0.25, "19-40": 0.35, "41-65": 0.25, "66-120": 0.15},
    "injury": {"0-18": 0.3, "19-40": 0.4, "41-65": 0.2, "66-120": 0.1},
    "factors_influencing": {"0-18": 0.15, "19-40": 0.35, "41-65": 0.3, "66-120": 0.2},
    "misc": {"0-18": 0.2, "19-40": 0.35, "41-65": 0.3, "66-120": 0.15},
}

CATEGORY_SEX_BIASES = {
    "cardiovascular": {"male": 0.55, "female": 0.45, "other": 0.1},
    "oncology": {"male": 0.5, "female": 0.5, "other": 0.1},
    "mental_health": {"male": 0.45, "female": 0.55, "other": 0.2},
    "obstetrics": {"male": 0.0, "female": 0.98, "other": 0.02},
    "perinatal": {"male": 0.5, "female": 0.5, "other": 0.1},
}

CATEGORY_ALIASES = {
    "cardiology": "cardiovascular",
    "pulmonology": "respiratory",
    "behavioral_health": "mental_health",
    "immunology": "factors_influencing",
}

KEYWORD_PREVALENCE_OVERRIDES = [
    ("hypertens", 0.28),
    ("type 2 diabetes", 0.18),
    ("type ii diabetes", 0.18),
    ("diabetes mellitus", 0.16),
    ("obesity", 0.22),
    ("hyperlipidemia", 0.18),
    ("heart failure", 0.14),
    ("ischemic heart disease", 0.14),
    ("ischaemic heart disease", 0.14),
    ("depress", 0.15),
    ("anxiety", 0.16),
    ("copd", 0.12),
    ("asthma", 0.12),
    ("chronic kidney disease", 0.12),
    ("kidney disease", 0.1),
    ("pregnancy", 0.08),
    ("gestational", 0.08),
    ("anemia", 0.1),
]

EXCLUDED_CATEGORIES = {"external_causes", "transport"}

CONDITION_SEVERITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "heart_failure": {
        "type": "nyha_class",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "449868002", "display": "NYHA class I"},
            {"code": "449869005", "display": "NYHA class II"},
            {"code": "449870006", "display": "NYHA class III"},
            {"code": "449871005", "display": "NYHA class IV"},
        ],
    },
    "asthma": {
        "type": "asthma_severity",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "370219009", "display": "Mild intermittent asthma"},
            {"code": "370220003", "display": "Mild persistent asthma"},
            {"code": "370221004", "display": "Moderate persistent asthma"},
            {"code": "370222006", "display": "Severe persistent asthma"},
        ],
    },
    "copd": {
        "type": "gold_stage",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "460050000", "display": "GOLD stage 1 mild COPD"},
            {"code": "460060004", "display": "GOLD stage 2 moderate COPD"},
            {"code": "460061000", "display": "GOLD stage 3 severe COPD"},
            {"code": "460062007", "display": "GOLD stage 4 very severe COPD"},
        ],
    },
    "ckd": {
        "type": "ckd_stage",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "431855005", "display": "Chronic kidney disease stage 1"},
            {"code": "431856006", "display": "Chronic kidney disease stage 2"},
            {"code": "431857002", "display": "Chronic kidney disease stage 3"},
            {"code": "431858007", "display": "Chronic kidney disease stage 4"},
            {"code": "431859004", "display": "Chronic kidney disease stage 5"},
        ],
    },
    "cancer_stage": {
        "type": "cancer_stage",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "260998006", "display": "Stage I malignant neoplasm"},
            {"code": "260999003", "display": "Stage II malignant neoplasm"},
            {"code": "261000000", "display": "Stage III malignant neoplasm"},
            {"code": "261001001", "display": "Stage IV malignant neoplasm"},
        ],
    },
    "depression_severity": {
        "type": "depression_severity",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "162561002", "display": "Mild depression"},
            {"code": "162562009", "display": "Moderate depression"},
            {"code": "162563004", "display": "Severe depression"},
        ],
    },
    "anxiety_severity": {
        "type": "anxiety_severity",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "371924009", "display": "Mild anxiety"},
            {"code": "371925005", "display": "Moderate anxiety"},
            {"code": "371926006", "display": "Severe anxiety"},
        ],
    },
    "diabetes_control": {
        "type": "diabetes_control",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "165679004", "display": "Diabetes well controlled"},
            {"code": "165680001", "display": "Diabetes reasonably controlled"},
            {"code": "165681002", "display": "Diabetes poorly controlled"},
        ],
    },
    "pregnancy_trimester": {
        "type": "pregnancy_stage",
        "code_system": "http://snomed.info/sct",
        "levels": [
            {"code": "71315007", "display": "First trimester of pregnancy"},
            {"code": "28024001", "display": "Second trimester of pregnancy"},
            {"code": "179049000", "display": "Third trimester of pregnancy"},
        ],
    },
}

CONDITION_SEVERITY_RULES = [
    {"keywords": ["heart failure"], "profile": "heart_failure"},
    {"keywords": ["chronic heart failure"], "profile": "heart_failure"},
    {"keywords": ["asthma"], "profile": "asthma"},
    {"keywords": ["chronic obstructive pulmonary disease"], "profile": "copd"},
    {"keywords": ["copd"], "profile": "copd"},
    {"keywords": ["chronic kidney disease"], "profile": "ckd"},
    {"keywords": ["kidney disease"], "profile": "ckd"},
    {"keywords": ["malignant neoplasm"], "profile": "cancer_stage"},
    {"keywords": ["cancer"], "profile": "cancer_stage"},
    {"keywords": ["depress"], "profile": "depression_severity"},
    {"keywords": ["anxiety"], "profile": "anxiety_severity"},
    {"keywords": ["diabetes"], "profile": "diabetes_control"},
    {"keywords": ["pregnancy"], "profile": "pregnancy_trimester", "category": "obstetrics"},
]


STAGE_PROFILE_TYPES = {"nyha_class", "cancer_stage", "gold_stage", "ckd_stage", "pregnancy_stage"}

VISIT_LOCATION_SUFFIXES = ["Clinic", "Medical Center", "Health Center", "Care Group", "Practice", "Institute"]

ENCOUNTER_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "wellness": {
        "type": "Wellness Visit",
        "reason_options": [
            "Annual preventive health exam",
            "Preventive care assessment",
            "Health maintenance check",
        ],
        "stop_code": "147",
        "stop_description": "Preventive Medicine",
        "service_category": "A",
        "department": "Preventive Medicine",
        "categories": [],
    },
    "primary_care": {
        "type": "Primary Care Follow-up",
        "reason_options": [
            "Chronic disease management",
            "Medication management",
            "Multi-condition follow-up",
        ],
        "stop_code": "323",
        "stop_description": "Primary Care",
        "service_category": "A",
        "department": "Primary Care",
        "categories": [
            "cardiometabolic",
            "endocrine",
            "respiratory",
            "mental_health",
            "gastroenterology",
            "dermatology",
            "musculoskeletal",
            "genitourinary",
            "infectious_disease",
            "symptoms",
            "factors_influencing",
            "misc",
        ],
    },
    "cardiology": {
        "type": "Cardiology Clinic",
        "reason_options": [
            "Coronary artery disease follow-up",
            "Heart failure management",
            "Cardiac risk assessment",
        ],
        "stop_code": "303",
        "stop_description": "Cardiology",
        "service_category": "A",
        "department": "Cardiology",
        "categories": ["cardiometabolic", "cardiovascular"],
    },
    "endocrinology": {
        "type": "Endocrinology Follow-up",
        "reason_options": [
            "Diabetes management",
            "Thyroid disorder follow-up",
        ],
        "stop_code": "312",
        "stop_description": "Endocrinology",
        "service_category": "A",
        "department": "Endocrinology",
        "categories": ["endocrine"],
    },
    "pulmonology": {
        "type": "Pulmonology Clinic",
        "reason_options": [
            "COPD management",
            "Asthma control visit",
            "Pulmonary function review",
        ],
        "stop_code": "332",
        "stop_description": "Pulmonary Disease",
        "service_category": "A",
        "department": "Pulmonology",
        "categories": ["respiratory"],
    },
    "behavioral_health": {
        "type": "Behavioral Health Session",
        "reason_options": [
            "Psychotherapy session",
            "Behavioral health follow-up",
            "Medication management",
        ],
        "stop_code": "167",
        "stop_description": "Mental Health Clinic",
        "service_category": "A",
        "department": "Behavioral Health",
        "categories": ["mental_health"],
    },
    "neurology": {
        "type": "Neurology Clinic",
        "reason_options": [
            "Seizure disorder follow-up",
            "Neuropathy assessment",
            "Stroke recovery visit",
        ],
        "stop_code": "345",
        "stop_description": "Neurology",
        "service_category": "A",
        "department": "Neurology",
        "categories": ["neurology"],
    },
    "ophthalmology": {
        "type": "Ophthalmology Clinic",
        "reason_options": [
            "Diabetic retinal exam",
            "Glaucoma monitoring",
            "Vision change evaluation",
        ],
        "stop_code": "407",
        "stop_description": "Ophthalmology",
        "service_category": "A",
        "department": "Ophthalmology",
        "categories": ["ophthalmology_otology"],
    },
    "dermatology": {
        "type": "Dermatology Clinic",
        "reason_options": [
            "Skin condition follow-up",
            "Lesion assessment",
        ],
        "stop_code": "302",
        "stop_description": "Dermatology",
        "service_category": "A",
        "department": "Dermatology",
        "categories": ["dermatology"],
    },
    "gastroenterology": {
        "type": "Gastroenterology Consult",
        "reason_options": [
            "IBD management",
            "Liver disease follow-up",
        ],
        "stop_code": "316",
        "stop_description": "Gastroenterology",
        "service_category": "A",
        "department": "Gastroenterology",
        "categories": ["gastroenterology"],
    },
    "orthopedics": {
        "type": "Orthopedic Visit",
        "reason_options": [
            "Joint pain evaluation",
            "Post-injury assessment",
        ],
        "stop_code": "411",
        "stop_description": "Orthopedics",
        "service_category": "A",
        "department": "Orthopedics",
        "categories": ["musculoskeletal", "injury"],
    },
    "rehab": {
        "type": "Rehabilitation Therapy",
        "reason_options": [
            "Physical therapy session",
            "Post-stroke rehabilitation",
        ],
        "stop_code": "372",
        "stop_description": "Rehabilitation Medicine",
        "service_category": "A",
        "department": "Rehabilitation Services",
        "categories": ["musculoskeletal", "neurology"],
    },
    "urology": {
        "type": "Urology Clinic",
        "reason_options": [
            "Renal stone follow-up",
            "Benign prostatic hyperplasia consult",
        ],
        "stop_code": "436",
        "stop_description": "Urology",
        "service_category": "A",
        "department": "Urology",
        "categories": ["genitourinary"],
    },
    "nephrology": {
        "type": "Nephrology Clinic",
        "reason_options": [
            "Chronic kidney disease management",
            "Dialysis planning",
        ],
        "stop_code": "315",
        "stop_description": "Nephrology",
        "service_category": "A",
        "department": "Nephrology",
        "categories": ["genitourinary"],
    },
    "oncology": {
        "type": "Oncology Visit",
        "reason_options": [
            "Treatment response assessment",
            "Chemotherapy toxicity monitoring",
        ],
        "stop_code": "318",
        "stop_description": "Oncology",
        "service_category": "A",
        "department": "Oncology",
        "categories": ["oncology", "hematologic"],
    },
    "obstetrics": {
        "type": "Obstetrics Prenatal Visit",
        "reason_options": [
            "Routine prenatal care",
            "High-risk pregnancy management",
        ],
        "stop_code": "404",
        "stop_description": "Obstetrics/Gynecology",
        "service_category": "A",
        "department": "Obstetrics",
        "categories": ["obstetrics"],
    },
    "pediatrics": {
        "type": "Pediatric Visit",
        "reason_options": [
            "Well-child visit",
            "Developmental follow-up",
            "Chronic condition management",
        ],
        "stop_code": "420",
        "stop_description": "Pediatrics",
        "service_category": "A",
        "department": "Pediatrics",
        "categories": ["perinatal", "congenital"],
    },
    "urgent_care": {
        "type": "Urgent Care Visit",
        "reason_options": [
            "Acute symptom evaluation",
            "Injury evaluation",
        ],
        "stop_code": "203",
        "stop_description": "Urgent Care",
        "service_category": "A",
        "department": "Urgent Care",
        "categories": ["injury", "symptoms", "infectious_disease"],
    },
    "emergency": {
        "type": "Emergency Department Visit",
        "reason_options": [
            "Severe symptom evaluation",
            "Acute exacerbation",
        ],
        "stop_code": "130",
        "stop_description": "Emergency Department",
        "service_category": "E",
        "department": "Emergency Department",
        "categories": ["injury", "infectious_disease", "respiratory", "cardiovascular"],
    },
    "telehealth": {
        "type": "Telehealth Check-in",
        "reason_options": [
            "Remote monitoring",
            "Medication adjustment",
            "Care coordination",
        ],
        "stop_code": "179",
        "stop_description": "Telehealth",
        "service_category": "A",
        "department": "Telehealth Services",
        "categories": ["mental_health", "cardiometabolic", "factors_influencing"],
        "mode": "virtual",
    },
    "lab": {
        "type": "Laboratory Workup",
        "reason_options": [
            "Routine laboratory monitoring",
            "Therapeutic drug monitoring",
            "Diagnostic workup",
        ],
        "stop_code": "175",
        "stop_description": "Laboratory",
        "service_category": "A",
        "department": "Laboratory",
        "categories": [
            "cardiometabolic",
            "endocrine",
            "oncology",
            "hematologic",
            "genitourinary",
            "gastroenterology",
        ],
    },
    "imaging": {
        "type": "Imaging Study",
        "reason_options": [
            "Diagnostic imaging",
            "Surveillance imaging",
        ],
        "stop_code": "324",
        "stop_description": "Diagnostic Radiology",
        "service_category": "A",
        "department": "Imaging Services",
        "categories": ["oncology", "neurology", "musculoskeletal", "gastroenterology"],
    },
}

DEFAULT_VISIT_CONTRIBUTIONS: Dict[str, float] = {"primary_care": 0.5}

CONDITION_CATEGORY_VISIT_CONTRIBUTIONS: Dict[str, Dict[str, float]] = {
    "cardiometabolic": {"primary_care": 1.4, "cardiology": 0.6, "lab": 1.0, "telehealth": 0.3},
    "cardiovascular": {"cardiology": 1.2, "primary_care": 0.6, "lab": 0.6},
    "endocrine": {"primary_care": 0.8, "endocrinology": 1.0, "lab": 1.2},
    "respiratory": {"primary_care": 0.8, "pulmonology": 1.0, "urgent_care": 0.3, "emergency": 0.2},
    "mental_health": {"behavioral_health": 2.0, "telehealth": 1.1, "primary_care": 0.4},
    "neurology": {"neurology": 1.0, "primary_care": 0.5, "imaging": 0.6, "rehab": 0.5},
    "ophthalmology_otology": {"ophthalmology": 0.9, "primary_care": 0.3},
    "oncology": {"oncology": 1.3, "lab": 1.2, "imaging": 0.8, "primary_care": 0.4},
    "hematologic": {"oncology": 0.8, "lab": 1.3, "primary_care": 0.5},
    "gastroenterology": {"gastroenterology": 0.9, "primary_care": 0.6, "lab": 0.5, "imaging": 0.3},
    "dermatology": {"dermatology": 0.8, "primary_care": 0.4},
    "musculoskeletal": {"orthopedics": 0.9, "rehab": 0.8, "primary_care": 0.5},
    "genitourinary": {"urology": 0.9, "nephrology": 0.5, "primary_care": 0.6, "lab": 0.4},
    "obstetrics": {"obstetrics": 2.1, "primary_care": 0.4, "lab": 0.7},
    "perinatal": {"pediatrics": 1.5, "primary_care": 0.3},
    "congenital": {"pediatrics": 1.0, "primary_care": 0.4},
    "infectious_disease": {"primary_care": 0.7, "urgent_care": 0.4, "lab": 0.6},
    "symptoms": {"primary_care": 0.6, "urgent_care": 0.3},
    "injury": {"urgent_care": 0.7, "emergency": 0.3, "orthopedics": 0.6},
    "factors_influencing": {"primary_care": 0.5, "telehealth": 0.4},
    "misc": {"primary_care": 0.5},
}


def _normalize_condition_display(raw: str) -> str:
    if not raw:
        return ""
    value = raw.strip()
    value = value.replace("(disorder)", "").replace("(finding)", "")
    value = re.sub(r"\s+", " ", value)
    if value.isupper():
        value = value.title()
    return value.strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _icd10_with_dot(code: str) -> str:
    if not code:
        return ""
    normalized = code.strip().upper().replace(" ", "").replace(".", "")
    if not normalized:
        return ""
    if normalized.endswith("-"):
        normalized = normalized[:-1]
    if len(normalized) <= 3:
        return normalized
    return f"{normalized[:3]}.{normalized[3:]}"


def classify_icd10_category(code: str) -> str:
    if not code:
        return "misc"
    prefix = code[0].upper()
    if prefix in {"A", "B"}:
        return "infectious_disease"
    if prefix == "C":
        return "oncology"
    if prefix == "D":
        if len(code) > 1 and code[1].isdigit() and int(code[1]) <= 4:
            return "oncology"
        return "hematologic"
    if prefix == "E":
        return "endocrine"
    if prefix == "F":
        return "mental_health"
    if prefix == "G":
        return "neurology"
    if prefix == "H":
        return "ophthalmology_otology"
    if prefix == "I":
        return "cardiovascular"
    if prefix == "J":
        return "respiratory"
    if prefix == "K":
        return "gastroenterology"
    if prefix == "L":
        return "dermatology"
    if prefix == "M":
        return "musculoskeletal"
    if prefix == "N":
        return "genitourinary"
    if prefix == "O":
        return "obstetrics"
    if prefix == "P":
        return "perinatal"
    if prefix == "Q":
        return "congenital"
    if prefix == "R":
        return "symptoms"
    if prefix in {"S", "T"}:
        return "injury"
    if prefix == "V":
        return "transport"
    if prefix in {"W", "X", "Y"}:
        return "external_causes"
    if prefix == "Z":
        return "factors_influencing"
    return "misc"


def _determine_base_prevalence(display: str, category: str) -> float:
    base = CATEGORY_BASE_PREVALENCE.get(category, 0.05)
    lowered = display.lower()
    for keyword, override in KEYWORD_PREVALENCE_OVERRIDES:
        if keyword in lowered:
            base = max(base, override)
    return round(min(base, 0.95), 4)


def _determine_severity_template(display: str, category: str) -> Optional[Dict[str, Any]]:
    lowered = display.lower()
    for rule in CONDITION_SEVERITY_RULES:
        if rule.get("category") and rule["category"] != category:
            continue
        if all(keyword in lowered for keyword in rule["keywords"]):
            profile_key = rule["profile"]
            profile = CONDITION_SEVERITY_PROFILES.get(profile_key)
            if profile:
                return profile
    return None


def _normalize_condition_category(category: Optional[str]) -> str:
    if not category:
        return "misc"
    normalized = CATEGORY_ALIASES.get(category.lower(), category.lower())
    return normalized


def _augment_condition_entry(
    display: str,
    icd10_code: str,
    snomed_code: str,
    category_hint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source_category = (category_hint or classify_icd10_category(icd10_code)) or "misc"
    category = _normalize_condition_category(source_category)
    entry = {
        "display": display,
        "icd10": icd10_code,
        "snomed": snomed_code,
        "category": category,
        "source_category": source_category,
        "chapter": ICD10_CATEGORY_LABELS.get(category, category),
        "normalized": _normalize_text(display),
        "base_prevalence": _determine_base_prevalence(display, category),
        "age_weights": CATEGORY_AGE_WEIGHTS.get(category),
        "sex_weights": CATEGORY_SEX_BIASES.get(category),
        "severity_profile": _determine_severity_template(display, category),
        "metadata": metadata or {},
    }
    return entry


def _build_dynamic_condition_catalog() -> Dict[str, Dict[str, Any]]:
    try:
        icd_entries = load_icd10_conditions()
    except Exception:
        return {}

    icd_lookup_by_code: Dict[str, TerminologyEntry] = {}
    for entry in icd_entries:
        code = _icd10_with_dot(entry.code)
        if code and code not in icd_lookup_by_code:
            icd_lookup_by_code[code] = entry

    try:
        snomed_entries = load_snomed_conditions()
    except Exception:
        snomed_entries = []

    snomed_lookup: Dict[str, TerminologyEntry] = {}
    if snomed_entries:
        for entry in snomed_entries:
            norm = _normalize_text(entry.display)
            if not norm or norm in snomed_lookup:
                continue
            if len(entry.display) > 90:
                continue
            snomed_lookup[norm] = entry
    snomed_keys = list(snomed_lookup.keys())

    try:
        crosswalk = load_snomed_icd10_crosswalk()
    except Exception:
        crosswalk = {}

    catalog: Dict[str, Dict[str, Any]] = {}
    category_counts: Dict[str, int] = defaultdict(int)

    for curated in CONDITION_TERMS:
        display = _normalize_condition_display(curated["display"])
        icd_code = _icd10_with_dot(curated.get("icd10", ""))
        snomed_code = curated.get("snomed", "")
        metadata = {}
        if icd_code and icd_code in icd_lookup_by_code:
            metadata = dict(icd_lookup_by_code[icd_code].metadata)
        entry = _augment_condition_entry(display, icd_code, snomed_code, curated.get("category"), metadata)
        catalog[display] = entry
        category_counts[entry["category"]] += 1

    MAX_TOTAL = 600
    MAX_PER_CATEGORY = 80

    for entry in icd_entries:
        icd_code = _icd10_with_dot(entry.code)
        if not icd_code:
            continue
        display = _normalize_condition_display(entry.display)
        if not display or display in catalog:
            continue
        level = entry.metadata.get("level") if isinstance(entry.metadata, dict) else None
        if level and str(level).isdigit() and int(level) > 2:
            continue
        if len(display) > 140:
            continue
        category = classify_icd10_category(icd_code)
        if category in EXCLUDED_CATEGORIES:
            continue
        if category_counts[category] >= MAX_PER_CATEGORY:
            continue

        snomed_code = ""
        if icd_code in crosswalk and crosswalk[icd_code]:
            snomed_code = crosswalk[icd_code][0].code
        else:
            normalized_display = _normalize_text(display)
            curated_candidate = CURATED_CONDITION_LOOKUP.get(normalized_display)
            if curated_candidate:
                snomed_code = curated_candidate.get("snomed", "")
            if not snomed_code and normalized_display in snomed_lookup:
                snomed_code = snomed_lookup[normalized_display].code
            if not snomed_code and snomed_keys:
                best_match = difflib.get_close_matches(normalized_display, snomed_keys, n=1, cutoff=0.97)
                if best_match:
                    snomed_code = snomed_lookup[best_match[0]].code

        catalog_entry = _augment_condition_entry(
            display,
            icd_code,
            snomed_code,
            category,
            dict(entry.metadata),
        )
        catalog[display] = catalog_entry
        category_counts[category] += 1
        if len(catalog) >= MAX_TOTAL:
            break

    return catalog


@lru_cache(maxsize=1)
def _load_condition_catalog() -> Dict[str, Dict[str, Any]]:
    try:
        catalog = _build_dynamic_condition_catalog()
    except Exception:
        catalog = {}

    if not catalog:
        catalog = {
            _normalize_condition_display(entry["display"]): _augment_condition_entry(
                _normalize_condition_display(entry["display"]),
                _icd10_with_dot(entry.get("icd10", "")),
                entry.get("snomed", ""),
                entry.get("category"),
                {},
            )
            for entry in CONDITION_TERMS
        }
    return catalog


def get_condition_catalog() -> Dict[str, Dict[str, Any]]:
    return _load_condition_catalog()


CONDITION_CATALOG = LazyMapping(_load_condition_catalog)
CONDITION_NAMES = LazySequence(lambda: list(_load_condition_catalog().keys()))


@lru_cache(maxsize=1)
def _load_immunization_catalog() -> Dict[str, Dict[str, Any]]:
    return {entry["display"]: entry for entry in IMMUNIZATION_TERMS}


def get_immunization_catalog() -> Dict[str, Dict[str, Any]]:
    return _load_immunization_catalog()


IMMUNIZATION_CATALOG = LazyMapping(_load_immunization_catalog)
IMMUNIZATION_BY_CVX = LazyMapping(
    lambda: {entry.get("cvx"): entry for entry in _load_immunization_catalog().values() if entry.get("cvx")}
)
IMMUNIZATIONS = LazySequence(lambda: list(_load_immunization_catalog().keys()))


@lru_cache(maxsize=1)
def _load_procedure_catalog() -> Dict[str, Dict[str, Any]]:
    return {entry["display"]: entry for entry in PROCEDURE_TERMS}


PROCEDURE_CATALOG = LazyMapping(_load_procedure_catalog)
PROCEDURES = LazySequence(lambda: list(_load_procedure_catalog().keys()))


IMMUNIZATION_SERIES_DEFINITIONS = [
    {
        "name": "Hepatitis B Vaccine",
        "series_id": "hepB_primary",
        "cvx": "08",
        "series_type": "childhood",
        "min_age_months": 0,
        "max_age_months": 600,
        "catch_up_end_months": 240,
        "contraindications": ["yeast"],
        "route": "intramuscular",
        "doses": [
            {"age_months": 0, "coverage": 0.98},
            {"age_months": 1, "coverage": 0.96},
            {"age_months": 6, "coverage": 0.93},
        ],
        "titer": {
            "loinc": "5196-1",
            "display": "Hepatitis B surface Ab [Units/volume] in Serum",
            "probability": 0.25,
        },
    },
    {
        "name": "DTaP Vaccine",
        "series_id": "dtap_child",
        "cvx": "20",
        "series_type": "childhood",
        "min_age_months": 2,
        "max_age_months": 96,
        "catch_up_end_months": 144,
        "route": "intramuscular",
        "doses": [
            {"age_months": 2, "coverage": 0.97},
            {"age_months": 4, "coverage": 0.96},
            {"age_months": 6, "coverage": 0.95},
            {"age_months": 15, "coverage": 0.93},
            {"age_months": 48, "coverage": 0.9},
        ],
    },
    {
        "name": "Inactivated Polio Vaccine",
        "series_id": "ipv_child",
        "cvx": "10",
        "series_type": "childhood",
        "min_age_months": 2,
        "max_age_months": 192,
        "catch_up_end_months": 228,
        "route": "intramuscular",
        "doses": [
            {"age_months": 2, "coverage": 0.97},
            {"age_months": 4, "coverage": 0.95},
            {"age_months": 6, "coverage": 0.94},
            {"age_months": 48, "coverage": 0.9},
        ],
    },
    {
        "name": "Haemophilus influenzae type b Vaccine",
        "series_id": "hib_child",
        "cvx": "49",
        "series_type": "childhood",
        "min_age_months": 2,
        "max_age_months": 72,
        "catch_up_end_months": 60,
        "route": "intramuscular",
        "doses": [
            {"age_months": 2, "coverage": 0.96},
            {"age_months": 4, "coverage": 0.95},
            {"age_months": 12, "coverage": 0.94},
        ],
    },
    {
        "name": "Pneumococcal Conjugate Vaccine",
        "series_id": "pcv_child",
        "cvx": "133",
        "series_type": "childhood",
        "min_age_months": 2,
        "max_age_months": 72,
        "catch_up_end_months": 84,
        "route": "intramuscular",
        "doses": [
            {"age_months": 2, "coverage": 0.96},
            {"age_months": 4, "coverage": 0.95},
            {"age_months": 6, "coverage": 0.94},
            {"age_months": 12, "coverage": 0.92},
        ],
    },
    {
        "name": "MMR Vaccine",
        "series_id": "mmr_child",
        "cvx": "03",
        "series_type": "childhood",
        "min_age_months": 12,
        "max_age_months": 216,
        "catch_up_end_months": 240,
        "route": "subcutaneous",
        "contraindications": ["gelatin"],
        "doses": [
            {"age_months": 12, "coverage": 0.94},
            {"age_months": 48, "coverage": 0.92},
        ],
    },
    {
        "name": "Varicella Vaccine",
        "series_id": "varicella_child",
        "cvx": "21",
        "series_type": "childhood",
        "min_age_months": 12,
        "max_age_months": 216,
        "catch_up_end_months": 240,
        "route": "subcutaneous",
        "contraindications": ["gelatin"],
        "doses": [
            {"age_months": 12, "coverage": 0.93},
            {"age_months": 48, "coverage": 0.9},
        ],
    },
    {
        "name": "HPV Vaccine",
        "series_id": "hpv_adolescent",
        "cvx": "62",
        "series_type": "adolescent",
        "min_age_months": 132,
        "max_age_months": 312,
        "catch_up_end_months": 432,
        "route": "intramuscular",
        "doses": [
            {"age_months": 132, "coverage": 0.85},
            {"age_months": 138, "coverage": 0.82},
            {"age_months": 144, "coverage": 0.75},
        ],
        "two_dose_cutoff_months": 180,
    },
    {
        "name": "COVID-19 mRNA Vaccine",
        "series_id": "covid_primary",
        "cvx": "207",
        "series_type": "adult",
        "min_age_months": 192,
        "route": "intramuscular",
        "doses": [
            {"age_months": 192, "coverage": 0.92},
            {"age_months": 192, "offset_days": 28, "coverage": 0.9},
        ],
    },
    {
        "name": "Zoster Vaccine",
        "series_id": "zoster_senior",
        "cvx": "187",
        "series_type": "adult",
        "min_age_months": 600,
        "route": "intramuscular",
        "doses": [
            {"age_months": 600, "coverage": 0.75},
            {"age_months": 602, "coverage": 0.72},
        ],
    },
]

IMMUNIZATION_ADMIN_SITES = [
    "left deltoid",
    "right deltoid",
    "left vastus lateralis",
    "right vastus lateralis",
    "left gluteus",
]

IMMUNIZATION_RECURRENT_DEFINITIONS = [
    {
        "name": "Seasonal Influenza Vaccine",
        "series_id": "influenza_seasonal",
        "cvx": "140",
        "min_age_months": 6,
        "route": "intramuscular",
        "series_type": "seasonal",
        "interval_years": 1,
        "max_years": 5,
        "season_month": 10,
        "coverage": 0.68,
        "contraindications": ["egg"],
    },
    {
        "name": "Tdap Vaccine",
        "series_id": "tdap_booster",
        "cvx": "115",
        "min_age_months": 132,
        "route": "intramuscular",
        "series_type": "booster",
        "interval_years": 10,
        "max_years": 40,
        "coverage": 0.8,
    },
    {
        "name": "COVID-19 mRNA Vaccine",
        "series_id": "covid_booster",
        "cvx": "207",
        "min_age_months": 192,
        "route": "intramuscular",
        "series_type": "booster",
        "interval_years": 1,
        "max_years": 3,
        "coverage": 0.7,
    },
    {
        "name": "Pneumococcal Conjugate Vaccine",
        "series_id": "pcv_senior",
        "cvx": "133",
        "min_age_months": 780,
        "route": "intramuscular",
        "series_type": "adult",
        "interval_years": 10,
        "max_years": 1,
        "coverage": 0.7,
        "target_categories": {"respiratory", "cardiometabolic"},
    },
]

@lru_cache(maxsize=1)
def _load_allergen_entries_cached() -> List[Dict[str, Any]]:
    try:
        loader_entries = load_allergen_entries()
    except Exception:  # pragma: no cover - loader fallback
        loader_entries = []

    if loader_entries:
        return [
            {
                "display": entry.display,
                "rxnorm_code": str(entry.code) if entry.code else "",
                "unii_code": entry.metadata.get("unii", ""),
                "category": entry.metadata.get("category", ""),
                "snomed_code": entry.metadata.get("snomed_code", ""),
                "rxnorm_name": entry.metadata.get("rxnorm_name", entry.display),
            }
            for entry in loader_entries
        ]

    return [
        {
            "display": item.get("display"),
            "rxnorm_code": str(item.get("rxnorm", "")),
            "unii_code": item.get("unii", ""),
            "category": item.get("category", "fallback"),
            "snomed_code": item.get("snomed", ""),
            "rxnorm_name": item.get("display"),
        }
        for item in FALLBACK_ALLERGEN_TERMS
    ]


@lru_cache(maxsize=1)
def _load_allergen_catalog() -> Dict[str, Dict[str, Any]]:
    entries = _load_allergen_entries_cached()
    return {entry["display"]: entry for entry in entries}


def get_allergen_catalog() -> Dict[str, Dict[str, Any]]:
    return _load_allergen_catalog()


ALLERGEN_ENTRIES = LazySequence(_load_allergen_entries_cached)
ALLERGEN_CATALOG = LazyMapping(_load_allergen_catalog)
ALLERGY_SUBSTANCES = LazySequence(lambda: list(_load_allergen_catalog().keys()))


@lru_cache(maxsize=1)
def _load_allergy_reactions() -> List[Dict[str, Any]]:
    try:
        reactions = load_allergy_reaction_entries()
    except Exception:  # pragma: no cover - loader fallback
        reactions = []

    if not reactions:
        reactions = [
            {"display": "Anaphylaxis", "code": "", "system": ""},
            {"display": "Urticaria", "code": "", "system": ""},
            {"display": "Angioedema", "code": "", "system": ""},
            {"display": "Wheezing", "code": "", "system": ""},
            {"display": "Shortness of breath", "code": "", "system": ""},
            {"display": "Nausea", "code": "", "system": ""},
            {"display": "Vomiting", "code": "", "system": ""},
            {"display": "Rash", "code": "", "system": ""},
            {"display": "Itching", "code": "", "system": ""},
        ]
    return reactions


ALLERGY_REACTIONS = LazySequence(_load_allergy_reactions)
ALLERGY_SEVERITIES = [
    {"display": "mild", "code": "255604002", "system": "http://snomed.info/sct"},
    {"display": "moderate", "code": "6736007", "system": "http://snomed.info/sct"},
    {"display": "severe", "code": "24484000", "system": "http://snomed.info/sct"},
]

@lru_cache(maxsize=1)
def _load_medication_catalog() -> Dict[str, Dict[str, Any]]:
    try:
        loader_entries = load_medication_entries()
    except Exception:  # pragma: no cover - loader fallback
        loader_entries = []

    catalog: Dict[str, Dict[str, Any]] = {}
    if loader_entries:
        for entry in loader_entries:
            metadata = dict(entry.metadata)
            med_record = {
                "display": entry.display,
                "rxnorm_code": entry.code,
                "rxnorm": entry.code,
                "ndc": metadata.get("ndc_example") or metadata.get("ndc"),
                "ndc_example": metadata.get("ndc_example") or metadata.get("ndc"),
                "therapeutic_class": metadata.get("therapeutic_class", ""),
                "rxnorm_name": metadata.get("rxnorm_name", entry.display),
            }
            catalog[entry.display] = med_record
            alias = entry.display.replace(" ", "_")
            catalog.setdefault(alias, med_record)
            for alias_name in metadata.get("aliases", []):
                catalog.setdefault(alias_name, med_record)
    else:
        for item in FALLBACK_MEDICATION_TERMS:
            display = item.get("display")
            med_record = {
                "display": display,
                "rxnorm_code": str(item.get("rxnorm", "")) if item.get("rxnorm") else "",
                "rxnorm": item.get("rxnorm"),
                "ndc": item.get("ndc"),
                "ndc_example": item.get("ndc"),
                "therapeutic_class": item.get("therapeutic_class", ""),
            }
            catalog[display] = med_record
            catalog.setdefault(display.replace(" ", "_"), med_record)

    for item in FALLBACK_MEDICATION_TERMS:
        display = item.get("display")
        if display not in catalog:
            med_record = {
                "display": display,
                "rxnorm_code": str(item.get("rxnorm", "")) if item.get("rxnorm") else "",
                "rxnorm": item.get("rxnorm"),
                "ndc": item.get("ndc"),
                "ndc_example": item.get("ndc"),
                "therapeutic_class": item.get("therapeutic_class", ""),
            }
            catalog[display] = med_record
            catalog.setdefault(display.replace(" ", "_"), med_record)

    return catalog


MEDICATION_CATALOG = LazyMapping(_load_medication_catalog)
MEDICATIONS = LazySequence(
    lambda: sorted({record["display"] for record in _load_medication_catalog().values()})
)


def get_medication_catalog() -> Dict[str, Dict[str, Any]]:
    return _load_medication_catalog()


@lru_cache(maxsize=1)
def _load_lab_test_entries_cached() -> List[Dict[str, Any]]:
    try:
        return list(load_lab_test_entries())
    except Exception:  # pragma: no cover - loader fallback
        return []


@lru_cache(maxsize=1)
def _load_lab_test_catalog() -> Dict[str, Dict[str, Any]]:
    return {entry["name"]: entry for entry in _load_lab_test_entries_cached()}


LAB_TEST_ENTRIES = LazySequence(_load_lab_test_entries_cached)
LAB_TEST_CATALOG = LazyMapping(_load_lab_test_catalog)


def get_lab_test_catalog() -> Dict[str, Dict[str, Any]]:
    return _load_lab_test_catalog()


def build_lab_test(
    name: str,
    *,
    loinc: Optional[str] = None,
    units: str = "",
    normal_range: Optional[tuple[float, float]] = None,
    critical_low: Optional[float] = None,
    critical_high: Optional[float] = None,
) -> Dict[str, Any]:
    base = {
        "name": name,
        "loinc": loinc or "",
        "units": units,
        "normal_range": normal_range or (0, 1),
        "critical_low": critical_low,
        "critical_high": critical_high,
    }
    entry = LAB_TEST_CATALOG.get(name)
    if entry:
        base["loinc"] = entry.get("loinc", base["loinc"])
        base["units"] = entry.get("units", base["units"])
        base["normal_range"] = entry.get("normal_range", base["normal_range"])
        base["critical_low"] = entry.get("critical_low", base["critical_low"])
        base["critical_high"] = entry.get("critical_high", base["critical_high"])
    return base


def resolve_medication_entry(name: str) -> Tuple[str, Dict[str, Any]]:
    candidates = [name, name.replace("_", " "), name.replace("-", " ")]
    lower_candidates = [candidate.lower() for candidate in candidates]
    for candidate in candidates:
        entry = MEDICATION_CATALOG.get(candidate)
        if entry:
            return entry["display"], entry
    for display, entry in MEDICATION_CATALOG.items():
        if display.lower() in lower_candidates:
            return entry["display"], entry
    return name, {}


THERAPEUTIC_CLASS_ROUTE_MAP = {
    "inhaled_combo": "inhaled",
    "inhaled_steroid": "inhaled",
    "long_acting_anticholinergic": "inhaled",
    "bronchodilator": "inhaled",
    "basal_insulin": "subcutaneous",
    "rapid_insulin": "subcutaneous",
    "glp1_agonist": "subcutaneous",
    "chemotherapy": "intravenous",
    "targeted_therapy": "intravenous",
    "biologic_dmard": "subcutaneous",
    "emergency_anaphylaxis": "intramuscular",
}

MEDICATION_MONITORING_MAP = {
    "anticoagulant": ["Coagulation_Panel"],
    "antiplatelet": ["Coagulation_Panel"],
    "statin": ["Lipid_Panel", "Liver_Function_Panel"],
    "ace_inhibitor": ["Renal_Function_Panel"],
    "arb": ["Renal_Function_Panel"],
    "thiazide_diuretic": ["Renal_Function_Panel"],
    "loop_diuretic": ["Renal_Function_Panel"],
    "aldosterone_antagonist": ["Renal_Function_Panel"],
    "sglt2_inhibitor": ["Diabetes_Monitoring"],
    "basal_insulin": ["Diabetes_Monitoring"],
    "rapid_insulin": ["Diabetes_Monitoring"],
    "glp1_agonist": ["Diabetes_Monitoring"],
    "beta_blocker": ["Cardiac_Markers"],
    "chemotherapy": ["Oncology_Tumor_Markers", "Complete_Blood_Count"],
    "targeted_therapy": ["Oncology_Tumor_Markers"],
    "biologic_dmard": ["Inflammatory_Markers"],
    "glucocorticoid": ["Inflammatory_Markers"],
    "thyroid_replacement": ["Thyroid_Function"],
    "bronchodilator": ["Pulmonary_Function"],
    "inhaled_combo": ["Pulmonary_Function"],
    "inhaled_steroid": ["Pulmonary_Function"],
    "long_acting_anticholinergic": ["Pulmonary_Function"],
    "antiviral": ["Inflammatory_Markers"],
}
# PHASE 2: Comprehensive laboratory panels with clinical accuracy
COMPREHENSIVE_LAB_PANELS = {
    "Basic_Metabolic_Panel": {
        "tests": [
            {"name": "Sodium", "loinc": "2951-2", "units": "mmol/L", "normal_range": (136, 145), "critical_low": 120, "critical_high": 160},
            {"name": "Potassium", "loinc": "2823-3", "units": "mmol/L", "normal_range": (3.5, 5.1), "critical_low": 2.5, "critical_high": 6.5},
            {"name": "Chloride", "loinc": "2075-0", "units": "mmol/L", "normal_range": (98, 107), "critical_low": 80, "critical_high": 120},
            {"name": "CO2", "loinc": "2028-9", "units": "mmol/L", "normal_range": (22, 28), "critical_low": 15, "critical_high": 40},
            {"name": "BUN", "loinc": "3094-0", "units": "mg/dL", "normal_range": (7, 20), "critical_low": None, "critical_high": 100},
            {"name": "Creatinine", "loinc": "2160-0", "units": "mg/dL", "normal_range": (0.7, 1.3), "critical_low": None, "critical_high": 10},
            {"name": "Glucose", "loinc": "2345-7", "units": "mg/dL", "normal_range": (70, 99), "critical_low": 40, "critical_high": 500},
            {"name": "eGFR", "loinc": "33914-3", "units": "mL/min/1.73m²", "normal_range": (90, 120), "critical_low": 15, "critical_high": None}
        ],
        "frequency": "routine",
        "indications": ["routine_screening", "kidney_function", "electrolyte_monitoring"]
    },
    
    "Complete_Blood_Count": {
        "tests": [
            {"name": "WBC", "loinc": "6690-2", "units": "K/uL", "normal_range": (4.5, 11.0), "critical_low": 1.0, "critical_high": 30.0},
            {"name": "RBC", "loinc": "789-8", "units": "M/uL", "normal_range": (4.2, 5.4), "critical_low": 2.0, "critical_high": 7.0},
            {"name": "Hemoglobin", "loinc": "718-7", "units": "g/dL", "normal_range": (12.0, 15.5), "critical_low": 5.0, "critical_high": 20.0},
            {"name": "Hematocrit", "loinc": "4544-3", "units": "%", "normal_range": (36.0, 46.0), "critical_low": 15.0, "critical_high": 60.0},
            {"name": "Platelets", "loinc": "777-3", "units": "K/uL", "normal_range": (150, 450), "critical_low": 20, "critical_high": 1000},
            {"name": "MCV", "loinc": "787-2", "units": "fL", "normal_range": (80, 100), "critical_low": None, "critical_high": None},
            {"name": "MCH", "loinc": "785-6", "units": "pg", "normal_range": (27, 32), "critical_low": None, "critical_high": None},
            {"name": "MCHC", "loinc": "786-4", "units": "g/dL", "normal_range": (32, 36), "critical_low": None, "critical_high": None}
        ],
        "frequency": "routine",
        "indications": ["anemia_workup", "bleeding_disorders", "infection_monitoring", "routine_screening"]
    },
    
    "Lipid_Panel": {
        "tests": [
            {"name": "Total_Cholesterol", "loinc": "2093-3", "units": "mg/dL", "normal_range": (125, 200), "critical_low": None, "critical_high": 500},
            {"name": "HDL_Cholesterol", "loinc": "2085-9", "units": "mg/dL", "normal_range": (40, 60), "critical_low": None, "critical_high": None},
            {"name": "LDL_Cholesterol", "loinc": "2089-1", "units": "mg/dL", "normal_range": (0, 100), "critical_low": None, "critical_high": 400},
            {"name": "Triglycerides", "loinc": "2571-8", "units": "mg/dL", "normal_range": (0, 150), "critical_low": None, "critical_high": 1000},
            {"name": "Non_HDL_Cholesterol", "loinc": "13457-7", "units": "mg/dL", "normal_range": (0, 130), "critical_low": None, "critical_high": None}
        ],
        "frequency": "annual",
        "indications": ["cardiovascular_risk", "diabetes_monitoring", "statin_therapy"]
    },
    
    "Liver_Function_Panel": {
        "tests": [
            {"name": "ALT", "loinc": "1742-6", "units": "U/L", "normal_range": (7, 56), "critical_low": None, "critical_high": 1000},
            {"name": "AST", "loinc": "1920-8", "units": "U/L", "normal_range": (10, 40), "critical_low": None, "critical_high": 1000},
            {"name": "Alkaline_Phosphatase", "loinc": "6768-6", "units": "U/L", "normal_range": (44, 147), "critical_low": None, "critical_high": 1000},
            {"name": "Total_Bilirubin", "loinc": "1975-2", "units": "mg/dL", "normal_range": (0.3, 1.2), "critical_low": None, "critical_high": 20},
            {"name": "Direct_Bilirubin", "loinc": "1968-7", "units": "mg/dL", "normal_range": (0.0, 0.4), "critical_low": None, "critical_high": None},
            {"name": "Albumin", "loinc": "1751-7", "units": "g/dL", "normal_range": (3.5, 5.0), "critical_low": 2.0, "critical_high": None}
        ],
        "frequency": "as_needed",
        "indications": ["liver_disease", "medication_monitoring", "hepatitis_screening"]
    },
    
    "Thyroid_Function": {
        "tests": [
            {"name": "TSH", "loinc": "3016-3", "units": "mIU/L", "normal_range": (0.27, 4.20), "critical_low": 0.01, "critical_high": 100},
            {"name": "Free_T4", "loinc": "3024-7", "units": "ng/dL", "normal_range": (0.93, 1.70), "critical_low": 0.2, "critical_high": 7.0},
            {"name": "Free_T3", "loinc": "3051-0", "units": "pg/mL", "normal_range": (2.0, 4.4), "critical_low": None, "critical_high": None}
        ],
        "frequency": "annual",
        "indications": ["thyroid_disorders", "fatigue_workup", "weight_changes"]
    },
    
    "Diabetes_Monitoring": {
        "tests": [
            {"name": "Hemoglobin_A1c", "loinc": "4548-4", "units": "%", "normal_range": (4.0, 5.6), "critical_low": None, "critical_high": 15},
            {"name": "Fasting_Glucose", "loinc": "1558-6", "units": "mg/dL", "normal_range": (70, 99), "critical_low": 40, "critical_high": 500},
            {"name": "Random_Glucose", "loinc": "2345-7", "units": "mg/dL", "normal_range": (70, 140), "critical_low": 40, "critical_high": 500},
            {"name": "Microalbumin", "loinc": "14957-5", "units": "mg/g", "normal_range": (0, 30), "critical_low": None, "critical_high": None}
        ],
        "frequency": "quarterly",
        "indications": ["diabetes_management", "prediabetes_screening"]
    },
    
    "Cardiac_Markers": {
        "tests": [
            {"name": "Troponin_I", "loinc": "10839-9", "units": "ng/mL", "normal_range": (0.0, 0.04), "critical_low": None, "critical_high": 50},
            {"name": "CK_MB", "loinc": "13969-1", "units": "ng/mL", "normal_range": (0.0, 6.3), "critical_low": None, "critical_high": 300},
            {"name": "BNP", "loinc": "30934-4", "units": "pg/mL", "normal_range": (0, 100), "critical_low": None, "critical_high": 5000},
            {"name": "NT_proBNP", "loinc": "33762-6", "units": "pg/mL", "normal_range": (0, 125), "critical_low": None, "critical_high": 35000}
        ],
        "frequency": "acute",
        "indications": ["chest_pain", "heart_failure", "myocardial_infarction"]
    },
    
    "Inflammatory_Markers": {
        "tests": [
            {"name": "ESR", "loinc": "4537-7", "units": "mm/hr", "normal_range": (0, 30), "critical_low": None, "critical_high": 150},
            {"name": "CRP", "loinc": "1988-5", "units": "mg/L", "normal_range": (0.0, 3.0), "critical_low": None, "critical_high": 500},
            {"name": "Procalcitonin", "loinc": "33747-0", "units": "ng/mL", "normal_range": (0.0, 0.25), "critical_low": None, "critical_high": 100}
        ],
        "frequency": "as_needed",
        "indications": ["infection", "inflammation", "sepsis_workup"]
    },

    # Phase 4: Specialty lab panels
    "Cardiology_Followup": {
        "tests": [
            {"name": "BNP", "loinc": "30934-4", "units": "pg/mL", "normal_range": (0, 100), "critical_low": None, "critical_high": 5000},
            {"name": "NT_proBNP", "loinc": "33762-6", "units": "pg/mL", "normal_range": (0, 125), "critical_low": None, "critical_high": 35000},
            {"name": "Troponin_T_High_Sensitivity", "loinc": "67151-1", "units": "ng/L", "normal_range": (0, 14), "critical_low": None, "critical_high": 500},
            {"name": "Lipid_Panel_Advanced", "loinc": "13457-7", "units": "mg/dL", "normal_range": (0, 100), "critical_low": None, "critical_high": 400}
        ],
        "frequency": "quarterly",
        "indications": ["heart_failure", "post_mi_monitoring", "cardiology_followup"]
    },
    "Oncology_Tumor_Markers": {
        "tests": [
            {"name": "CEA", "loinc": "2039-6", "units": "ng/mL", "normal_range": (0.0, 5.0), "critical_low": None, "critical_high": 100},
            {"name": "CA_125", "loinc": "10334-1", "units": "U/mL", "normal_range": (0.0, 35.0), "critical_low": None, "critical_high": 200},
            {"name": "PSA_Total", "loinc": "2857-1", "units": "ng/mL", "normal_range": (0.0, 4.0), "critical_low": None, "critical_high": 50},
            {"name": "LDH", "loinc": "14804-9", "units": "U/L", "normal_range": (125, 220), "critical_low": None, "critical_high": 2000}
        ],
        "frequency": "as_needed",
        "indications": ["oncology_followup", "tumor_burden"]
    },
    "Behavioral_Health_Assessments": {
        "tests": [
            {"name": "PHQ9_Score", "loinc": "44249-1", "units": "score", "normal_range": (0, 4), "critical_low": None, "critical_high": 27},
            {"name": "GAD7_Score", "loinc": "70273-5", "units": "score", "normal_range": (0, 4), "critical_low": None, "critical_high": 21},
            {"name": "AUDIT_C", "loinc": "75626-2", "units": "score", "normal_range": (0, 4), "critical_low": None, "critical_high": 12}
        ],
        "frequency": "annual",
        "indications": ["behavioral_health", "substance_use_screening"]
    },
    "Pulmonary_Function": {
        "tests": [
            {"name": "FEV1", "loinc": "20150-9", "units": "L", "normal_range": (2.5, 4.0), "critical_low": 0.5, "critical_high": None},
            {"name": "FVC", "loinc": "19870-5", "units": "L", "normal_range": (3.0, 5.0), "critical_low": 1.0, "critical_high": None},
            {"name": "FEV1_FVC_Ratio", "loinc": "19926-5", "units": "%", "normal_range": (70, 100), "critical_low": 40, "critical_high": None}
        ],
        "frequency": "annual",
        "indications": ["copd_management", "asthma_monitoring"]
    }
}

COMPREHENSIVE_LAB_PANELS.update(
    {
        "Coagulation_Panel": {
            "tests": [
                build_lab_test(
                    "Prothrombin Time",
                    units="s",
                    normal_range=(10, 13),
                    critical_high=20,
                ),
                build_lab_test(
                    "International Normalized Ratio",
                    units="ratio",
                    normal_range=(0.9, 1.2),
                    critical_low=0.5,
                    critical_high=4.5,
                ),
                build_lab_test(
                    "Activated Partial Thromboplastin Time",
                    units="s",
                    normal_range=(25, 35),
                    critical_high=80,
                ),
                build_lab_test(
                    "D-Dimer",
                    units="ng/mL",
                    normal_range=(0, 500),
                    critical_high=1000,
                ),
            ],
            "frequency": "as_needed",
            "indications": ["anticoagulant_monitoring", "thromboembolic_risk"],
        },
        "Cardiac_Markers_Advanced": {
            "tests": [
                build_lab_test(
                    "B-Type Natriuretic Peptide",
                    units="pg/mL",
                    normal_range=(0, 100),
                    critical_high=1000,
                ),
                build_lab_test(
                    "N-terminal proBNP",
                    units="pg/mL",
                    normal_range=(0, 125),
                    critical_high=5000,
                ),
                build_lab_test(
                    "High Sensitivity Troponin I",
                    units="ng/L",
                    normal_range=(0, 14),
                    critical_high=100,
                ),
            ],
            "frequency": "as_needed",
            "indications": ["heart_failure", "acute_coronary_syndrome"],
        },
        "Metabolic_Nutrition": {
            "tests": [
                build_lab_test(
                    "Vitamin D 25-Hydroxy",
                    units="ng/mL",
                    normal_range=(30, 100),
                    critical_low=10,
                ),
            ],
            "frequency": "annual",
            "indications": ["osteoporosis_risk", "malnutrition"],
        },
        "Renal_Function_Panel": {
            "tests": [
                build_lab_test(
                    "Creatinine",
                    units="mg/dL",
                    normal_range=(0.7, 1.3),
                    critical_high=10,
                ),
                build_lab_test(
                    "BUN",
                    units="mg/dL",
                    normal_range=(7, 20),
                    critical_high=100,
                ),
                build_lab_test(
                    "eGFR",
                    units="mL/min/1.73m²",
                    normal_range=(90, 120),
                    critical_low=15,
                ),
                build_lab_test(
                    "Potassium",
                    units="mmol/L",
                    normal_range=(3.5, 5.1),
                    critical_low=2.5,
                    critical_high=6.5,
                ),
            ],
            "frequency": "quarterly",
            "indications": ["hypertension", "heart_failure", "diabetes"],
        },
        "Hematology_Iron": {
            "tests": [
                build_lab_test(
                    "Ferritin",
                    units="ng/mL",
                    normal_range=(30, 300),
                    critical_low=10,
                ),
                build_lab_test(
                    "Serum Iron",
                    units="ug/dL",
                    normal_range=(60, 170),
                    critical_low=30,
                    critical_high=300,
                ),
                build_lab_test(
                    "Total Iron Binding Capacity",
                    units="ug/dL",
                    normal_range=(240, 450),
                ),
                build_lab_test(
                    "Transferrin",
                    units="mg/dL",
                    normal_range=(200, 350),
                ),
            ],
            "frequency": "as_needed",
            "indications": ["anemia_workup", "iron_deficiency"],
        },
        "Sepsis_Markers": {
            "tests": [
                build_lab_test(
                    "Lactate",
                    units="mmol/L",
                    normal_range=(0.5, 2.2),
                    critical_high=4.0,
                ),
                build_lab_test(
                    "Procalcitonin",
                    units="ng/mL",
                    normal_range=(0, 0.5),
                    critical_high=10,
                ),
                build_lab_test(
                    "C-Reactive Protein High Sensitivity",
                    units="mg/L",
                    normal_range=(0, 3),
                    critical_high=50,
                ),
            ],
            "frequency": "as_needed",
            "indications": ["sepsis", "systemic_inflammation"],
        },
        "Endocrine": {
            "tests": [
                build_lab_test(
                    "Cortisol",
                    units="ug/dL",
                    normal_range=(5, 23),
                ),
                build_lab_test(
                    "TSH Receptor Antibody",
                    units="IU/L",
                    normal_range=(0, 1.75),
                ),
                build_lab_test(
                    "Free T3",
                    units="pg/mL",
                    normal_range=(2.0, 4.4),
                ),
            ],
            "frequency": "as_needed",
            "indications": ["endocrine_disorder", "thyroid_disorder"],
        },
    }
)

# Age and gender-specific reference range adjustments
AGE_GENDER_ADJUSTMENTS = {
    "Hemoglobin": {
        "male": {"normal_range": (13.5, 17.5)},
        "female": {"normal_range": (12.0, 15.5)},
        "pediatric": {"normal_range": (11.0, 14.0)}
    },
    "Hematocrit": {
        "male": {"normal_range": (41.0, 50.0)},
        "female": {"normal_range": (36.0, 46.0)},
        "pediatric": {"normal_range": (32.0, 42.0)}
    },
    "Creatinine": {
        "male": {"normal_range": (0.9, 1.3)},
        "female": {"normal_range": (0.7, 1.1)},
        "elderly": {"normal_range": (0.8, 1.4)}
    },
    "eGFR": {
        "elderly": {"normal_range": (60, 89)},
        "adult": {"normal_range": (90, 120)}
    }
}

# PHASE 2: Condition complexity modeling with staging and complications
CONDITION_COMPLEXITY_MODELS = {
    "Diabetes": {
        "stages": {
            "Prediabetes": {
                "criteria": {"hba1c_range": (5.7, 6.4), "fasting_glucose_range": (100, 125)},
                "complications": [],
                "medications": ["lifestyle_modification"],
                "monitoring": ["Diabetes_Monitoring"]
            },
            "Type_2_Diabetes_Early": {
                "criteria": {"hba1c_range": (6.5, 8.0), "years_since_diagnosis": (0, 5)},
                "complications": ["Microalbuminuria"],
                "medications": ["Metformin"],
                "monitoring": ["Diabetes_Monitoring", "Basic_Metabolic_Panel"]
            },
            "Type_2_Diabetes_Established": {
                "criteria": {"hba1c_range": (7.0, 10.0), "years_since_diagnosis": (5, 15)},
                "complications": ["Diabetic_Nephropathy", "Diabetic_Retinopathy", "Peripheral_Neuropathy"],
                "medications": ["Metformin", "Insulin", "Glipizide"],
                "monitoring": ["Diabetes_Monitoring", "Basic_Metabolic_Panel", "Lipid_Panel"]
            },
            "Type_2_Diabetes_Advanced": {
                "criteria": {"hba1c_range": (8.5, 15.0), "years_since_diagnosis": (15, 30)},
                "complications": ["End_Stage_Renal_Disease", "Diabetic_Foot_Ulcer", "Coronary_Artery_Disease"],
                "medications": ["Insulin", "multiple_agents"],
                "monitoring": ["Diabetes_Monitoring", "Cardiac_Markers", "Complete_Blood_Count"]
            }
        },
        "complications": {
            "Diabetic_Nephropathy": {"icd10": "E11.21", "progression_risk": 0.3},
            "Diabetic_Retinopathy": {"icd10": "E11.311", "progression_risk": 0.25},
            "Peripheral_Neuropathy": {"icd10": "E11.40", "progression_risk": 0.4},
            "Diabetic_Foot_Ulcer": {"icd10": "E11.621", "progression_risk": 0.15},
            "End_Stage_Renal_Disease": {"icd10": "N18.6", "progression_risk": 0.1}
        }
    },
    
    "Cancer": {
        "staging": {
            "TNM_Stage_I": {
                "criteria": {"tumor_size": "small", "lymph_nodes": "negative", "metastasis": "none"},
                "prognosis": "excellent",
                "treatment": ["surgery", "radiation"],
                "survival_5yr": 0.90
            },
            "TNM_Stage_II": {
                "criteria": {"tumor_size": "moderate", "lymph_nodes": "limited", "metastasis": "none"},
                "prognosis": "good", 
                "treatment": ["surgery", "chemotherapy", "radiation"],
                "survival_5yr": 0.75
            },
            "TNM_Stage_III": {
                "criteria": {"tumor_size": "large", "lymph_nodes": "extensive", "metastasis": "regional"},
                "prognosis": "fair",
                "treatment": ["chemotherapy", "radiation", "surgery"],
                "survival_5yr": 0.45
            },
            "TNM_Stage_IV": {
                "criteria": {"tumor_size": "any", "lymph_nodes": "any", "metastasis": "distant"},
                "prognosis": "poor",
                "treatment": ["palliative_chemotherapy", "supportive_care"],
                "survival_5yr": 0.15
            }
        },
        "subtypes": {
            "Breast_Cancer": {"icd10": "C50.911", "common_staging": ["TNM_Stage_I", "TNM_Stage_II"]},
            "Lung_Cancer": {"icd10": "C78.00", "common_staging": ["TNM_Stage_III", "TNM_Stage_IV"]},
            "Colon_Cancer": {"icd10": "C18.9", "common_staging": ["TNM_Stage_II", "TNM_Stage_III"]},
            "Prostate_Cancer": {"icd10": "C61", "common_staging": ["TNM_Stage_I", "TNM_Stage_II"]},
            "Pancreatic_Cancer": {"icd10": "C25.9", "common_staging": ["TNM_Stage_III", "TNM_Stage_IV"]}
        }
    },
    
    "Heart_Disease": {
        "risk_stratification": {
            "Low_Risk": {
                "criteria": {"framingham_score": (0, 10), "ejection_fraction": (55, 70)},
                "medications": ["lifestyle_modification", "statin"],
                "monitoring": ["Lipid_Panel"],
                "procedures": ["stress_test"]
            },
            "Moderate_Risk": {
                "criteria": {"framingham_score": (10, 20), "ejection_fraction": (40, 54)},
                "medications": ["statin", "ace_inhibitor", "beta_blocker"],
                "monitoring": ["Lipid_Panel", "Cardiac_Markers"],
                "procedures": ["echocardiogram", "cardiac_catheterization"]
            },
            "High_Risk": {
                "criteria": {"framingham_score": (20, 100), "ejection_fraction": (30, 39)},
                "medications": ["multiple_agents", "antiplatelet"],
                "monitoring": ["Cardiac_Markers", "Inflammatory_Markers"],
                "procedures": ["PCI", "CABG"]
            },
            "Heart_Failure": {
                "criteria": {"ejection_fraction": (0, 29), "nyha_class": (3, 4)},
                "medications": ["ace_inhibitor", "beta_blocker", "diuretic"],
                "monitoring": ["Cardiac_Markers", "Basic_Metabolic_Panel"],
                "procedures": ["device_therapy", "transplant_evaluation"]
            }
        },
        "complications": {
            "Myocardial_Infarction": {"icd10": "I21.9", "risk_factor": 3.0},
            "Heart_Failure": {"icd10": "I50.9", "risk_factor": 2.5},
            "Atrial_Fibrillation": {"icd10": "I48.91", "risk_factor": 1.8},
            "Stroke": {"icd10": "I64", "risk_factor": 2.2}
        }
    },
    
    "Hypertension": {
        "stages": {
            "Stage_1": {
                "criteria": {"systolic": (130, 139), "diastolic": (80, 89)},
                "medications": ["lifestyle_modification"],
                "target": {"systolic": 130, "diastolic": 80}
            },
            "Stage_2": {
                "criteria": {"systolic": (140, 179), "diastolic": (90, 119)},
                "medications": ["ace_inhibitor", "thiazide_diuretic"],
                "target": {"systolic": 130, "diastolic": 80}
            },
            "Hypertensive_Crisis": {
                "criteria": {"systolic": (180, 250), "diastolic": (120, 150)},
                "medications": ["multiple_agents", "emergency_treatment"],
                "target": {"systolic": 140, "diastolic": 90}
            }
        },
        "complications": {
            "Left_Ventricular_Hypertrophy": {"icd10": "I51.7", "risk": 0.3},
            "Chronic_Kidney_Disease": {"icd10": "N18.9", "risk": 0.25},
            "Retinopathy": {"icd10": "H35.039", "risk": 0.2}
        }
    }
    ,

    "Heart_Disease": {
        "stages": {
            "Chronic_Ischemic": {
                "criteria": {"ef_range": (45, 60), "nyha_class": 1},
                "monitoring": ["Cardiology_Followup", "Lipid_Panel"],
                "interventions": ["statin", "ace_inhibitor"],
                "complications": ["Arrhythmia"]
            },
            "Post_MI": {
                "criteria": {"ef_range": (30, 45), "nyha_class": 2},
                "monitoring": ["Cardiology_Followup", "Cardiac_Markers"],
                "interventions": ["beta_blocker", "dual_antiplatelet"],
                "complications": ["Heart_Failure", "Arrhythmia"]
            },
            "Advanced_Heart_Failure": {
                "criteria": {"ef_range": (0, 30), "nyha_class": 3},
                "monitoring": ["Cardiology_Followup", "Basic_Metabolic_Panel"],
                "interventions": ["ace_inhibitor", "device_therapy"],
                "complications": ["Renal_Dysfunction", "Hospitalization"]
            }
        },
        "complications": {
            "Arrhythmia": {"icd10": "I49.9", "progression_risk": 0.35},
            "Heart_Failure": {"icd10": "I50.9", "progression_risk": 0.25},
            "Renal_Dysfunction": {"icd10": "N18.3", "progression_risk": 0.15}
        }
    },

    "COPD": {
        "stages": {
            "GOLD_I": {
                "criteria": {"fev1_percent": (80, 100)},
                "monitoring": ["Pulmonary_Function"],
                "interventions": ["bronchodilator"],
                "complications": []
            },
            "GOLD_II": {
                "criteria": {"fev1_percent": (50, 80)},
                "monitoring": ["Pulmonary_Function", "Inflammatory_Markers"],
                "interventions": ["bronchodilator", "inhaled_steroid"],
                "complications": ["Acute_Exacerbation"]
            },
            "GOLD_III": {
                "criteria": {"fev1_percent": (30, 50)},
                "monitoring": ["Pulmonary_Function", "Cardiology_Followup"],
                "interventions": ["combination_inhaler", "oxygen_therapy"],
                "complications": ["Acute_Exacerbation", "Pulmonary_Hypertension"]
            },
            "GOLD_IV": {
                "criteria": {"fev1_percent": (0, 30)},
                "monitoring": ["Pulmonary_Function", "Basic_Metabolic_Panel"],
                "interventions": ["chronic_oxygen", "transplant_evaluation"],
                "complications": ["Respiratory_Failure"]
            }
        },
        "complications": {
            "Acute_Exacerbation": {"icd10": "J44.1", "progression_risk": 0.3},
            "Pulmonary_Hypertension": {"icd10": "I27.2", "progression_risk": 0.15},
            "Respiratory_Failure": {"icd10": "J96.90", "progression_risk": 0.1}
        }
    },

    "Major_Depressive_Disorder": {
        "stages": {
            "Mild": {
                "criteria": {"phq9": (5, 9)},
                "monitoring": ["Behavioral_Health_Assessments"],
                "interventions": ["therapy"],
                "complications": []
            },
            "Moderate": {
                "criteria": {"phq9": (10, 19)},
                "monitoring": ["Behavioral_Health_Assessments"],
                "interventions": ["therapy", "ssri"],
                "complications": ["Anxiety_Disorder"]
            },
            "Severe": {
                "criteria": {"phq9": (20, 27)},
                "monitoring": ["Behavioral_Health_Assessments"],
                "interventions": ["snri", "psych_hospitalization"],
                "complications": ["Suicidality"]
            }
        },
        "complications": {
            "Anxiety_Disorder": {"icd10": "F41.9", "progression_risk": 0.4},
            "Suicidality": {"icd10": "R45.851", "progression_risk": 0.1}
        }
    }
}

# Enhanced procedure-condition relationships with CPT codes
CLINICAL_PROCEDURES = {
    "Cardiovascular": {
        "diagnostic": [
            {"name": "Echocardiogram", "cpt": "93306", "conditions": ["Heart_Disease", "Heart_Failure", "Hypertension"], "complexity": "routine"},
            {"name": "Cardiac_Catheterization", "cpt": "93458", "conditions": ["Coronary_Artery_Disease", "Myocardial_Infarction"], "complexity": "high"},
            {"name": "Stress_Test", "cpt": "93017", "conditions": ["Chest_Pain", "Coronary_Artery_Disease"], "complexity": "routine"},
            {"name": "Holter_Monitor", "cpt": "93224", "conditions": ["Arrhythmia", "Atrial_Fibrillation"], "complexity": "routine"},
            {"name": "CT_Angiography", "cpt": "75571", "conditions": ["Coronary_Artery_Disease", "Peripheral_Artery_Disease"], "complexity": "moderate"}
        ],
        "therapeutic": [
            {"name": "Percutaneous_Coronary_Intervention", "cpt": "92928", "conditions": ["STEMI", "NSTEMI", "Unstable_Angina"], "complexity": "high"},
            {"name": "Coronary_Artery_Bypass", "cpt": "33533", "conditions": ["Multivessel_CAD", "Left_Main_Disease"], "complexity": "very_high"},
            {"name": "Pacemaker_Insertion", "cpt": "33206", "conditions": ["Heart_Block", "Bradycardia"], "complexity": "high"},
            {"name": "ICD_Implantation", "cpt": "33249", "conditions": ["Heart_Failure", "Ventricular_Arrhythmia"], "complexity": "high"}
        ]
    },
    
    "Endocrinology": {
        "diagnostic": [
            {"name": "Glucose_Tolerance_Test", "cpt": "82951", "conditions": ["Prediabetes", "Gestational_Diabetes"], "complexity": "routine"},
            {"name": "Thyroid_Ultrasound", "cpt": "76536", "conditions": ["Thyroid_Nodule", "Hyperthyroidism"], "complexity": "routine"},
            {"name": "Diabetic_Eye_Exam", "cpt": "92012", "conditions": ["Diabetes", "Diabetic_Retinopathy"], "complexity": "routine"}
        ],
        "therapeutic": [
            {"name": "Insulin_Pump_Insertion", "cpt": "95990", "conditions": ["Type_1_Diabetes", "Brittle_Diabetes"], "complexity": "moderate"},
            {"name": "Continuous_Glucose_Monitor", "cpt": "95249", "conditions": ["Diabetes", "Hypoglycemia"], "complexity": "routine"}
        ]
    },
    
    "Oncology": {
        "diagnostic": [
            {"name": "CT_Chest_Abdomen_Pelvis", "cpt": "71250", "conditions": ["Cancer", "Metastatic_Disease"], "complexity": "routine"},
            {"name": "PET_Scan", "cpt": "78815", "conditions": ["Cancer", "Staging"], "complexity": "moderate"},
            {"name": "Bone_Marrow_Biopsy", "cpt": "38221", "conditions": ["Leukemia", "Lymphoma"], "complexity": "moderate"},
            {"name": "Tumor_Biopsy", "cpt": "19083", "conditions": ["Breast_Mass", "Lung_Nodule"], "complexity": "moderate"}
        ],
        "therapeutic": [
            {"name": "Chemotherapy_Administration", "cpt": "96413", "conditions": ["Active_Cancer"], "complexity": "moderate"},
            {"name": "Radiation_Therapy", "cpt": "77301", "conditions": ["Localized_Cancer"], "complexity": "moderate"},
            {"name": "Tumor_Resection", "cpt": "19301", "conditions": ["Breast_Cancer", "Lung_Cancer"], "complexity": "high"}
        ]
    },
    
    "Gastroenterology": {
        "diagnostic": [
            {"name": "Colonoscopy", "cpt": "45378", "conditions": ["Colorectal_Screening", "GI_Bleeding", "IBD"], "complexity": "routine"},
            {"name": "Upper_Endoscopy", "cpt": "43235", "conditions": ["GERD", "Peptic_Ulcer", "GI_Bleeding"], "complexity": "routine"},
            {"name": "ERCP", "cpt": "43260", "conditions": ["Pancreatic_Disease", "Biliary_Obstruction"], "complexity": "high"}
        ],
        "therapeutic": [
            {"name": "Polypectomy", "cpt": "45385", "conditions": ["Colon_Polyps"], "complexity": "routine"},
            {"name": "Variceal_Banding", "cpt": "43244", "conditions": ["Esophageal_Varices", "Cirrhosis"], "complexity": "moderate"}
        ]
    }
}

# Backward compatibility - simplified observation types for legacy functions
OBSERVATION_TYPES = ["Height", "Weight", "Blood Pressure", "Heart Rate", "Temperature", "Hemoglobin A1c", "Cholesterol"]

# PHASE 1: Expanded death causes with ICD-10-CM coding and age stratification
DEATH_CAUSES_BY_AGE = {
    # Neonatal/Infant deaths (0-1 years)
    (0, 1): [
        {"icd10": "P07.30", "description": "Extremely low birth weight newborn, unspecified weight", "weight": 15},
        {"icd10": "Q24.9", "description": "Congenital malformation of heart, unspecified", "weight": 12},
        {"icd10": "P22.0", "description": "Respiratory distress syndrome of newborn", "weight": 10},
        {"icd10": "P36.9", "description": "Bacterial sepsis of newborn, unspecified", "weight": 8},
        {"icd10": "R95", "description": "Sudden infant death syndrome", "weight": 5}
    ],
    
    # Pediatric deaths (1-14 years)  
    (1, 14): [
        {"icd10": "W87.XXXA", "description": "Exposure to unspecified electric current, initial encounter", "weight": 15},
        {"icd10": "V43.52XA", "description": "Car passenger injured in collision with car in traffic accident, initial encounter", "weight": 12},
        {"icd10": "C95.90", "description": "Leukemia, unspecified of unspecified cell type not having achieved remission", "weight": 10},
        {"icd10": "Q90.9", "description": "Down syndrome, unspecified", "weight": 8},
        {"icd10": "W65.XXXA", "description": "Drowning and submersion while in bathtub, initial encounter", "weight": 7},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 5}
    ],
    
    # Young adult deaths (15-34 years)
    (15, 34): [
        {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 20},
        {"icd10": "V43.52XA", "description": "Car passenger injured in collision with car in traffic accident, initial encounter", "weight": 18},
        {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 15},
        {"icd10": "X95.XXXA", "description": "Assault by other and unspecified firearm discharge, initial encounter", "weight": 12},
        {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 8},
        {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 7},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 5}
    ],
    
    # Middle-aged deaths (35-64 years)
    (35, 64): [
        {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 25},
        {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 20},
        {"icd10": "K72.90", "description": "Hepatic failure, unspecified without coma", "weight": 12},
        {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 10},
        {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 8},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 8},
        {"icd10": "E14.9", "description": "Unspecified diabetes mellitus with unspecified complications", "weight": 7},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 5},
        {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 5}
    ],
    
    # Elderly deaths (65+ years)
    (65, 120): [
        {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 30},
        {"icd10": "C78.00", "description": "Secondary malignant neoplasm of unspecified lung", "weight": 25},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 15},
        {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 12},
        {"icd10": "G30.9", "description": "Alzheimer disease, unspecified", "weight": 10},
        {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 8},
        {"icd10": "J18.9", "description": "Pneumonia, unspecified organism", "weight": 8},
        {"icd10": "N18.6", "description": "End stage renal disease", "weight": 7},
        {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 5},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 10}
    ]
}

# Condition-specific death cause mappings with ICD-10-CM codes
CONDITION_MORTALITY_RISK = {
    "Hypertension": {
        "relative_risk": 1.3,
        "likely_deaths": [
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 40},
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 30},
            {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 20},
            {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 10}
        ]
    },
    "Diabetes": {
        "relative_risk": 1.8,
        "likely_deaths": [
            {"icd10": "E14.9", "description": "Unspecified diabetes mellitus with unspecified complications", "weight": 30},
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 25},
            {"icd10": "N18.6", "description": "End stage renal disease", "weight": 20},
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 15},
            {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 10}
        ]
    },
    "Cancer": {
        "relative_risk": 3.5,
        "likely_deaths": [
            {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 40},
            {"icd10": "C78.00", "description": "Secondary malignant neoplasm of unspecified lung", "weight": 30},
            {"icd10": "C25.9", "description": "Malignant neoplasm of pancreas, unspecified", "weight": 15},
            {"icd10": "C50.911", "description": "Malignant neoplasm of unspecified site of right female breast", "weight": 15}
        ]
    },
    "Heart Disease": {
        "relative_risk": 2.2,
        "likely_deaths": [
            {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 35},
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 30},
            {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 25},
            {"icd10": "I46.9", "description": "Cardiac arrest, cause unspecified", "weight": 10}
        ]
    },
    "COPD": {
        "relative_risk": 2.0,
        "likely_deaths": [
            {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 50},
            {"icd10": "J44.1", "description": "Chronic obstructive pulmonary disease with acute exacerbation", "weight": 30},
            {"icd10": "J80", "description": "Acute respiratory distress syndrome", "weight": 20}
        ]
    },
    "Depression": {
        "relative_risk": 1.5,
        "likely_deaths": [
            {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 60},
            {"icd10": "X84.XXXA", "description": "Intentional self-harm by unspecified means, initial encounter", "weight": 30},
            {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 10}
        ]
    },
    "Stroke": {
        "relative_risk": 2.5,
        "likely_deaths": [
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 70},
            {"icd10": "I61.9", "description": "Nontraumatic intracerebral hemorrhage, unspecified", "weight": 20},
            {"icd10": "I63.9", "description": "Cerebral infarction, unspecified", "weight": 10}
        ]
    },
    "Alzheimer's": {
        "relative_risk": 2.8,
        "likely_deaths": [
            {"icd10": "G30.9", "description": "Alzheimer disease, unspecified", "weight": 80},
            {"icd10": "J18.9", "description": "Pneumonia, unspecified organism", "weight": 15},
            {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 5}
        ]
    }
}

FAMILY_RELATIONSHIPS = ["Mother", "Father", "Sibling"]

# Phase 3 constants: clinical comorbidities, genetic risk, precision medicine, and SDOH impacts
COMORBIDITY_RELATIONSHIPS = {
    "Diabetes": {"Hypertension": 0.6, "Heart Disease": 0.35, "Stroke": 0.15},
    "Hypertension": {"Heart Disease": 0.45, "Stroke": 0.2, "Diabetes": 0.25},
    "Obesity": {"Diabetes": 0.5, "Hypertension": 0.4, "Heart Disease": 0.25},
    "COPD": {"Heart Disease": 0.25, "Stroke": 0.1},
    "Depression": {"Anxiety": 0.6},
    "Anxiety": {"Depression": 0.55},
    "Heart Disease": {"Stroke": 0.2}
}

SDOH_CONDITION_MODIFIERS = {
    "Diabetes": {"low_income": 0.05, "housing_instability": 0.04, "limited_education": 0.03},
    "Heart Disease": {"smoker": 0.06, "heavy_alcohol_use": 0.03, "low_income": 0.02},
    "Hypertension": {"low_income": 0.04, "smoker": 0.03, "limited_education": 0.02},
    "Depression": {"housing_instability": 0.06, "unemployed": 0.05},
    "Anxiety": {"housing_instability": 0.05, "unemployed": 0.04},
    "COPD": {"smoker": 0.15},
    "Stroke": {"smoker": 0.04, "low_income": 0.02},
    "Obesity": {"low_income": 0.04, "limited_education": 0.03}
}

SDOH_CONTEXT_MODIFIERS = {
    "cardiometabolic": {
        "deprivation_weight": 0.05,
        "access_weight": -0.03
    },
    "oncology": {
        "deprivation_weight": 0.04,
        "care_gap_penalty": 0.05
    },
    "behavioral": {
        "language_barrier_weight": 0.03,
        "support_weight": -0.04
    }
}

GENETIC_RISK_FACTORS = {
    "BRCA1_BRCA2": {
        "base_prevalence": 0.02,
        "applicable_genders": ["female"],
        "associated_conditions": {"Cancer": 0.18},
        "family_history_conditions": ["Breast Cancer", "Ovarian Cancer"],
        "recommended_screenings": ["Mammography", "Breast_MRI"],
        "risk_score": 1.2
    },
    "Lynch_Syndrome": {
        "base_prevalence": 0.01,
        "associated_conditions": {"Cancer": 0.12},
        "family_history_conditions": ["Colorectal Cancer", "Endometrial Cancer"],
        "recommended_screenings": ["Colonoscopy"],
        "risk_score": 1.0
    },
    "Familial_Hypercholesterolemia": {
        "base_prevalence": 0.03,
        "associated_conditions": {"Heart Disease": 0.2},
        "family_history_conditions": ["Premature Coronary Artery Disease"],
        "recommended_screenings": ["Lipid_Panel"],
        "risk_score": 1.1
    }
}

PRECISION_MEDICINE_MARKERS = {
    "Cancer": [
        {"name": "HER2_Positive", "prevalence": 0.15, "targeted_therapy": "Trastuzumab", "applicable_genders": ["female"]},
        {"name": "EGFR_Mutation", "prevalence": 0.1, "targeted_therapy": "Osimertinib"},
        {"name": "PDL1_High", "prevalence": 0.12, "targeted_therapy": "Pembrolizumab"}
    ],
    "Asthma": [
        {"name": "Eosinophilic_Phenotype", "prevalence": 0.12, "targeted_therapy": "Mepolizumab"}
    ],
    "Diabetes": [
        {"name": "GAD_Antibody_Positive", "prevalence": 0.08, "care_plan": "intensive_monitoring"}
    ]
}

# Phase 4: Care pathway templates for specialty conditions
SPECIALTY_CARE_PATHWAYS = {
    "Heart Disease": {
        "care_team": ["Cardiology", "Primary_Care", "Pharmacy"],
        "pathway": [
            {
                "stage": "Initial_Diagnosis",
                "expected_interval_days": 30,
                "window_days": 45,
                "quality_metric": "beta_blocker_on_discharge",
                "encounter_types": ["Cardiology Clinic", "Primary Care Follow-up"],
                "required_panels": ["Cardiac_Markers", "Lipid_Panel"],
                "required_procedures": ["Echocardiogram"],
                "required_therapeutic_classes": ["beta_blocker", "ace_inhibitor"],
                "care_team": ["Cardiology"],
                "priority": "high",
                "notes": "Confirm ischemic burden, initiate guideline-directed therapy, document beta blocker use."
            },
            {
                "stage": "Cardiac_Rehab",
                "expected_interval_days": 90,
                "window_days": 75,
                "quality_metric": "rehab_completion",
                "encounter_types": ["Rehabilitation Therapy"],
                "required_procedures": ["Stress_Test"],
                "required_observation_panels": ["Pulmonary_Function"],
                "care_team": ["Rehabilitation", "Nursing"],
                "priority": "routine",
                "notes": "Enroll patient in supervised cardiac rehab and track functional progress."
            },
            {
                "stage": "Six_Month_Followup",
                "expected_interval_days": 180,
                "window_days": 90,
                "quality_metric": "ldl_control",
                "encounter_types": ["Cardiology Clinic", "Primary Care Follow-up"],
                "required_panels": ["Lipid_Panel"],
                "required_medications": ["Atorvastatin", "Rosuvastatin"],
                "care_team": ["Primary_Care"],
                "priority": "routine",
                "notes": "Adjust statin or antihypertensive therapy to maintain LDL and blood pressure goals."
            },
        ],
    },
    "Cancer": {
        "care_team": ["Oncology", "Radiology", "Nutrition"],
        "pathway": [
            {
                "stage": "Staging",
                "expected_interval_days": 14,
                "window_days": 21,
                "quality_metric": "stage_documented",
                "encounter_types": ["Oncology Visit"],
                "required_procedures": ["CT_Chest_Abdomen_Pelvis", "Tumor_Biopsy"],
                "care_team": ["Oncology"],
                "priority": "high",
                "notes": "Complete staging studies and document TNM classification."
            },
            {
                "stage": "First_Line_Therapy",
                "expected_interval_days": 45,
                "window_days": 60,
                "quality_metric": "chemo_initiated",
                "encounter_types": ["Oncology Visit"],
                "required_procedures": ["Chemotherapy_Administration"],
                "required_therapeutic_classes": ["chemotherapy"],
                "care_team": ["Oncology", "Pharmacy"],
                "priority": "high",
                "notes": "Start systemic therapy aligned to biomarker profile and document regimen."
            },
            {
                "stage": "Restaging",
                "expected_interval_days": 180,
                "window_days": 90,
                "quality_metric": "tumor_marker_tracked",
                "encounter_types": ["Oncology Visit"],
                "required_panels": ["Oncology_Tumor_Markers"],
                "required_procedures": ["PET_Scan"],
                "care_team": ["Oncology", "Radiology"],
                "priority": "high",
                "notes": "Assess treatment response and modify plan for recurrence or progression."
            },
        ],
    },
    "COPD": {
        "care_team": ["Pulmonology", "Primary_Care", "Respiratory_Therapy"],
        "pathway": [
            {
                "stage": "Pulmonary_Assessment",
                "expected_interval_days": 60,
                "window_days": 45,
                "quality_metric": "spirometry_updated",
                "encounter_types": ["Pulmonology Clinic"],
                "required_observation_panels": ["Pulmonary_Function"],
                "care_team": ["Pulmonology"],
                "priority": "routine",
                "notes": "Update spirometry and review inhaler technique."
            },
            {
                "stage": "Maintenance_Therapy",
                "expected_interval_days": 120,
                "window_days": 60,
                "quality_metric": "inhaler_education",
                "encounter_types": ["Pulmonology Clinic", "Primary Care Follow-up"],
                "required_therapeutic_classes": ["inhaled_steroid", "bronchodilator"],
                "care_team": ["Respiratory_Therapy"],
                "priority": "routine",
                "notes": "Reinforce maintenance regimen and enroll in pulmonary rehab when appropriate."
            },
            {
                "stage": "Exacerbation_Prevention",
                "expected_interval_days": 180,
                "window_days": 90,
                "quality_metric": "vaccinations_up_to_date",
                "encounter_types": ["Primary Care Follow-up", "Telehealth Check-in"],
                "required_immunizations": ["Seasonal Influenza Vaccine", "Pneumococcal Conjugate Vaccine"],
                "care_team": ["Primary_Care"],
                "priority": "routine",
                "notes": "Confirm vaccinations, update action plan, and review rescue medication usage."
            },
        ],
    },
    "Depression": {
        "care_team": ["Behavioral_Health", "Primary_Care", "Social_Work"],
        "pathway": [
            {
                "stage": "Evaluation",
                "expected_interval_days": 30,
                "window_days": 30,
                "quality_metric": "phq9_documented",
                "encounter_types": ["Behavioral Health Session", "Primary Care Follow-up"],
                "required_observation_panels": ["Behavioral_Health_Assessments"],
                "care_team": ["Behavioral_Health"],
                "priority": "routine",
                "notes": "Complete standardized screening and risk assessment."
            },
            {
                "stage": "Therapy_Initiation",
                "expected_interval_days": 60,
                "window_days": 45,
                "quality_metric": "therapy_sessions_started",
                "encounter_types": ["Behavioral Health Session"],
                "required_therapeutic_classes": ["ssri", "snri"],
                "care_team": ["Behavioral_Health", "Pharmacy"],
                "priority": "routine",
                "notes": "Start psychotherapy and/or pharmacotherapy, monitor for adverse effects."
            },
            {
                "stage": "Remission_Assessment",
                "expected_interval_days": 120,
                "window_days": 60,
                "quality_metric": "phq9_improved",
                "encounter_types": ["Behavioral Health Session", "Telehealth Check-in"],
                "required_observation_panels": ["Behavioral_Health_Assessments"],
                "care_team": ["Behavioral_Health", "Primary_Care"],
                "priority": "routine",
                "notes": "Assess symptom improvement and update relapse prevention plan."
            },
        ],
    },
    "Diabetes": {
        "care_team": ["Endocrinology", "Primary_Care", "Nutrition"],
        "pathway": [
            {
                "stage": "Baseline_Assessment",
                "expected_interval_days": 30,
                "window_days": 30,
                "quality_metric": "diabetes_baseline_documented",
                "encounter_types": ["Primary Care Follow-up", "Endocrinology Clinic"],
                "required_panels": ["Diabetes_Monitoring"],
                "required_observation_types": ["Hemoglobin_A1c"],
                "required_procedures": ["Diabetic_Eye_Exam"],
                "required_therapeutic_classes": ["antidiabetic"],
                "care_team": ["Endocrinology"],
                "priority": "high",
                "notes": "Establish glycemic control, initiate therapy, and schedule retinal screening."
            },
            {
                "stage": "Quarterly_A1c",
                "expected_interval_days": 90,
                "window_days": 45,
                "quality_metric": "a1c_control",
                "encounter_types": ["Endocrinology Clinic", "Primary Care Follow-up", "Telehealth Check-in"],
                "required_observation_types": ["Hemoglobin_A1c"],
                "required_panels": ["Diabetes_Monitoring"],
                "required_medications": ["Metformin"],
                "care_team": ["Primary_Care"],
                "priority": "routine",
                "notes": "Review adherence, titrate oral agents or insulin, and capture A1c trend."
            },
            {
                "stage": "Annual_Preventive",
                "expected_interval_days": 365,
                "window_days": 60,
                "quality_metric": "complication_screening",
                "encounter_types": ["Primary Care Follow-up"],
                "required_panels": ["Renal_Function_Panel"],
                "required_observation_types": ["Microalbumin", "Creatinine"],
                "required_procedures": ["Diabetic_Eye_Exam"],
                "required_immunizations": ["Seasonal Influenza Vaccine"],
                "care_team": ["Primary_Care", "Ophthalmology"],
                "priority": "routine",
                "notes": "Assess nephropathy risk, reinforce vaccinations, and repeat retinal exam when due."
            },
        ],
    },
    "Chronic Kidney Disease": {
        "care_team": ["Nephrology", "Primary_Care", "Pharmacy"],
        "pathway": [
            {
                "stage": "Renal_Function_Baseline",
                "expected_interval_days": 30,
                "window_days": 30,
                "quality_metric": "egfr_documented",
                "encounter_types": ["Primary Care Follow-up", "Nephrology Clinic"],
                "required_panels": ["Renal_Function_Panel"],
                "required_observation_types": ["eGFR", "Potassium"],
                "required_therapeutic_classes": ["ace_inhibitor"],
                "care_team": ["Nephrology"],
                "priority": "high",
                "notes": "Document baseline kidney function and optimize ACEi/ARB therapy."
            },
            {
                "stage": "Progression_Mitigation",
                "expected_interval_days": 120,
                "window_days": 60,
                "quality_metric": "renal_risk_reduction",
                "encounter_types": ["Primary Care Follow-up", "Telehealth Check-in"],
                "required_panels": ["Renal_Function_Panel", "Diabetes_Monitoring"],
                "required_observation_types": ["Microalbumin"],
                "required_therapeutic_classes": ["sglt2_inhibitor"],
                "care_team": ["Primary_Care", "Pharmacy"],
                "priority": "routine",
                "notes": "Monitor albuminuria trends and reinforce SGLT2 or ACEi adherence."
            },
            {
                "stage": "Advanced_Care_Planning",
                "expected_interval_days": 240,
                "window_days": 90,
                "quality_metric": "renal_care_plan_documented",
                "encounter_types": ["Nephrology Clinic"],
                "required_panels": ["Renal_Function_Panel"],
                "required_immunizations": ["COVID-19 mRNA Vaccine", "Seasonal Influenza Vaccine"],
                "care_team": ["Nephrology", "Primary_Care"],
                "priority": "routine",
                "notes": "Discuss modality planning, update vaccinations, and coordinate multidisciplinary support."
            },
        ],
    },
    "Asthma": {
        "care_team": ["Pulmonology", "Primary_Care", "Respiratory_Therapy"],
        "pathway": [
            {
                "stage": "Asthma_Control_Assessment",
                "expected_interval_days": 60,
                "window_days": 45,
                "quality_metric": "asthma_control_test",
                "encounter_types": ["Pulmonology Clinic", "Primary Care Follow-up"],
                "required_observation_panels": ["Pulmonary_Function"],
                "required_observation_types": ["FEV1"],
                "required_therapeutic_classes": ["inhaled_steroid"],
                "care_team": ["Pulmonology"],
                "priority": "routine",
                "notes": "Review symptom control, update inhaled corticosteroid therapy, and document spirometry."
            },
            {
                "stage": "Maintenance_Titration",
                "expected_interval_days": 120,
                "window_days": 60,
                "quality_metric": "controller_adherence",
                "encounter_types": ["Pulmonology Clinic", "Telehealth Check-in"],
                "required_therapeutic_classes": ["bronchodilator", "inhaled_combo"],
                "required_panels": ["Pulmonary_Function"],
                "care_team": ["Respiratory_Therapy", "Primary_Care"],
                "priority": "routine",
                "notes": "Ensure dual-controller therapy adherence and reinforce inhaler technique."
            },
            {
                "stage": "Exacerbation_Prevention",
                "expected_interval_days": 365,
                "window_days": 90,
                "quality_metric": "preventive_care_completed",
                "encounter_types": ["Primary Care Follow-up"],
                "required_immunizations": ["Seasonal Influenza Vaccine", "COVID-19 mRNA Vaccine"],
                "required_panels": ["Pulmonary_Function"],
                "care_team": ["Primary_Care", "Respiratory_Therapy"],
                "priority": "routine",
                "notes": "Deliver annual vaccinations, refresh action plan, and consider pulmonary rehab referral."
            },
        ],
    },
}

SPECIALTY_CARE_PATHWAY_SYNONYMS = {
    _normalize_condition_display(name): name for name in SPECIALTY_CARE_PATHWAYS
}
SPECIALTY_CARE_PATHWAY_SYNONYMS.update(
    {
        _normalize_condition_display("Type 2 Diabetes Mellitus"): "Diabetes",
        _normalize_condition_display("Type II Diabetes Mellitus"): "Diabetes",
        _normalize_condition_display("Type 1 Diabetes Mellitus"): "Diabetes",
        _normalize_condition_display("Chronic Kidney Disease"): "Chronic Kidney Disease",
        _normalize_condition_display("Chronic kidney disease"): "Chronic Kidney Disease",
        _normalize_condition_display("Chronic kidney disease stage 3"): "Chronic Kidney Disease",
        _normalize_condition_display("Chronic kidney disease stage 4"): "Chronic Kidney Disease",
        _normalize_condition_display("Asthma"): "Asthma",
        _normalize_condition_display("Severe persistent asthma"): "Asthma",
        _normalize_condition_display("Moderate persistent asthma"): "Asthma",
    }
)


RELATION_ROLE_CODES = {
    "Mother": "MTH",
    "Father": "FTH",
    "Brother": "BRO",
    "Sister": "SIS",
    "Sibling": "NSIB",
    "Grandmother": "GRNDM",
    "Grandfather": "GRNDF",
    "Grandparent": "GRPRN",
}

FAMILY_RELATIONSHIP_FACTORS = {
    "Mother": 1.0,
    "Father": 1.0,
    "Brother": 0.85,
    "Sister": 0.85,
    "Sibling": 0.85,
    "Grandmother": 0.45,
    "Grandfather": 0.45,
    "Grandparent": 0.45,
}

FAMILY_HISTORY_PROFILES = [
    {
        "condition": "Heart Disease",
        "category": "cardiometabolic",
        "base_rate": 0.22,
        "risk_boost": 0.08,
        "onset_mean": 55,
        "onset_sd": 8,
        "relations": {"Father": 0.35, "Mother": 0.3, "Brother": 0.2, "Sister": 0.1, "Grandparent": 0.05},
        "sex_bias": None,
        "notes": "Early coronary artery disease in first-degree relative."
    },
    {
        "condition": "Hypertension",
        "category": "cardiometabolic",
        "base_rate": 0.28,
        "risk_boost": 0.05,
        "onset_mean": 48,
        "onset_sd": 6,
        "relations": {"Mother": 0.3, "Father": 0.3, "Brother": 0.2, "Sister": 0.2},
        "sex_bias": None,
        "notes": "Parental hypertension increases lifetime risk."
    },
    {
        "condition": "Diabetes",
        "category": "cardiometabolic",
        "base_rate": 0.18,
        "risk_boost": 0.07,
        "onset_mean": 50,
        "onset_sd": 7,
        "relations": {"Mother": 0.35, "Father": 0.3, "Sibling": 0.2, "Grandparent": 0.15},
        "sex_bias": None,
        "notes": "Family history of type 2 diabetes."
    },
    {
        "condition": "Cancer",
        "category": "oncology",
        "base_rate": 0.16,
        "risk_boost": 0.06,
        "onset_mean": 52,
        "onset_sd": 10,
        "relations": {"Mother": 0.25, "Father": 0.2, "Sister": 0.2, "Brother": 0.15, "Grandparent": 0.2},
        "sex_bias": None,
        "notes": "General solid tumor history; refine with genetic markers when available."
    },
    {
        "condition": "Stroke",
        "category": "cardiovascular",
        "base_rate": 0.12,
        "risk_boost": 0.06,
        "onset_mean": 60,
        "onset_sd": 9,
        "relations": {"Father": 0.3, "Mother": 0.3, "Brother": 0.2, "Sister": 0.2},
        "sex_bias": None,
        "notes": "Ischemic stroke or TIA in a parent or sibling."
    },
    {
        "condition": "COPD",
        "category": "respiratory",
        "base_rate": 0.08,
        "risk_boost": 0.04,
        "onset_mean": 58,
        "onset_sd": 7,
        "relations": {"Father": 0.35, "Mother": 0.25, "Sibling": 0.3, "Grandparent": 0.1},
        "sex_bias": None,
        "notes": "Smoking-related obstructive disease in first-degree relative."
    },
    {
        "condition": "Depression",
        "category": "mental_health",
        "base_rate": 0.20,
        "risk_boost": 0.05,
        "onset_mean": 32,
        "onset_sd": 6,
        "relations": {"Mother": 0.35, "Father": 0.25, "Sister": 0.2, "Brother": 0.2},
        "sex_bias": None,
        "notes": "Mood disorder diagnosed in first-degree relative."
    },
    {
        "condition": "Anxiety",
        "category": "mental_health",
        "base_rate": 0.18,
        "risk_boost": 0.04,
        "onset_mean": 25,
        "onset_sd": 5,
        "relations": {"Mother": 0.4, "Father": 0.2, "Sister": 0.2, "Brother": 0.2},
        "sex_bias": "female",
        "notes": "Generalized anxiety disorder in close relative."
    },
    {
        "condition": "Alzheimer's",
        "category": "neurology",
        "base_rate": 0.10,
        "risk_boost": 0.07,
        "onset_mean": 72,
        "onset_sd": 6,
        "relations": {"Mother": 0.3, "Father": 0.3, "Sibling": 0.2, "Grandparent": 0.2},
        "sex_bias": None,
        "notes": "Late-onset dementia in immediate family."
    },
    {
        "condition": "Osteoporosis",
        "category": "musculoskeletal",
        "base_rate": 0.08,
        "risk_boost": 0.03,
        "onset_mean": 62,
        "onset_sd": 5,
        "relations": {"Mother": 0.5, "Grandmother": 0.5},
        "sex_bias": "female",
        "notes": "Maternal history of fragility fractures."
    },
]


def _family_history_probability(profile: Dict[str, Any], patient: Dict[str, Any]) -> float:
    """Estimate likelihood of a documented family history entry for this profile."""

    probability = float(profile.get("base_rate", 0.1) or 0.1)
    age = int(patient.get("age", 0) or 0)
    onset_mean = profile.get("onset_mean", 50) or 50
    onset_sd = profile.get("onset_sd", 10) or 10

    if age >= onset_mean:
        probability *= 1.2
    elif age <= max(0, onset_mean - max(15, onset_sd * 2)):
        probability *= 0.75

    gender = (patient.get("gender") or "").lower()
    sex_bias = profile.get("sex_bias")
    if sex_bias == "female":
        probability *= 1.25 if gender.startswith("f") else 0.7
    elif sex_bias == "male":
        probability *= 1.25 if gender.startswith("m") else 0.7

    smoking = patient.get("smoking_status")
    alcohol = patient.get("alcohol_use")
    category = profile.get("category", "")
    if smoking == "Current" and category in {"cardiometabolic", "cardiovascular", "respiratory"}:
        probability *= 1.1
    if alcohol == "Heavy" and category in {"cardiometabolic", "cardiovascular"}:
        probability *= 1.05

    deprivation_index = patient.get("community_deprivation_index")
    if deprivation_index is not None:
        probability *= 1 + min(max(float(deprivation_index), 0.0), 1.0) * 0.05

    return max(0.01, min(probability, 0.9))


def _choose_family_relation(relations: Dict[str, float]) -> Optional[str]:
    if not relations:
        return None
    total = sum(relations.values())
    if total <= 0:
        return random.choice(list(relations.keys()))
    threshold = random.uniform(0, total)
    cumulative = 0.0
    for relation, weight in relations.items():
        cumulative += weight
        if cumulative >= threshold:
            return relation
    return next(iter(relations))


def _sample_family_history_onset(profile: Dict[str, Any]) -> Optional[int]:
    mean = profile.get("onset_mean")
    sd = profile.get("onset_sd") or 6
    if mean is None:
        return None
    sampled = max(0.0, random.gauss(float(mean), float(sd)))
    return int(round(sampled))


def _resolve_condition_catalog_entry(condition_name: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    normalized = _normalize_condition_display(condition_name)
    entry = CONDITION_CATALOG.get(normalized)
    if entry is None:
        entry = CONDITION_CATALOG.get(condition_name)
    return normalized, entry


def _build_family_history_entry(
    patient: Dict[str, Any],
    profile: Dict[str, Any],
    relation: str,
    relation_code: Optional[str],
    onset_age: Optional[int],
    risk_modifier: float,
    normalized_condition: str,
    catalog_entry: Optional[Dict[str, Any]],
    source: str = "profile",
) -> Dict[str, Any]:
    patient_id = patient.get("patient_id", "")
    recorded_date = datetime.now().date().isoformat()
    snomed = catalog_entry.get("snomed") if catalog_entry else ""
    icd10 = catalog_entry.get("icd10") if catalog_entry else ""
    if not snomed and catalog_entry:
        snomed = catalog_entry.get("snomed_code") or ""
    if not icd10 and catalog_entry:
        icd10 = catalog_entry.get("icd10_code") or ""

    entry: Dict[str, Any] = {
        "family_history_id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "relation": relation,
        "relation_code": relation_code or "",
        "condition": profile.get("condition", normalized_condition),
        "condition_system": "http://snomed.info/sct" if snomed else "http://hl7.org/fhir/sid/icd-10-cm",
        "condition_code": snomed or icd10,
        "icd10_code": icd10,
        "category": profile.get("category"),
        "onset_age": onset_age,
        "risk_modifier": round(risk_modifier, 4),
        "notes": profile.get("notes", ""),
        "recorded_date": recorded_date,
        "source": source,
    }
    if catalog_entry:
        entry["condition_display"] = catalog_entry.get("display", normalized_condition)
    else:
        entry["condition_display"] = profile.get("condition", normalized_condition)
    return entry


fake = Faker()


def _safe_parse_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _patient_age_context(patient: Dict[str, Any]) -> Tuple[int, Optional[date], date]:
    today = datetime.now().date()
    birthdate = _safe_parse_date(patient.get("birthdate"))
    if birthdate:
        age_days = max((today - birthdate).days, 0)
        age_months = age_days // 30
    else:
        age_years = int(patient.get("age", 0) or 0)
        age_months = max(age_years * 12, 0)
    return age_months, birthdate, today


def _collect_allergy_terms(allergies: Optional[List[Dict[str, Any]]]) -> Set[str]:
    if not allergies:
        return set()
    terms: Set[str] = set()
    for allergy in allergies:
        substance = (allergy.get("substance") or "").lower()
        if substance:
            terms.add(substance)
        category = (allergy.get("category") or "").lower()
        if category:
            terms.add(category)
    return terms


def _series_applicable(
    series: Dict[str, Any],
    age_months: int,
    condition_categories: Set[str],
    condition_names: Set[str],
) -> bool:
    if age_months < series.get("min_age_months", 0):
        return False
    max_age = series.get("max_age_months")
    if max_age is not None and age_months > max_age and series.get("series_type") != "adult":
        return False
    catch_up_end = series.get("catch_up_end_months")
    if (
        catch_up_end is not None
        and series.get("series_type") == "childhood"
        and age_months > catch_up_end
    ):
        return False
    required_conditions = series.get("required_conditions")
    if required_conditions and not set(required_conditions).intersection(condition_names):
        return False
    target_categories = series.get("target_categories")
    if target_categories and not target_categories.intersection(condition_categories):
        return False
    return True


def _has_contraindication(entry: Dict[str, Any], allergy_terms: Set[str]) -> bool:
    contraindications = entry.get("contraindications") or []
    if not contraindications or not allergy_terms:
        return False
    for item in contraindications:
        token = item.lower()
        if any(token in term for term in allergy_terms):
            return True
    return False


def _add_months(base_date: date, months: int) -> date:
    year = base_date.year + months // 12
    month = base_date.month + months % 12
    if month > 12:
        year += 1
        month -= 12
    day = min(base_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _select_encounter_for_date(
    encounters: List[Dict[str, Any]], target_date: Optional[date]
) -> Optional[Dict[str, Any]]:
    if not encounters or target_date is None:
        return None
    best_match: Optional[Dict[str, Any]] = None
    smallest_delta: Optional[int] = None
    for encounter in encounters:
        encounter_date = _safe_parse_date(encounter.get("date"))
        if not encounter_date:
            continue
        delta = abs((encounter_date - target_date).days)
        if smallest_delta is None or delta < smallest_delta:
            best_match = encounter
            smallest_delta = delta
    return best_match


def _random_lot_number() -> str:
    return f"{random.choice(string.ascii_uppercase)}{random.randint(100000, 999999)}"


def _prepare_series_doses(series: Dict[str, Any], age_months: int) -> Tuple[List[Dict[str, Any]], int]:
    planned = series.get("doses", [])
    if not planned:
        return [], 0
    max_doses = len(planned)
    cutoff = series.get("two_dose_cutoff_months")
    if cutoff is not None and age_months < cutoff:
        max_doses = min(2, max_doses)

    prepared: List[Dict[str, Any]] = []
    for idx, config in enumerate(planned, start=1):
        if idx > max_doses:
            break
        target_age = config.get("age_months", series.get("min_age_months", 0))
        grace_months = config.get("grace_months", 1)
        if age_months + grace_months < target_age:
            continue
        prepared.append(
            {
                "dose_number": idx,
                "target_age_months": target_age,
                "coverage": config.get("coverage", series.get("coverage", 0.9)),
                "offset_days": config.get("offset_days"),
                "route": config.get("route"),
                "is_catch_up": age_months > target_age + 12,
            }
        )
    return prepared, max_doses


def _resolve_target_date(
    series: Dict[str, Any],
    dose: Dict[str, Any],
    birthdate: Optional[date],
    today: date,
    prior_doses: List[Dict[str, Any]],
    age_months: int,
) -> date:
    offset_days = dose.get("offset_days")
    if offset_days and prior_doses:
        previous_date = _safe_parse_date(prior_doses[-1].get("date")) or today
        candidate = previous_date + timedelta(days=offset_days)
    elif birthdate and dose.get("target_age_months") is not None:
        candidate = _add_months(birthdate, int(dose["target_age_months"]))
    elif birthdate:
        candidate = birthdate + timedelta(days=age_months * 30)
    else:
        candidate = today - timedelta(days=max(0, series.get("min_age_months", 0)) * 30)

    if candidate > today:
        candidate = today - timedelta(days=random.randint(7, 90))
    if birthdate and candidate < birthdate:
        candidate = birthdate + timedelta(days=14)
    return candidate


def _build_immunization_record(
    patient: Dict[str, Any],
    encounter: Optional[Dict[str, Any]],
    series: Dict[str, Any],
    dose: Dict[str, Any],
    administration_date: date,
    series_total: int,
    series_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    catalog_entry = IMMUNIZATION_CATALOG.get(series["name"], {})
    fallback_by_cvx = IMMUNIZATION_BY_CVX.get(series.get("cvx")) or {}
    cvx_code = series.get("cvx") or catalog_entry.get("cvx") or fallback_by_cvx.get("cvx")
    snomed_code = catalog_entry.get("snomed") or fallback_by_cvx.get("snomed")
    rxnorm_code = (
        series.get("rxnorm")
        or series.get("rxnorm_code")
        or catalog_entry.get("rxnorm")
        or fallback_by_cvx.get("rxnorm")
    )
    route = dose.get("route") or series.get("route") or "intramuscular"
    encounter_id = encounter.get("encounter_id") if encounter else None
    location = encounter.get("location") if encounter else None
    provider = encounter.get("provider") if encounter else f"Nurse {fake.last_name()}"
    status_reason = "catch-up" if dose.get("is_catch_up") else "routine"

    record = {
        "immunization_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": encounter_id,
        "vaccine": series["name"],
        "name": series["name"],
        "cvx_code": cvx_code,
        "snomed_code": snomed_code,
        "rxnorm_code": rxnorm_code,
        "date": administration_date.isoformat(),
        "dose_number": dose.get("dose_number", 1),
        "series_total": series_total or dose.get("dose_number", 1),
        "series_id": series.get("series_id"),
        "series_type": series.get("series_type", "unspecified"),
        "series_description": f"Dose {dose.get('dose_number', 1)} of {series_total or dose.get('dose_number', 1)}",
        "status": "completed",
        "status_reason": status_reason,
        "route": route,
        "site": random.choice(IMMUNIZATION_ADMIN_SITES),
        "provider": provider,
        "performer": provider,
        "location": location,
        "lot_number": _random_lot_number(),
        "manufacturer": random.choice(["Pfizer", "Moderna", "Merck", "Sanofi", "GSK"]),
        "expiration_date": (administration_date + timedelta(days=365)).isoformat(),
        "recorded_date": administration_date.isoformat(),
        "was_booster": series.get("series_type") in {"booster", "seasonal"},
    }

    return record


def _build_titer_observation(
    patient: Dict[str, Any],
    encounter: Optional[Dict[str, Any]],
    immunization_record: Dict[str, Any],
    titer_config: Dict[str, Any],
    observation_date: date,
) -> Dict[str, Any]:
    protective_threshold = titer_config.get("protective_threshold", 10.0)
    value = round(random.uniform(protective_threshold * 4, protective_threshold * 10), 1)
    status = "normal" if value >= protective_threshold else "abnormal"
    interpretation = "N" if status == "normal" else "A"

    return {
        "observation_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": encounter.get("encounter_id") if encounter else None,
        "type": titer_config.get("display", "Post-vaccine Antibody Titer"),
        "loinc_code": titer_config.get("loinc", ""),
        "value": str(value),
        "value_numeric": value,
        "units": titer_config.get("units", "mIU/mL"),
        "reference_range": titer_config.get("reference_range", ">= 10 mIU/mL"),
        "status": status,
        "interpretation": interpretation,
        "date": observation_date.isoformat(),
        "panel": "Immunization_Titers",
    }


def _determine_recurrent_date(
    definition: Dict[str, Any], birthdate: Optional[date], today: date
) -> date:
    season_month = definition.get("season_month")
    if season_month:
        year = today.year if today.month >= season_month else today.year - 1
        day = min(15, calendar.monthrange(year, season_month)[1])
        candidate = date(year, season_month, day)
    else:
        candidate = today - timedelta(days=random.randint(60, 365))

    if birthdate and candidate < birthdate:
        candidate = birthdate + timedelta(days=definition.get("min_age_months", 0) * 30)
    if candidate > today:
        candidate = today - timedelta(days=30)
    return candidate


def _generate_series_immunizations(
    patient: Dict[str, Any],
    encounters: List[Dict[str, Any]],
    allergies: Optional[List[Dict[str, Any]]],
    conditions: Optional[List[Dict[str, Any]]],
    age_months: int,
    birthdate: Optional[date],
    today: date,
    series_history: Dict[str, List[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    immunizations: List[Dict[str, Any]] = []
    followup_observations: List[Dict[str, Any]] = []
    allergy_terms = _collect_allergy_terms(allergies)
    condition_names = {cond["name"] for cond in conditions or []}
    condition_categories = {
        cond.get("condition_category")
        for cond in conditions or []
        if cond.get("condition_category")
    }

    for series in IMMUNIZATION_SERIES_DEFINITIONS:
        if not _series_applicable(series, age_months, condition_categories, condition_names):
            continue
        if _has_contraindication(series, allergy_terms):
            continue

        doses, series_total = _prepare_series_doses(series, age_months)
        if not doses:
            continue

        history = series_history.setdefault(series["series_id"], [])
        for dose in doses:
            if any(record["dose_number"] == dose["dose_number"] for record in history):
                continue
            if random.random() > dose.get("coverage", 0.9):
                continue

            administration_date = _resolve_target_date(series, dose, birthdate, today, history, age_months)
            encounter = _select_encounter_for_date(encounters, administration_date)
            record = _build_immunization_record(
                patient,
                encounter,
                series,
                dose,
                administration_date,
                series_total,
                history,
            )
            history.append(record)
            immunizations.append(record)

            titer_config = series.get("titer")
            if titer_config and random.random() < titer_config.get("probability", 0.0):
                observation_date = min(administration_date + timedelta(days=60), today)
                followup_observations.append(
                    _build_titer_observation(patient, encounter, record, titer_config, observation_date)
                )

    return immunizations, followup_observations


def _generate_recurrent_immunizations(
    patient: Dict[str, Any],
    encounters: List[Dict[str, Any]],
    allergies: Optional[List[Dict[str, Any]]],
    conditions: Optional[List[Dict[str, Any]]],
    age_months: int,
    birthdate: Optional[date],
    today: date,
    series_history: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    immunizations: List[Dict[str, Any]] = []
    allergy_terms = _collect_allergy_terms(allergies)
    condition_categories = {
        cond.get("condition_category")
        for cond in conditions or []
        if cond.get("condition_category")
    }

    for definition in IMMUNIZATION_RECURRENT_DEFINITIONS:
        if age_months < definition.get("min_age_months", 0):
            continue
        if definition.get("target_categories") and not definition["target_categories"].intersection(condition_categories):
            continue
        if _has_contraindication(definition, allergy_terms):
            continue

        history = series_history.setdefault(definition["series_id"], [])
        if history and definition.get("interval_years"):
            last_date = _safe_parse_date(history[-1].get("date"))
            if last_date and (today - last_date).days < definition["interval_years"] * 365:
                continue

        coverage = definition.get("coverage", 0.7)
        if random.random() > coverage:
            continue

        administration_date = _determine_recurrent_date(definition, birthdate, today)
        encounter = _select_encounter_for_date(encounters, administration_date)
        dose = {
            "dose_number": len(history) + 1,
            "coverage": coverage,
            "route": definition.get("route"),
            "is_catch_up": False,
        }
        record = _build_immunization_record(
            patient,
            encounter,
            definition,
            dose,
            administration_date,
            1,
            history,
        )
        history.append(record)
        immunizations.append(record)

    return immunizations
def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    return choices[-1][0]

# Condition prevalence by age, gender, race, SDOH
CONDITION_PREVALENCE = {
    # name: (age_min, age_max, gender, race, smoking, alcohol, weight)
    "Asthma": [(0, 18, None, None, None, None, 0.12), (19, 65, None, None, None, None, 0.06)],
    "COPD": [(40, 120, None, None, "Current", None, 0.15)],
    "Hypertension": [(30, 120, None, None, None, None, 0.25)],
    "Diabetes": [(40, 120, None, None, None, None, 0.12)],
    "Heart Disease": [(50, 120, "male", None, None, None, 0.18), (50, 120, "female", None, None, None, 0.10)],
    "Cancer": [(50, 120, None, None, None, None, 0.10)],
    "Depression": [(12, 120, None, None, None, None, 0.15)],
    "Anxiety": [(12, 120, None, None, None, None, 0.18)],
    "Obesity": [(10, 120, None, None, None, None, 0.20)],
    "Arthritis": [(40, 120, None, None, None, None, 0.15)],
    "Flu": [(0, 120, None, None, None, None, 0.08)],
    "COVID-19": [(0, 120, None, None, None, None, 0.05)],
    "Migraine": [(10, 60, "female", None, None, None, 0.12), (10, 60, "male", None, None, None, 0.06)],
    "Allergy": [(0, 30, None, None, None, None, 0.15)],
    "Stroke": [(60, 120, None, None, None, None, 0.07)],
    "Alzheimer's": [(70, 120, None, None, None, None, 0.10)],
}

def calculate_sdoh_risk(patient: Dict[str, Any]) -> List[str]:
    """Calculate SDOH risk profile for a patient and persist to the record."""
    risk_score = 0.0
    factors = []

    income = patient.get("income", 0)
    if income and income < 30000:
        risk_score += 0.2
        factors.append("low_income")

    housing = patient.get("housing_status", "")
    if housing in {"Homeless", "Temporary"}:
        risk_score += 0.25
        factors.append("housing_instability")

    education = patient.get("education", "")
    if education in {"None", "Primary", "Secondary"}:
        risk_score += 0.1
        factors.append("limited_education")

    employment = patient.get("employment_status", "")
    if employment == "Unemployed":
        risk_score += 0.15
        factors.append("unemployed")

    smoking = patient.get("smoking_status", "")
    if smoking == "Current":
        risk_score += 0.2
        factors.append("smoker")

    alcohol = patient.get("alcohol_use", "")
    if alcohol == "Heavy":
        risk_score += 0.1
        factors.append("heavy_alcohol_use")

    context = generate_sdoh_context(patient)
    patient["community_deprivation_index"] = context["deprivation_index"]
    patient["access_to_care_score"] = context["access_score"]
    patient["transportation_access"] = context["transportation"]
    patient["language_access_barrier"] = context["language_barrier"]
    patient["social_support_score"] = context["social_support"]
    patient["sdoh_care_gaps"] = context["care_gaps"]

    patient["sdoh_risk_score"] = round(min(risk_score + context["deprivation_index"] * 0.2, 1.0), 2)
    patient["sdoh_risk_factors"] = factors
    return factors

def generate_sdoh_context(patient: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate geographic and social determinants context for Phase 4."""
    deprivation_index = round(random.uniform(0.0, 1.0), 2)
    access_score = round(random.uniform(-0.3, 0.3), 2)  # positive means better access
    transportation = random.choice(["public_transit", "personal_vehicle", "limited"])
    language_barrier = random.random() < 0.1 if patient.get("language") not in ["English"] else False
    social_support = round(random.uniform(-0.2, 0.2), 2)

    care_gaps = []
    age = patient.get("age", 0)
    if deprivation_index > 0.7 and age >= 50:
        care_gaps.append("missed_colonoscopy")
    if transportation == "limited" and age >= 40:
        care_gaps.append("missed_cardiology_followup")
    if language_barrier:
        care_gaps.append("behavioral_health_followup")

    return {
        "deprivation_index": deprivation_index,
        "access_score": access_score,
        "transportation": transportation,
        "language_barrier": language_barrier,
        "social_support": social_support,
        "care_gaps": care_gaps
    }

def apply_sdoh_adjustments(condition: str, base_probability: float, patient: Dict[str, Any]) -> float:
    """Adjust condition probability based on social determinants of health."""
    modifiers = SDOH_CONDITION_MODIFIERS.get(condition, {})
    normalized = condition.lower()
    if not modifiers:
        for key, value in SDOH_CONDITION_MODIFIERS.items():
            if key.lower() in normalized:
                modifiers = value
                break
    if not modifiers:
        return base_probability

    adjusted = base_probability
    sdoh_factors = patient.get("sdoh_risk_factors", [])
    for factor, boost in modifiers.items():
        if factor in sdoh_factors:
            adjusted += boost

    deprivation_index = patient.get("community_deprivation_index", 0.0)
    access_score = patient.get("access_to_care_score", 0.0)
    language_barrier = patient.get("language_access_barrier", False)
    support_score = patient.get("social_support_score", 0.0)

    if any(keyword in normalized for keyword in {"heart", "hypertens", "diabetes"}):
        weights = SDOH_CONTEXT_MODIFIERS["cardiometabolic"]
        adjusted += deprivation_index * weights["deprivation_weight"]
        adjusted += access_score * weights["access_weight"]
    if "cancer" in normalized or "neoplasm" in normalized:
        weights = SDOH_CONTEXT_MODIFIERS["oncology"]
        if patient.get("sdoh_care_gaps"):
            adjusted += len(patient["sdoh_care_gaps"]) * weights["care_gap_penalty"] / 3
        adjusted += deprivation_index * weights["deprivation_weight"]
    if any(keyword in normalized for keyword in {"depress", "anxiety", "mental"}):
        weights = SDOH_CONTEXT_MODIFIERS["behavioral"]
        if language_barrier:
            adjusted += weights["language_barrier_weight"]
        adjusted += support_score * weights["support_weight"]

    return min(adjusted, 0.95)

def determine_genetic_risk(patient: Dict[str, Any]) -> Dict[str, float]:
    """Assign genetic risk markers and probability adjustments."""
    adjustments = defaultdict(float)
    markers = []
    risk_score = 0.0

    gender = patient.get("gender")

    for marker_name, config in GENETIC_RISK_FACTORS.items():
        allowed_genders = config.get("applicable_genders")
        if allowed_genders and gender not in allowed_genders:
            continue

        base_prevalence = config.get("base_prevalence", 0.01)
        if random.random() < base_prevalence:
            marker_entry = {
                "name": marker_name,
                "conditions": list(config.get("associated_conditions", {}).keys()),
                "screenings": config.get("recommended_screenings", [])
            }
            markers.append(marker_entry)
            risk_score += config.get("risk_score", 1.0)

            for condition, boost in config.get("associated_conditions", {}).items():
                adjustments[condition] += boost

    patient["genetic_markers"] = markers
    patient["genetic_risk_score"] = round(risk_score, 2)
    patient["genetic_risk_adjustments"] = dict(adjustments)
    return patient["genetic_risk_adjustments"]

def apply_comorbidity_relationships(conditions: List[str], patient: Dict[str, Any]) -> List[str]:
    """Inject clinically realistic comorbid conditions."""
    added_relationships = []
    assigned = list(conditions)
    assigned_set = set(assigned)

    for primary in list(assigned):
        relationships = COMORBIDITY_RELATIONSHIPS.get(primary, {})
        for secondary, probability in relationships.items():
            if secondary in assigned_set:
                continue
            if random.random() < probability:
                assigned.append(secondary)
                assigned_set.add(secondary)
                added_relationships.append({
                    "primary": primary,
                    "associated": secondary,
                    "probability": probability
                })

    patient["comorbidity_profile"] = added_relationships
    return assigned

def assign_precision_markers(patient: Dict[str, Any], conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign precision medicine markers and targeted therapy options."""
    markers = []
    existing = set()
    gender = patient.get("gender")

    for condition in conditions:
        condition_name = condition.get("name")
        marker_configs = PRECISION_MEDICINE_MARKERS.get(condition_name, [])
        condition_markers = []

        for marker_config in marker_configs:
            allowed = marker_config.get("applicable_genders")
            if allowed and gender not in allowed:
                continue

            prevalence = marker_config.get("prevalence", 0.1)
            if random.random() < prevalence:
                marker_name = marker_config["name"]
                if marker_name in existing:
                    continue

                marker_entry = {
                    "condition": condition_name,
                    "marker": marker_name,
                    "targeted_therapy": marker_config.get("targeted_therapy"),
                    "care_plan": marker_config.get("care_plan")
                }
                markers.append(marker_entry)
                existing.add(marker_name)
                condition_markers.append(marker_name)

        if condition_markers:
            condition["precision_markers"] = condition_markers

    patient["precision_markers"] = markers
    return markers

def generate_care_plans(
    patient: Dict[str, Any],
    conditions: List[Dict[str, Any]],
    encounters: List[Dict[str, Any]],
    medications: Optional[List[Dict[str, Any]]] = None,
    procedures: Optional[List[Dict[str, Any]]] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
    immunizations: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Create specialty care pathway milestones with status tracking and activities."""

    meds = list(medications) if medications is not None else list(patient.get("medications", []))
    procs = list(procedures) if procedures is not None else list(patient.get("procedures", []))
    obs = list(observations) if observations is not None else list(patient.get("observations", []))
    imm = list(immunizations) if immunizations is not None else list(patient.get("immunizations", []))

    today = datetime.now().date()
    care_plans: List[Dict[str, Any]] = []
    status_counter: Counter[str] = Counter()

    def _parse_related_conditions(value: Any) -> Set[str]:
        if not value:
            return set()
        if isinstance(value, str):
            tokens = [token.strip().strip('"').lower() for token in value.split(',') if token.strip()]
            return set(tokens)
        if isinstance(value, list):
            return {str(token).strip().lower() for token in value if token}
        return set()

    def _collect_by_key(records: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
        lookup: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for record in records:
            value = record.get(key)
            if value:
                lookup[str(value).lower()].append(record)
        return lookup

    def _collect_encounters_for_condition(condition_name: str) -> List[Dict[str, Any]]:
        name_lower = condition_name.lower()
        matches = []
        for encounter in encounters:
            related = _parse_related_conditions(encounter.get("related_conditions"))
            if not related and condition_name:
                continue
            if not related or name_lower in related:
                matches.append(encounter)
        return matches

    observations_by_panel = defaultdict(list)
    observations_by_type = defaultdict(list)
    for ob in obs:
        panel = ob.get("panel")
        if panel:
            observations_by_panel[panel].append(ob)
        ob_type = ob.get("type") or ob.get("name")
        if ob_type:
            observations_by_type[ob_type].append(ob)

    procedures_by_name = defaultdict(list)
    for proc in procs:
        name = proc.get("name")
        if name:
            procedures_by_name[name].append(proc)

    medications_by_name = defaultdict(list)
    medications_by_class = defaultdict(list)
    for med in meds:
        name = med.get("name") or med.get("medication")
        if name:
            medications_by_name[name.lower()].append(med)
        therapeutic_class = (med.get("therapeutic_class") or "").lower()
        if therapeutic_class:
            medications_by_class[therapeutic_class].append(med)

    immunizations_by_name = defaultdict(list)
    for record in imm:
        vaccine = record.get("vaccine") or record.get("name")
        if vaccine:
            immunizations_by_name[vaccine.lower()].append(record)

    condition_names = {c.get("name") for c in conditions if c.get("name")}

    for condition_name in sorted(condition_names):
        normalized_condition_name = _normalize_condition_display(condition_name)
        canonical_name = SPECIALTY_CARE_PATHWAY_SYNONYMS.get(normalized_condition_name)
        pathway_template = None
        if canonical_name:
            pathway_template = SPECIALTY_CARE_PATHWAYS.get(canonical_name)
        if pathway_template is None:
            pathway_template = SPECIALTY_CARE_PATHWAYS.get(condition_name) or SPECIALTY_CARE_PATHWAYS.get(
                normalized_condition_name
            )
        if not pathway_template:
            continue

        condition_records = [c for c in conditions if c.get("name") == condition_name]
        condition_id = condition_records[0].get("condition_id") if condition_records else None
        condition_category = condition_records[0].get("condition_category") if condition_records else None
        onset_dates = [
            _safe_parse_date(record.get("onset_date"))
            for record in condition_records
            if _safe_parse_date(record.get("onset_date")) is not None
        ]
        condition_encounters = _collect_encounters_for_condition(condition_name)
        encounter_dates = [
            _safe_parse_date(encounter.get("date"))
            for encounter in condition_encounters
            if _safe_parse_date(encounter.get("date")) is not None
        ]

        if onset_dates:
            anchor_date = min(onset_dates)
        elif encounter_dates:
            anchor_date = min(encounter_dates)
        else:
            anchor_date = today - timedelta(days=30)

        previous_anchor = anchor_date
        default_care_team = set(pathway_template.get("care_team", []))

        # Pre-compute encounter lookups for efficiency
        encounters_by_type = defaultdict(list)
        for encounter in condition_encounters:
            enc_type = encounter.get("type")
            enc_date = _safe_parse_date(encounter.get("date"))
            if enc_type and enc_date:
                encounters_by_type[enc_type].append((enc_date, encounter))

        for encounter_list in encounters_by_type.values():
            encounter_list.sort(key=lambda item: item[0])

        for stage in pathway_template.get("pathway", []):
            interval_days = stage.get("expected_interval_days", stage.get("offset_days", 30))
            scheduled_date = previous_anchor + timedelta(days=int(interval_days))
            window_days = stage.get("window_days", 45)
            due_date = scheduled_date + timedelta(days=int(window_days))

            activities: List[Dict[str, Any]] = []
            actual_event_dates: List[date] = []
            completed_requirements = 0
            total_requirements = 0

            def _register_activity(
                activity_type: str,
                code: str,
                *,
                display: Optional[str] = None,
                is_completed: bool = False,
                reference: Optional[str] = None,
                planned: Optional[date] = None,
                actual: Optional[date] = None,
            ) -> None:
                entry = {
                    "type": activity_type,
                    "code": code,
                    "display": display or code,
                    "status": "completed" if is_completed else "pending",
                    "reference": reference,
                }
                if planned:
                    entry["planned_date"] = planned.isoformat()
                if actual:
                    entry["actual_date"] = actual.isoformat()
                activities.append(entry)

            def _choose_encounter(encounter_types: List[str]) -> Optional[Dict[str, Any]]:
                candidates: List[Tuple[int, Tuple[date, Dict[str, Any]]]] = []
                for enc_type in encounter_types:
                    for enc_date, enc in encounters_by_type.get(enc_type, []):
                        delta = abs((enc_date - scheduled_date).days)
                        candidates.append((delta, (enc_date, enc)))
                if not candidates:
                    return None
                candidates.sort(key=lambda item: (item[0], item[1][0]))
                return candidates[0][1]

            # Encounter requirement
            encounter_types = stage.get("encounter_types", [])
            matched_encounter: Optional[Tuple[date, Dict[str, Any]]] = None
            if encounter_types:
                total_requirements += 1
                matched_encounter = _choose_encounter(encounter_types)
                encounter_completed = matched_encounter is not None and matched_encounter[0] <= today
                if encounter_completed:
                    completed_requirements += 1
                    actual_event_dates.append(matched_encounter[0])
                _register_activity(
                    "encounter",
                    ", ".join(encounter_types),
                    is_completed=encounter_completed,
                    reference=matched_encounter[1].get("encounter_id") if matched_encounter else None,
                    planned=scheduled_date,
                    actual=matched_encounter[0] if matched_encounter and encounter_completed else None,
                )

            def _handle_panel(panel_name: str) -> bool:
                candidates = observations_by_panel.get(panel_name, [])
                candidates = [
                    ( _safe_parse_date(ob.get("date")), ob )
                    for ob in candidates
                    if _safe_parse_date(ob.get("date")) is not None
                ]
                if not candidates:
                    return False
                candidates.sort(key=lambda item: (abs((item[0] - scheduled_date).days), item[0]))
                chosen_date, chosen_ob = candidates[0]
                completed = chosen_date <= today
                _register_activity(
                    "observation",
                    panel_name,
                    is_completed=completed,
                    reference=chosen_ob.get("observation_id"),
                    planned=scheduled_date,
                    actual=chosen_date if completed else None,
                )
                if completed:
                    actual_event_dates.append(chosen_date)
                return completed

            # Observation panels
            for panel_name in stage.get("required_panels", []):
                total_requirements += 1
                if _handle_panel(panel_name):
                    completed_requirements += 1

            for panel_name in stage.get("required_observation_panels", []):
                total_requirements += 1
                if _handle_panel(panel_name):
                    completed_requirements += 1

            # Observation types
            for obs_type in stage.get("required_observation_types", []):
                total_requirements += 1
                candidates = observations_by_type.get(obs_type, [])
                candidates = [
                    (_safe_parse_date(item.get("date")), item)
                    for item in candidates
                    if _safe_parse_date(item.get("date")) is not None
                ]
                if candidates:
                    candidates.sort(key=lambda item: (abs((item[0] - scheduled_date).days), item[0]))
                    chosen_date, chosen_ob = candidates[0]
                    completed = chosen_date <= today
                    if completed:
                        completed_requirements += 1
                        actual_event_dates.append(chosen_date)
                    _register_activity(
                        "observation",
                        obs_type,
                        is_completed=completed,
                        reference=chosen_ob.get("observation_id"),
                        planned=scheduled_date,
                        actual=chosen_date if completed else None,
                    )
                else:
                    _register_activity("observation", obs_type, planned=scheduled_date)

            # Procedures
            for proc_name in stage.get("required_procedures", []):
                total_requirements += 1
                candidates = procedures_by_name.get(proc_name, [])
                candidates = [
                    (_safe_parse_date(item.get("date")), item)
                    for item in candidates
                    if _safe_parse_date(item.get("date")) is not None
                ]
                if candidates:
                    candidates.sort(key=lambda item: (abs((item[0] - scheduled_date).days), item[0]))
                    chosen_date, chosen_proc = candidates[0]
                    completed = chosen_date <= today
                    if completed:
                        completed_requirements += 1
                        actual_event_dates.append(chosen_date)
                    _register_activity(
                        "procedure",
                        proc_name,
                        display=chosen_proc.get("name", proc_name),
                        is_completed=completed,
                        reference=chosen_proc.get("procedure_id"),
                        planned=scheduled_date,
                        actual=chosen_date if completed else None,
                    )
                else:
                    _register_activity("procedure", proc_name, planned=scheduled_date)

            # Medications by name
            for med_name in stage.get("required_medications", []):
                total_requirements += 1
                matches = medications_by_name.get(med_name.lower(), [])
                if matches:
                    med = matches[0]
                    start_date = _safe_parse_date(med.get("start_date")) or scheduled_date
                    completed = start_date <= today
                    if completed:
                        completed_requirements += 1
                        actual_event_dates.append(start_date)
                    _register_activity(
                        "medication",
                        med_name,
                        display=med.get("name", med_name),
                        is_completed=completed,
                        reference=med.get("medication_id"),
                        planned=scheduled_date,
                        actual=start_date if completed else None,
                    )
                else:
                    _register_activity("medication", med_name, planned=scheduled_date)

            # Medications by therapeutic class
            for med_class in stage.get("required_therapeutic_classes", []):
                total_requirements += 1
                matches = medications_by_class.get(med_class.lower(), [])
                if matches:
                    med = matches[0]
                    start_date = _safe_parse_date(med.get("start_date")) or scheduled_date
                    completed = start_date <= today
                    if completed:
                        completed_requirements += 1
                        actual_event_dates.append(start_date)
                    _register_activity(
                        "medication_class",
                        med_class,
                        display=med_class,
                        is_completed=completed,
                        reference=med.get("medication_id"),
                        planned=scheduled_date,
                        actual=start_date if completed else None,
                    )
                else:
                    _register_activity("medication_class", med_class, planned=scheduled_date)

            # Immunizations
            for vaccine_name in stage.get("required_immunizations", []):
                total_requirements += 1
                matches = immunizations_by_name.get(vaccine_name.lower(), [])
                if matches:
                    event = matches[0]
                    event_date = _safe_parse_date(event.get("date")) or scheduled_date
                    completed = event_date <= today
                    if completed:
                        completed_requirements += 1
                        actual_event_dates.append(event_date)
                    _register_activity(
                        "immunization",
                        vaccine_name,
                        is_completed=completed,
                        reference=event.get("immunization_id"),
                        planned=scheduled_date,
                        actual=event_date if completed else None,
                    )
                else:
                    _register_activity("immunization", vaccine_name, planned=scheduled_date)

            progress = (
                round(completed_requirements / total_requirements, 2)
                if total_requirements
                else 0.0
            )
            actual_date = min(actual_event_dates) if actual_event_dates else None

            if completed_requirements and completed_requirements == total_requirements:
                status = "completed"
            elif due_date < today:
                status = "overdue"
            elif completed_requirements > 0:
                status = "in-progress"
            else:
                status = "scheduled"

            status_counter[status] += 1

            care_team_members = set(default_care_team)
            care_team_members.update(stage.get("care_team", []))

            metric_status = "met" if total_requirements and completed_requirements == total_requirements else "not_met"
            linked_encounters = [
                act.get("reference")
                for act in activities
                if act["type"] == "encounter" and act.get("status") == "completed" and act.get("reference")
            ]

            care_plans.append(
                {
                    "care_plan_id": str(uuid.uuid4()),
                    "patient_id": patient["patient_id"],
                    "condition": condition_name,
                    "condition_id": condition_id,
                    "condition_category": condition_category,
                    "pathway_stage": stage.get("stage"),
                    "scheduled_date": scheduled_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "actual_date": actual_date.isoformat() if actual_date else None,
                    "status": status,
                    "progress": progress,
                    "completed_requirements": completed_requirements,
                    "total_requirements": total_requirements,
                    "quality_metric": stage.get("quality_metric"),
                    "metric_status": metric_status,
                    "priority": stage.get("priority", "routine"),
                    "care_team": ",".join(sorted(member for member in care_team_members if member)),
                    "responsible_roles": list(sorted(member for member in care_team_members if member)),
                    "activities": activities,
                    "notes": stage.get("notes", ""),
                    "linked_encounters": linked_encounters,
                    "planned_duration_days": window_days,
                    "target_metric": stage.get("quality_metric", ""),
                    "goal": stage.get("quality_metric", ""),
                }
            )

            previous_anchor = actual_date or scheduled_date

    scheduled_count = status_counter.get("scheduled", 0) + status_counter.get("in-progress", 0)
    patient["care_plan_summary"] = {
        "total": len(care_plans),
        "completed": status_counter.get("completed", 0),
        "scheduled": scheduled_count,
        "overdue": status_counter.get("overdue", 0),
        "in_progress": status_counter.get("in-progress", 0),
    }

    return care_plans

# Map conditions to likely medications, observations, and death causes
# PHASE 1: Evidence-based medication mappings with clinical accuracy
CONDITION_MEDICATIONS = {
    "Hypertension": {
        "first_line": ["Lisinopril", "Amlodipine", "Hydrochlorothiazide"],
        "second_line": ["Metoprolol", "Losartan", "Indapamide"],
        "combinations": ["Lisinopril/Hydrochlorothiazide"]
    },
    "Diabetes": {
        "first_line": ["Metformin"],
        "second_line": ["Glipizide", "Sitagliptin", "Empagliflozin"],
        "insulin": ["Insulin_glargine", "Insulin_lispro"]
    },
    "Asthma": {
        "controller": ["Fluticasone", "Budesonide/Formoterol"],
        "rescue": ["Albuterol", "Levalbuterol"]
    },
    "COPD": {
        "bronchodilators": ["Tiotropium", "Salmeterol/Fluticasone"],
        "rescue": ["Albuterol", "Ipratropium"]
    },
    "Heart Disease": {
        "statins": ["Atorvastatin", "Rosuvastatin", "Simvastatin"],
        "antiplatelet": ["Aspirin", "Clopidogrel"],
        "ace_inhibitors": ["Lisinopril", "Enalapril"]
    },
    "Obesity": {
        "lifestyle": [],  # Primarily lifestyle interventions
        "medications": ["Orlistat", "Phentermine"]  # When BMI >30 with comorbidities
    },
    "Depression": {
        "ssri": ["Sertraline", "Escitalopram", "Fluoxetine"],
        "snri": ["Venlafaxine", "Duloxetine"],
        "atypical": ["Bupropion", "Mirtazapine"]
    },
    "Anxiety": {
        "ssri": ["Sertraline", "Paroxetine", "Escitalopram"],
        "benzodiazepines": ["Lorazepam", "Alprazolam"],
        "other": ["Buspirone"]
    },
    "Arthritis": {
        "nsaids": ["Ibuprofen", "Naproxen", "Celecoxib"],
        "dmards": ["Methotrexate", "Hydroxychloroquine"],
        "biologics": ["Adalimumab", "Etanercept"]
    },
    "Cancer": {
        "chemotherapy": ["Doxorubicin", "Cyclophosphamide", "Paclitaxel"],
        "targeted": ["Trastuzumab", "Bevacizumab"],
        "supportive": ["Ondansetron", "Dexamethasone", "Filgrastim"]
    },
    "Flu": {
        "antivirals": ["Oseltamivir", "Zanamivir"],  # Only if started within 48 hours
        "supportive": ["Acetaminophen", "Ibuprofen"]
    },
    "COVID-19": {
        "antivirals": ["Paxlovid", "Remdesivir"],  # For high-risk patients
        "supportive": ["Acetaminophen", "Dexamethasone"]  # Dex for severe cases
    },
    "Migraine": {
        "acute": ["Sumatriptan", "Rizatriptan", "Ibuprofen"],
        "prophylaxis": ["Propranolol", "Topiramate", "Amitriptyline"]
    },
    "Allergy": {
        "antihistamines": ["Loratadine", "Cetirizine", "Fexofenadine"],
        "nasal_steroids": ["Fluticasone_nasal", "Mometasone_nasal"],
        "emergency": ["Epinephrine"]  # For severe allergic reactions
    },
    "Stroke": {
        "antiplatelet": ["Aspirin", "Clopidogrel"],
        "anticoagulants": ["Warfarin", "Apixaban", "Rivaroxaban"],
        "statins": ["Atorvastatin", "Rosuvastatin"]
    },
    "Alzheimer's": {
        "cholinesterase_inhibitors": ["Donepezil", "Rivastigmine", "Galantamine"],
        "nmda_antagonist": ["Memantine"],
        "behavioral": []  # Primarily non-pharmacological
    }
}

# Basic contraindications to prevent dangerous prescribing
MEDICATION_CONTRAINDICATIONS = {
    "Metformin": ["eGFR_less_than_30", "Severe_heart_failure", "Metabolic_acidosis"],
    "Lisinopril": ["Pregnancy", "Hyperkalemia", "Angioedema_history", "Bilateral_renal_artery_stenosis"],
    "Warfarin": ["Active_bleeding", "Severe_liver_disease", "Recent_surgery"],
    "Aspirin": ["Active_GI_bleeding", "Severe_asthma", "Age_under_16_with_viral_illness"],
    "Ibuprofen": ["Active_GI_bleeding", "Severe_kidney_disease", "Heart_failure"],
    "Lorazepam": ["Severe_respiratory_disease", "Myasthenia_gravis", "Sleep_apnea"],
    "Alprazolam": ["Severe_respiratory_disease", "Myasthenia_gravis", "Sleep_apnea"],
    "Methotrexate": ["Pregnancy", "Severe_liver_disease", "Severe_kidney_disease", "Active_infection"]
}
CONDITION_OBSERVATIONS = {
    "Hypertension": ["Blood Pressure"],
    "Diabetes": ["Hemoglobin A1c", "Cholesterol"],
    "Asthma": ["Heart Rate"],
    "COPD": ["Heart Rate"],
    "Heart Disease": ["Cholesterol"],
    "Obesity": ["Weight"],
    "Depression": [],
    "Anxiety": [],
    "Arthritis": [],
    "Cancer": [],
    "Flu": ["Temperature"],
    "COVID-19": ["Temperature"],
    "Migraine": [],
    "Allergy": [],
    "Stroke": [],
    "Alzheimer's": [],
}
# CONDITION_DEATH_CAUSES removed - replaced by CONDITION_MORTALITY_RISK with ICD-10-CM coding


def _get_age_bin_label(age: int) -> str:
    for (lower, upper), label in zip(AGE_BINS, AGE_BIN_LABELS):
        if lower <= age <= upper:
            return label
    return AGE_BIN_LABELS[-1]


def _calculate_condition_probability(
    entry: Dict[str, Any],
    patient: Dict[str, Any],
    genetic_adjustments: Dict[str, float],
    family_history_adjustments: Dict[str, float],
) -> float:
    base = entry.get("base_prevalence", 0.05)
    age = patient.get("age", 0)
    age_weights = entry.get("age_weights") or {}
    if age_weights:
        label = _get_age_bin_label(age)
        weight = age_weights.get(label)
        if weight is None and age_weights:
            weight = sum(age_weights.values()) / len(age_weights)
        if weight is not None:
            base *= max(0.3, 0.5 + float(weight))

    sex_weights = entry.get("sex_weights") or {}
    if sex_weights:
        gender_raw = (patient.get("gender") or "").lower()
        if gender_raw.startswith("m"):
            gender_key = "male"
        elif gender_raw.startswith("f"):
            gender_key = "female"
        else:
            gender_key = "other"
        weight = sex_weights.get(gender_key, sex_weights.get("other", 0.05))
        base *= max(0.3, 0.5 + float(weight))

    base = apply_sdoh_adjustments(entry.get("display", ""), base, patient)

    normalized_entry = entry.get("normalized") or _normalize_condition_display(entry.get("display", ""))
    display_lower = entry.get("display", "").lower()
    for risk_condition, boost in genetic_adjustments.items():
        risk_lower = risk_condition.lower()
        if risk_lower and (risk_lower in display_lower or risk_lower in normalized_entry):
            base += boost

    family_boost = 0.0
    if normalized_entry:
        family_boost = family_history_adjustments.get(normalized_entry, 0.0)
    if not family_boost and entry.get("display"):
        family_boost = family_history_adjustments.get(_normalize_condition_display(entry.get("display", "")), 0.0)
    base += family_boost

    sdoh_risk = patient.get("sdoh_risk_score", 0.0)
    if sdoh_risk:
        base *= 1 + min(sdoh_risk * 0.25, 0.3)

    return min(base, 0.95)


def _determine_condition_target(patient: Dict[str, Any], candidate_count: int) -> int:
    age = patient.get("age", 0)
    sdoh_risk = patient.get("sdoh_risk_score", 0.0)
    genetic_risk = patient.get("genetic_risk_score", 0.0)

    target = 1
    if age >= 18:
        target += 1
    if age >= 40:
        target += 1
    if age >= 65:
        target += 1
    if sdoh_risk > 0.4:
        target += 1
    if sdoh_risk > 0.7:
        target += 1
    if genetic_risk > 1.5:
        target += 1
    if patient.get("smoking_status") == "Current":
        target += 1

    target = min(target, max(1, candidate_count))
    return min(target, 8)


def assign_conditions(patient: Dict[str, Any]) -> List[str]:
    # Enrich patient risk profile prior to assigning conditions
    calculate_sdoh_risk(patient)
    genetic_adjustments = determine_genetic_risk(patient)
    family_history_adjustments = patient.get("family_history_adjustments", {})

    candidates: List[Tuple[str, float, Dict[str, Any]]] = []
    for name, entry in CONDITION_CATALOG.items():
        probability = _calculate_condition_probability(
            entry,
            patient,
            genetic_adjustments,
            family_history_adjustments,
        )
        if probability <= 0.005:
            continue
        candidates.append((name, probability, entry))

    if not candidates:
        fallback = random.choice(list(CONDITION_CATALOG.keys()))
        patient["condition_profile"] = [fallback]
        return [fallback]

    candidates.sort(key=lambda item: item[1], reverse=True)
    target = _determine_condition_target(patient, len(candidates))

    assigned: List[str] = []
    category_cap = Counter()
    for name, probability, entry in candidates:
        if len(assigned) >= target:
            break
        category = entry.get("category", "misc")
        cap = 3 if category in {"infectious_disease", "symptoms"} else 2
        if category_cap[category] >= cap:
            continue
        threshold = min(0.95, probability)
        if random.random() < threshold:
            assigned.append(name)
            category_cap[category] += 1

    if not assigned:
        assigned.append(candidates[0][0])

    # Add occasional acute events for additional realism
    acute_pool = [
        name
        for name, _, entry in candidates
        if entry.get("category") in {"infectious_disease", "injury", "symptoms"}
        and name not in assigned
    ]
    if acute_pool and random.random() < 0.35:
        assigned.append(random.choice(acute_pool))

    assigned = apply_comorbidity_relationships(assigned, patient)
    patient["condition_profile"] = assigned
    return assigned

def _sample_condition_profile(entry: Dict[str, Any]) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    profile = entry.get("severity_profile")
    if not profile:
        return None, None
    levels = profile.get("levels") or []
    if not levels:
        return None, None
    choice = random.choice(levels)
    coding = {
        "system": profile.get("code_system", "http://snomed.info/sct"),
        "code": choice.get("code", ""),
        "display": choice.get("display", ""),
        "type": profile.get("type"),
    }
    if profile.get("type") in STAGE_PROFILE_TYPES:
        return coding, None
    return None, coding


def parse_distribution(dist_str, valid_keys, value_type="str", default_dist=None):
    if not dist_str:
        return default_dist
    if isinstance(dist_str, dict):
        # Validate keys and sum
        total = sum(dist_str.values())
        for k in dist_str.keys():
            if k not in valid_keys:
                raise ValueError(f"Invalid key '{k}' in distribution. Valid: {valid_keys}")
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Distribution must sum to 1.0, got {total}")
        return dist_str
    dist = {}
    total = 0.0
    for part in dist_str.split(","):
        k, v = part.split(":")
        k = k.strip()
        v = float(v.strip())
        if value_type == "int":
            k = int(k)
        if k not in valid_keys:
            raise ValueError(f"Invalid key '{k}' in distribution. Valid: {valid_keys}")
        dist[k] = v
        total += v
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Distribution must sum to 1.0, got {total}")
    return dist

def sample_from_dist(dist):
    keys = list(dist.keys())
    weights = list(dist.values())
    return random.choices(keys, weights=weights, k=1)[0]

def generate_patient(_):
    """Generate patient using enhanced PatientRecord class"""
    birthdate = fake.date_of_birth(minimum_age=0, maximum_age=100)
    age = (datetime.now().date() - birthdate).days // 365
    income = random.randint(0, 200000) if age >= 18 else 0
    
    patient = PatientRecord(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        middle_name=fake.first_name()[:1],  # Simple middle initial
        gender=random.choice(GENDERS),
        birthdate=birthdate.isoformat(),
        age=age,
        race=random.choice(RACES),
        ethnicity=random.choice(ETHNICITIES),
        address=fake.street_address(),
        city=fake.city(),
        state=fake.state_abbr(),
        zip=fake.zipcode(),
        country="US",
        phone=fake.phone_number(),
        email=fake.email(),
        marital_status=random.choice(MARITAL_STATUSES),
        language=random.choice(LANGUAGES),
        insurance=random.choice(INSURANCES),
        ssn=fake.ssn(),
        # SDOH fields
        smoking_status=random.choice(SDOH_SMOKING),
        alcohol_use=random.choice(SDOH_ALCOHOL),
        education=random.choice(SDOH_EDUCATION) if age >= 18 else "None",
        employment_status=random.choice(SDOH_EMPLOYMENT) if age >= 16 else "Student",
        income=income,
        housing_status=random.choice(SDOH_HOUSING),
    )
    
    # Generate healthcare IDs
    patient.generate_vista_id()
    patient.generate_mrn()
    
    return patient

def generate_encounters(
    patient: Dict[str, Any],
    conditions: Optional[List[Dict[str, Any]]] = None,
    min_enc: int = 1,
    max_enc: int = 8,
    preassigned_conditions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Generate encounters driven by condition burden and care pathways."""

    age = int(patient.get("age", 0) or 0)
    birthdate_str = patient.get("birthdate")
    try:
        birthdate = datetime.strptime(str(birthdate_str), "%Y-%m-%d").date()
    except Exception:
        birthdate = datetime.now().date() - timedelta(days=age * 365)

    today = datetime.now().date()
    max_history_days = max((today - birthdate).days, 30)
    history_years = min(max(age // 20 + 1, 1), 5)
    history_days = min(history_years * 365, max_history_days)

    def _iter_condition_names() -> List[str]:
        names: List[str] = []
        if preassigned_conditions:
            names.extend(preassigned_conditions)
        elif patient.get("preassigned_conditions"):
            names.extend(patient.get("preassigned_conditions", []))
        elif patient.get("condition_profile"):
            names.extend(patient.get("condition_profile", []))

        if conditions:
            for cond in conditions:
                if isinstance(cond, str):
                    names.append(cond)
                elif isinstance(cond, dict):
                    name = cond.get("name") or cond.get("condition") or cond.get("display")
                    if name:
                        names.append(name)
        cleaned: List[str] = []
        seen: set[str] = set()
        for name in names:
            if not name:
                continue
            normalized = _normalize_condition_display(name)
            entry = CONDITION_CATALOG.get(normalized) or CONDITION_CATALOG.get(name)
            canonical = entry["display"] if entry else normalized or name
            if canonical not in seen:
                cleaned.append(canonical)
                seen.add(canonical)
        return cleaned

    assigned_conditions = _iter_condition_names()

    visit_weights: Dict[str, float] = defaultdict(float)
    visit_weights["wellness"] = 1.0 if age >= 2 else 0.3
    if age < 18:
        visit_weights["pediatrics"] += 0.8
    if age >= 65:
        visit_weights["primary_care"] += 0.6

    patient_transport = patient.get("transportation_access")
    if patient_transport == "limited":
        visit_weights["telehealth"] += 0.4

    category_condition_map: Dict[str, List[str]] = defaultdict(list)

    for condition_name in assigned_conditions:
        catalog_entry = CONDITION_CATALOG.get(condition_name)
        if not catalog_entry:
            normalized = _normalize_condition_display(condition_name)
            catalog_entry = CONDITION_CATALOG.get(normalized)
            if catalog_entry is None:
                continue
            condition_name = catalog_entry["display"]

        category = catalog_entry.get("category", "misc")
        category_condition_map[category].append(condition_name)

        contributions = CONDITION_CATEGORY_VISIT_CONTRIBUTIONS.get(category, DEFAULT_VISIT_CONTRIBUTIONS)
        severity_multiplier = 1.0
        if catalog_entry.get("severity_profile"):
            severity_multiplier += 0.2
        base_prev = float(catalog_entry.get("base_prevalence", 0) or 0)
        if base_prev >= 0.20:
            severity_multiplier += 0.1

        for blueprint_key, weight in contributions.items():
            visit_weights[blueprint_key] += weight * severity_multiplier

    if not assigned_conditions and age >= 18:
        visit_weights["primary_care"] += 0.4

    planned_blueprints: List[str] = []
    for blueprint_key, weight in visit_weights.items():
        blueprint = ENCOUNTER_BLUEPRINTS.get(blueprint_key)
        if not blueprint or weight <= 0:
            continue
        expected = weight * max(1.0, history_years)
        if blueprint_key == "wellness":
            expected = max(expected, history_years * 0.9)
        expected = min(expected, history_years * 4)
        count = max(0, int(expected))
        remainder = expected - count
        if random.random() < remainder:
            count += 1
        if blueprint_key == "wellness":
            count = max(count, 1)
        for _ in range(count):
            planned_blueprints.append(blueprint_key)

    if not planned_blueprints:
        planned_blueprints.append("primary_care")

    if len(planned_blueprints) < min_enc:
        planned_blueprints.extend(["primary_care"] * (min_enc - len(planned_blueprints)))

    soft_cap = max(max_enc, min(len(planned_blueprints), max_enc + max(0, len(assigned_conditions) // 2)))
    essential = {"wellness", "primary_care"}
    while len(planned_blueprints) > soft_cap:
        removed = False
        for idx, key in enumerate(planned_blueprints):
            if key not in essential:
                planned_blueprints.pop(idx)
                removed = True
                break
        if not removed:
            planned_blueprints = planned_blueprints[:soft_cap]
            break

    random.shuffle(planned_blueprints)

    def _pick_reason(blueprint_key: str, blueprint: Dict[str, Any]) -> str:
        options = blueprint.get("reason_options") or [blueprint.get("type", "Encounter")]
        reason = random.choice(options)
        categories = blueprint.get("categories") or []
        related: List[str] = []
        for cat in categories:
            related.extend(category_condition_map.get(cat, []))
        related = [cond for cond in related if cond]
        if related:
            focus = random.choice(related)
            return f"{reason} for {focus}"
        return reason

    def _build_location(department: str) -> str:
        suffix = random.choice(VISIT_LOCATION_SUFFIXES)
        return f"{department} - {fake.city()} {suffix}"

    def _build_provider(blueprint_key: str, department: str) -> str:
        if blueprint_key == "lab":
            return f"{fake.last_name()} Laboratory Technologist"
        if blueprint_key == "imaging":
            return f"{fake.last_name()} Imaging Specialist"
        if blueprint_key == "telehealth":
            return f"{fake.last_name()} Telehealth Clinician"
        if blueprint_key == "rehab":
            return f"{fake.last_name()} Physical Therapist"
        if blueprint_key == "behavioral_health":
            return f"{fake.last_name()} Behavioral Health Counselor"
        if blueprint_key == "urgent_care":
            return f"{fake.last_name()} Urgent Care PA"
        if blueprint_key == "emergency":
            return f"Dr. {fake.last_name()} (Emergency Medicine)"
        return f"Dr. {fake.last_name()}"

    encounters: List[Dict[str, Any]] = []
    for blueprint_key in planned_blueprints:
        blueprint = ENCOUNTER_BLUEPRINTS.get(blueprint_key)
        if not blueprint:
            continue

        offset_days = random.randint(0, max(1, history_days))
        encounter_date = today - timedelta(days=offset_days)
        if encounter_date < birthdate:
            encounter_date = birthdate + timedelta(days=random.randint(0, 30))

        if blueprint.get("service_category") == "E":
            hour = random.randint(0, 23)
        else:
            hour = random.randint(8, 17)
        minute = random.choice([0, 15, 30, 45])
        time_value = f"{hour:02d}:{minute:02d}"

        encounter = {
            "encounter_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "date": encounter_date.isoformat(),
            "time": time_value,
            "type": blueprint["type"],
            "reason": _pick_reason(blueprint_key, blueprint),
            "provider": _build_provider(blueprint_key, blueprint["department"]),
            "location": _build_location(blueprint["department"]),
            "clinic_stop": blueprint["stop_code"],
            "clinic_stop_description": blueprint.get("stop_description", ""),
            "service_category": blueprint.get("service_category", "A"),
            "department": blueprint["department"],
            "mode": blueprint.get("mode", "in-person"),
        }

        encounter["encounter_class"] = (
            "emergency"
            if encounter["service_category"] == "E"
            else "inpatient"
            if encounter["service_category"] == "I"
            else "ambulatory"
        )

        if blueprint_key in {"lab", "imaging"}:
            encounter["duration_minutes"] = random.randint(30, 90)
        elif blueprint_key == "emergency":
            encounter["duration_minutes"] = random.randint(120, 360)
        else:
            encounter["duration_minutes"] = random.randint(25, 75)

        categories = blueprint.get("categories") or []
        related: List[str] = []
        for cat in categories:
            related.extend(category_condition_map.get(cat, []))
        if related:
            encounter["related_conditions"] = ", ".join(sorted(set(related)))

        encounters.append(encounter)

    encounters.sort(key=lambda item: (item.get("date"), item.get("time", "")))
    return encounters

def generate_conditions(
    patient: Dict[str, Any],
    encounters: List[Dict[str, Any]],
    min_cond: int = 1,
    max_cond: int = 5,
    preassigned_conditions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Instantiate condition records using pre-assigned condition names."""

    assigned: List[str]
    if preassigned_conditions:
        assigned = list(preassigned_conditions)
    elif patient.get("preassigned_conditions"):
        assigned = list(patient.get("preassigned_conditions", []))
    else:
        assigned = assign_conditions(patient)
        patient["preassigned_conditions"] = assigned

    if len(assigned) > max_cond:
        assigned = assigned[:max_cond]

    condition_records: List[Dict[str, Any]] = []
    for cond in assigned:
        catalog_entry = CONDITION_CATALOG.get(cond) or CONDITION_CATALOG.get(_normalize_condition_display(cond), {})
        enc = random.choice(encounters) if encounters else None
        if enc is None and encounters:
            enc = encounters[0]
        encounter_id = enc.get("encounter_id") if enc else None
        onset_date = enc.get("date") if enc else patient.get("birthdate")
        stage_detail, severity_detail = _sample_condition_profile(catalog_entry)
        condition_records.append({
            "condition_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": encounter_id,
            "name": catalog_entry.get("display", cond),
            "status": random.choice(CONDITION_STATUSES),
            "onset_date": onset_date,
            "icd10_code": catalog_entry.get("icd10"),
            "snomed_code": catalog_entry.get("snomed"),
            "condition_category": catalog_entry.get("category"),
            "stage_detail": stage_detail,
            "severity_detail": severity_detail,
        })

    if len(condition_records) < min_cond and CONDITION_NAMES:
        fallback_candidates = [c for c in CONDITION_NAMES if c not in assigned]
        if fallback_candidates:
            cond = random.choice(fallback_candidates)
            catalog_entry = CONDITION_CATALOG.get(cond, {})
            enc = random.choice(encounters) if encounters else None
            encounter_id = enc.get("encounter_id") if enc else None
            onset_date = enc.get("date") if enc else patient.get("birthdate")
            stage_detail, severity_detail = _sample_condition_profile(catalog_entry)
            condition_records.append({
                "condition_id": str(uuid.uuid4()),
                "patient_id": patient["patient_id"],
                "encounter_id": encounter_id,
                "name": cond,
                "status": random.choice(CONDITION_STATUSES),
                "onset_date": onset_date,
                "icd10_code": catalog_entry.get("icd10"),
                "snomed_code": catalog_entry.get("snomed"),
                "condition_category": catalog_entry.get("category"),
                "stage_detail": stage_detail,
                "severity_detail": severity_detail,
            })

    patient["condition_profile"] = [record["name"] for record in condition_records]
    patient["preassigned_conditions"] = patient.get("condition_profile", [])

    assign_precision_markers(patient, condition_records)
    return condition_records

# PHASE 1: Evidence-based medication generation with contraindication checking
def generate_medications(patient, encounters, conditions=None, min_med=0, max_med=4):
    medications = []
    patient_contraindications = get_patient_contraindications(patient)
    
    # Add evidence-based medications for chronic conditions
    if conditions:
        for cond in conditions:
            condition_meds = prescribe_evidence_based_medication(patient, cond, encounters, patient_contraindications)
            medications.extend(condition_meds)

        precision_markers = patient.get("precision_markers", [])
        if precision_markers:
            markers_by_condition = defaultdict(list)
            for marker in precision_markers:
                if isinstance(marker, dict) and marker.get("condition"):
                    markers_by_condition[marker["condition"]].append(marker)

            for cond in conditions:
                for marker in markers_by_condition.get(cond.get("name"), []):
                    targeted_therapy = marker.get("targeted_therapy")
                    if targeted_therapy:
                        precision_med = create_medication_record(patient, cond, encounters, targeted_therapy, "precision_targeted")
                        precision_med["precision_marker"] = marker.get("marker")
                        precision_med["targeted_therapy"] = True
                        medications.append(precision_med)

                    if marker.get("care_plan") == "intensive_monitoring":
                        care_plan = cond.setdefault("care_plan", [])
                        if "intensive_monitoring" not in care_plan:
                            care_plan.append("intensive_monitoring")

    return medications

def get_patient_contraindications(patient):
    """Determine patient-specific contraindications based on age, conditions, etc."""
    contraindications = []
    
    age = patient.get("age", 0)
    gender = patient.get("gender", "")
    
    # Age-based contraindications
    if age < 16:
        contraindications.append("Age_under_16_with_viral_illness")
    
    # Gender-based contraindications
    if gender == "female" and 18 <= age <= 50:
        # Assume 5% chance of pregnancy for women of childbearing age
        if random.random() < 0.05:
            contraindications.append("Pregnancy")
    
    # Condition-based contraindications (simplified for Phase 1)
    # In a real system, this would check actual conditions
    if random.random() < 0.03:  # 3% chance of kidney disease
        contraindications.append("Severe_kidney_disease")
    if random.random() < 0.02:  # 2% chance of liver disease
        contraindications.append("Severe_liver_disease")
    if random.random() < 0.01:  # 1% chance of bleeding disorder
        contraindications.append("Active_bleeding")
    
    return contraindications

def prescribe_evidence_based_medication(patient, condition, encounters, contraindications):
    """Generate clinically appropriate medication prescriptions"""
    age = patient.get("age", 0)
    condition_name = condition["name"]
    treatment_guidelines = CONDITION_MEDICATIONS.get(condition_name, {})
    
    if not treatment_guidelines:
        return []
    
    medications = []
    
    # Select appropriate medication category based on condition
    if condition_name in ["Hypertension", "Heart Disease", "Stroke"]:
        # Prioritize first-line therapy
        if "first_line" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["first_line"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "first_line"))
    
    elif condition_name == "Diabetes":
        # Always start with Metformin if no contraindications
        metformin_safe = not any(contra in contraindications for contra in MEDICATION_CONTRAINDICATIONS.get("Metformin", []))
        if metformin_safe:
            medications.append(create_medication_record(patient, condition, encounters, "Metformin", "first_line"))
        else:
            # Use second-line if Metformin contraindicated
            selected_med = select_safe_medication(treatment_guidelines["second_line"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "second_line"))
    
    elif condition_name in ["Depression", "Anxiety"]:
        # Start with SSRI (safer than benzodiazepines)
        if "ssri" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["ssri"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "ssri"))
    
    elif condition_name in ["Flu", "COVID-19"]:
        # Only prescribe antivirals if within appropriate timeframe, otherwise supportive care
        if random.random() < 0.3:  # 30% get antivirals (early presentation)
            if "antivirals" in treatment_guidelines:
                selected_med = select_safe_medication(treatment_guidelines["antivirals"], contraindications)
                if selected_med:
                    medications.append(create_medication_record(patient, condition, encounters, selected_med, "antiviral"))
        
        # Add supportive care
        if "supportive" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["supportive"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "supportive"))
    
    else:
        # For other conditions, select from first available category
        for category, med_list in treatment_guidelines.items():
            if med_list:  # Skip empty categories
                selected_med = select_safe_medication(med_list, contraindications)
                if selected_med:
                    medications.append(create_medication_record(patient, condition, encounters, selected_med, category))
                    break
    
    return medications

def select_safe_medication(medication_list, contraindications):
    """Select a medication that doesn't have contraindications"""
    safe_medications = []

    for med in medication_list:
        med_contraindications = MEDICATION_CONTRAINDICATIONS.get(med, [])
        if not med_contraindications and "_" in med:
            med_contraindications = MEDICATION_CONTRAINDICATIONS.get(med.replace("_", " "), [])
        is_safe = not any(contra in contraindications for contra in med_contraindications)
        if is_safe:
            safe_medications.append(med)

    return random.choice(safe_medications) if safe_medications else None

def create_medication_record(patient, condition, encounters, medication_name, therapy_category):
    """Create a standardized medication record"""
    enc = random.choice(encounters) if encounters else None
    start_date = enc["date"] if enc else patient["birthdate"]

    if isinstance(start_date, str):
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date_obj = start_date

    today = datetime.now().date()
    if start_date_obj > today:
        start_date_obj = today
    start_date_iso = start_date_obj.isoformat()
    
    # Chronic medications typically don't have end dates
    chronic_conditions = ["Hypertension", "Diabetes", "Heart Disease", "Depression", "Anxiety"]
    if condition["name"] in chronic_conditions:
        end_date = None
    else:
        # Acute medications have limited duration
        if random.random() < 0.8:  # 80% have end date
            end_date_date = fake.date_between(start_date=start_date_obj, end_date=today)
            end_date = end_date_date.isoformat()
        else:
            end_date = None

    resolved_name, med_entry = resolve_medication_entry(medication_name)
    therapeutic_class = med_entry.get("therapeutic_class") if med_entry else ""
    route = THERAPEUTIC_CLASS_ROUTE_MAP.get(therapeutic_class, "oral")
    if therapeutic_class in {"chemotherapy", "targeted_therapy"}:
        route = "intravenous"
    monitoring_panels = MEDICATION_MONITORING_MAP.get(therapeutic_class, [])

    return {
        "medication_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": enc["encounter_id"] if enc else None,
        "name": resolved_name,
        "indication": condition["name"],
        "therapy_category": therapy_category,
        "start_date": start_date_iso,
        "end_date": end_date,
        "rxnorm_code": med_entry.get("rxnorm_code") if med_entry else med_entry.get("rxnorm") if med_entry else None,
        "ndc_code": med_entry.get("ndc") if med_entry else med_entry.get("ndc_code") if med_entry else None,
        "therapeutic_class": therapeutic_class,
        "route": route,
        "monitoring_panels": monitoring_panels,
        "status": "active" if not end_date else "completed",
    }

def generate_allergies(patient, min_all=0, max_all=2):
    n = random.randint(min_all, max_all)
    if not ALLERGEN_ENTRIES or n <= 0:
        return []

    allergies = []
    birthdate = patient.get("birthdate")
    today = datetime.now().date()
    birth_dt = None
    if birthdate:
        try:
            birth_dt = datetime.strptime(birthdate, "%Y-%m-%d").date()
        except ValueError:
            birth_dt = None

    for _ in range(n):
        allergen = random.choice(ALLERGEN_ENTRIES)
        reaction = random.choice(ALLERGY_REACTIONS)
        severity = random.choice(ALLERGY_SEVERITIES)

        recorded_date = None
        if birth_dt:
            delta_days = max((today - birth_dt).days, 1)
            random_offset = random.randint(0, delta_days)
            recorded_date = (birth_dt + timedelta(days=random_offset)).isoformat()

        allergies.append({
            "allergy_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "substance": allergen["display"],
            "category": allergen.get("category"),
            "reaction": reaction["display"],
            "reaction_code": reaction.get("code"),
            "reaction_system": reaction.get("system"),
            "severity": severity["display"],
            "severity_code": severity.get("code"),
            "severity_system": severity.get("system"),
            "rxnorm_code": allergen.get("rxnorm_code"),
            "unii_code": allergen.get("unii_code"),
            "snomed_code": allergen.get("snomed_code"),
            "recorded_date": recorded_date,
        })

    return allergies

# PHASE 2: Enhanced procedure generation with clinical appropriateness and CPT coding
def generate_procedures(patient, encounters, conditions=None, min_proc=0, max_proc=3):
    procedures = []
    age = patient.get("age", 30)
    
    # Generate condition-appropriate procedures
    if conditions:
        for condition in conditions:
            condition_procedures = generate_condition_procedures(patient, encounters, condition)
            procedures.extend(condition_procedures)
    
    # Add age-appropriate screening procedures
    screening_procedures = generate_screening_procedures(patient, encounters, age)
    procedures.extend(screening_procedures)
    
    # Add random procedures (simulate incidental findings or routine care)
    n_random = random.randint(min_proc, max_proc)
    for _ in range(n_random):
        random_procedure = generate_random_procedure(patient, encounters)
        if random_procedure:
            procedures.append(random_procedure)
    
    return procedures

def generate_condition_procedures(patient, encounters, condition):
    """Generate clinically appropriate procedures for specific conditions"""
    procedures = []
    condition_name = condition["name"]
    
    # Find appropriate procedures for this condition
    applicable_procedures = []
    
    for specialty, procedure_categories in CLINICAL_PROCEDURES.items():
        for category, procedure_list in procedure_categories.items():
            for procedure in procedure_list:
                if condition_name in procedure.get("conditions", []):
                    applicable_procedures.append({
                        **procedure,
                        "specialty": specialty,
                        "category": category
                    })
    
    # Select procedures based on clinical appropriateness
    for procedure in applicable_procedures:
        # Probability based on complexity and clinical need
        complexity_probability = {
            "routine": 0.6,
            "moderate": 0.3,
            "high": 0.1,
            "very_high": 0.05
        }
        
        complexity = procedure.get("complexity", "routine")
        if random.random() < complexity_probability.get(complexity, 0.3):
            enc = random.choice(encounters) if encounters else None
            date = enc["date"] if enc else patient["birthdate"]
            
            # Determine outcome based on complexity
            outcome = generate_procedure_outcome(complexity, patient.get("age", 30))
            
            procedures.append({
                "procedure_id": str(uuid.uuid4()),
                "patient_id": patient["patient_id"],
                "encounter_id": enc["encounter_id"] if enc else None,
                "name": procedure["name"],
                "cpt_code": procedure.get("cpt", ""),
                "specialty": procedure["specialty"],
                "category": procedure["category"],
                "complexity": complexity,
                "indication": condition_name,
                "date": date,
                "outcome": outcome,
            })
    
    return procedures

def generate_screening_procedures(patient, encounters, age):
    """Generate age-appropriate screening procedures"""
    procedures = []
    gender = patient.get("gender", "")
    
    # Age-based screening guidelines
    screening_guidelines = {
        "Colonoscopy": {"age_range": (50, 75), "frequency_years": 10, "gender": "both"},
        "Mammography": {"age_range": (40, 74), "frequency_years": 2, "gender": "female"},
        "Cervical_Cancer_Screening": {"age_range": (21, 65), "frequency_years": 3, "gender": "female"},
        "Prostate_Screening": {"age_range": (50, 75), "frequency_years": 2, "gender": "male"},
        "Bone_Density_Scan": {"age_range": (65, 85), "frequency_years": 2, "gender": "female"},
        "Cardiac_Stress_Test": {"age_range": (40, 80), "frequency_years": 5, "gender": "both"}
    }
    
    for procedure_name, guidelines in screening_guidelines.items():
        age_min, age_max = guidelines["age_range"]
        required_gender = guidelines["gender"]
        
        # Check if patient meets screening criteria
        if age_min <= age <= age_max:
            if required_gender == "both" or gender == required_gender:
                # 70% chance of having age-appropriate screening
                if random.random() < 0.7:
                    enc = random.choice(encounters) if encounters else None
                    date = enc["date"] if enc else patient["birthdate"]
                    
                    # Find CPT code from clinical procedures
                    cpt_code = find_procedure_cpt(procedure_name)
                    
                    procedures.append({
                        "procedure_id": str(uuid.uuid4()),
                        "patient_id": patient["patient_id"],
                        "encounter_id": enc["encounter_id"] if enc else None,
                        "name": procedure_name,
                        "cpt_code": cpt_code,
                        "specialty": "Preventive_Medicine",
                        "category": "screening",
                        "complexity": "routine",
                        "indication": "routine_screening",
                        "date": date,
                        "outcome": "normal" if random.random() < 0.85 else "abnormal",
                    })
    
    return procedures

def generate_random_procedure(patient, encounters):
    """Generate random procedure from legacy list for variety"""
    enc = random.choice(encounters) if encounters else None
    date = enc["date"] if enc else patient["birthdate"]

    # Use legacy procedure list for backward compatibility
    procedure_name = random.choice(PROCEDURES)
    procedure_entry = PROCEDURE_CATALOG.get(procedure_name, {})

    return {
        "procedure_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": enc["encounter_id"] if enc else None,
        "name": procedure_name,
        "cpt_code": procedure_entry.get("cpt", ""),
        "snomed_code": procedure_entry.get("snomed"),
        "specialty": "General",
        "category": "other",
        "complexity": "routine",
        "indication": "clinical_judgment",
        "date": date,
        "outcome": random.choice(["successful", "complication", "failed"]),
    }

def generate_procedure_outcome(complexity, age):
    """Generate realistic procedure outcomes based on complexity and patient age"""
    base_success_rate = 0.95
    
    # Adjust success rate based on complexity
    complexity_adjustment = {
        "routine": 0.0,
        "moderate": -0.05,
        "high": -0.10,
        "very_high": -0.20
    }
    
    # Adjust success rate based on age (older patients have higher complication rates)
    age_adjustment = 0.0
    if age >= 65:
        age_adjustment = -0.05
    elif age >= 80:
        age_adjustment = -0.10
    
    final_success_rate = base_success_rate + complexity_adjustment.get(complexity, 0) + age_adjustment
    
    rand = random.random()
    if rand < final_success_rate:
        return "successful"
    elif rand < final_success_rate + 0.03:  # 3% complication rate
        return "complication"
    else:
        return "failed"

def find_procedure_cpt(procedure_name):
    """Find CPT code for a procedure"""
    for specialty, procedure_categories in CLINICAL_PROCEDURES.items():
        for category, procedure_list in procedure_categories.items():
            for procedure in procedure_list:
                if procedure_name.lower() in procedure["name"].lower():
                    return procedure.get("cpt", "")
    return ""

def generate_immunizations(
    patient: Dict[str, Any],
    encounters: List[Dict[str, Any]],
    allergies: Optional[List[Dict[str, Any]]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    min_imm: int = 0,
    max_imm: int = 3,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    # min_imm and max_imm retained for backward compatibility but handled implicitly
    age_months, birthdate, today = _patient_age_context(patient)
    series_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    series_immunizations, followup_observations = _generate_series_immunizations(
        patient,
        encounters,
        allergies,
        conditions,
        age_months,
        birthdate,
        today,
        series_history,
    )

    recurrent_immunizations = _generate_recurrent_immunizations(
        patient,
        encounters,
        allergies,
        conditions,
        age_months,
        birthdate,
        today,
        series_history,
    )

    immunizations = series_immunizations + recurrent_immunizations
    immunizations.sort(key=lambda record: record.get("date", ""))
    return immunizations, followup_observations

# PHASE 2: Enhanced observation generation with comprehensive lab panels
def generate_observations(patient, encounters, conditions=None, medications=None, min_obs=1, max_obs=8):
    observations = []
    age = patient.get("age", 30)
    gender = patient.get("gender", "")
    
    # Determine appropriate lab panels based on conditions and demographics
    required_panels = determine_lab_panels(patient, conditions, medications)
    
    # Generate condition-specific lab panels
    for panel_name in required_panels:
        panel_observations = generate_lab_panel(patient, encounters, panel_name, age, gender)
        observations.extend(panel_observations)
    
    # Add routine vitals and basic observations
    routine_obs = generate_routine_observations(patient, encounters, min_obs, max_obs)
    observations.extend(routine_obs)
    
    return observations

def determine_lab_panels(patient, conditions, medications=None):
    """Determine which lab panels are clinically appropriate"""
    panels = set()
    age = patient.get("age", 30)
    
    # Age-based routine screening
    if age >= 18:
        panels.add("Basic_Metabolic_Panel")
    if age >= 20:
        panels.add("Lipid_Panel")
    if age >= 30:
        panels.add("Complete_Blood_Count")
    
    # Condition-based lab panels
    if conditions:
        for condition in conditions:
            condition_name = condition["name"]
            complexity_model = CONDITION_COMPLEXITY_MODELS.get(condition_name, {})
            
            if condition_name == "Diabetes":
                panels.add("Diabetes_Monitoring")
                panels.add("Basic_Metabolic_Panel")
                panels.add("Lipid_Panel")
            elif condition_name in ["Heart Disease", "Hypertension"]:
                panels.add("Lipid_Panel")
                panels.add("Cardiac_Markers")
                panels.add("Cardiology_Followup")
            elif condition_name == "Cancer":
                panels.add("Complete_Blood_Count")
                panels.add("Liver_Function_Panel")
                panels.add("Oncology_Tumor_Markers")
            elif "Thyroid" in condition_name or random.random() < 0.1:  # 10% get thyroid screening
                panels.add("Thyroid_Function")
            if condition_name in ["COPD", "Asthma"]:
                panels.add("Pulmonary_Function")
            if condition_name in ["Depression", "Anxiety", "Major_Depressive_Disorder"]:
                panels.add("Behavioral_Health_Assessments")
    
    med_classes = set()
    if medications:
        for med in medications:
            med_class = (med.get("therapeutic_class") or "").lower()
            if med_class:
                med_classes.add(med_class)
            for panel in med.get("monitoring_panels", []):
                if panel:
                    panels.add(panel)
        med_names = {(med.get("name") or "").lower() for med in medications}
        if med_classes.intersection({"anticoagulant", "antiplatelet"}) or any(name in med_names for name in {"warfarin", "apixaban", "rivaroxaban"}):
            panels.add("Coagulation_Panel")
        if med_classes.intersection({"statin", "ace_inhibitor", "arb", "thiazide_diuretic", "loop_diuretic", "aldosterone_antagonist"}):
            panels.add("Renal_Function_Panel")
            panels.add("Lipid_Panel")
        if med_classes.intersection({"sglt2_inhibitor", "basal_insulin", "rapid_insulin", "glp1_agonist", "sulfonylurea"}):
            panels.add("Diabetes_Monitoring")
        if med_classes.intersection({"bronchodilator", "inhaled_combo", "inhaled_steroid", "long_acting_anticholinergic"}):
            panels.add("Pulmonary_Function")
        if med_classes.intersection({"chemotherapy", "targeted_therapy"}):
            panels.add("Oncology_Tumor_Markers")
            panels.add("Complete_Blood_Count")
        if med_classes.intersection({"anticoagulant", "chemotherapy"}):
            panels.add("Cardiac_Markers_Advanced")
        if med_classes.intersection({"glucocorticoid", "antiviral", "antibiotic"}):
            panels.add("Inflammatory_Markers")
        if med_classes.intersection({"thyroid_replacement"}):
            panels.add("Thyroid_Function")

    # Random additional panels (simulate clinical judgment)
    if random.random() < 0.3:  # 30% chance of inflammatory markers
        panels.add("Inflammatory_Markers")
    
    return list(panels)

def generate_lab_panel(patient, encounters, panel_name, age, gender):
    """Generate all tests in a specific lab panel"""
    panel_data = COMPREHENSIVE_LAB_PANELS.get(panel_name, {})
    tests = panel_data.get("tests", [])
    observations = []
    
    for test in tests:
        test_name = test["name"]
        value = generate_lab_value(test_name, age, gender, test)
        value_numeric = value

        # Select appropriate encounter
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        
        # Determine if value is critical
        is_critical = is_critical_value(value, test)
        status = "critical" if is_critical else "normal" if is_normal_value(value, test, age, gender) else "abnormal"
        
        observations.append({
            "observation_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "type": test_name,
            "loinc_code": test.get("loinc", ""),
            "value": str(value),
            "value_numeric": value_numeric,
            "units": test.get("units", ""),
            "reference_range": get_reference_range_string(test, age, gender),
            "status": status,
            "date": date,
            "panel": panel_name
        })
    
    return observations

def generate_lab_value(test_name, age, gender, test_config):
    """Generate clinically realistic lab values"""
    normal_range = get_adjusted_normal_range(test_name, age, gender, test_config)
    
    # 85% of values should be normal, 10% slightly abnormal, 5% significantly abnormal
    rand = random.random()
    
    if rand < 0.85:  # Normal values
        return round(random.uniform(normal_range[0], normal_range[1]), 2)
    elif rand < 0.95:  # Slightly abnormal
        if random.random() < 0.5:  # Below normal
            low_abnormal = normal_range[0] * 0.8
            return round(random.uniform(low_abnormal, normal_range[0]), 2)
        else:  # Above normal
            high_abnormal = normal_range[1] * 1.2
            return round(random.uniform(normal_range[1], high_abnormal), 2)
    else:  # Significantly abnormal
        critical_low = test_config.get("critical_low")
        critical_high = test_config.get("critical_high")
        
        if random.random() < 0.5 and critical_low:  # Critically low
            return round(random.uniform(critical_low, normal_range[0] * 0.7), 2)
        elif critical_high:  # Critically high
            return round(random.uniform(normal_range[1] * 1.5, critical_high), 2)
        else:
            return round(random.uniform(normal_range[0], normal_range[1]), 2)

def get_adjusted_normal_range(test_name, age, gender, test_config):
    """Get age/gender adjusted reference ranges"""
    base_range = test_config.get("normal_range", (0, 100))
    
    # Check for age/gender adjustments
    adjustments = AGE_GENDER_ADJUSTMENTS.get(test_name, {})
    
    if gender in adjustments:
        return adjustments[gender].get("normal_range", base_range)
    elif age >= 65 and "elderly" in adjustments:
        return adjustments["elderly"].get("normal_range", base_range)
    elif age < 18 and "pediatric" in adjustments:
        return adjustments["pediatric"].get("normal_range", base_range)
    elif age >= 18 and "adult" in adjustments:
        return adjustments["adult"].get("normal_range", base_range)
    
    return base_range

def is_critical_value(value, test_config):
    """Determine if a lab value is critical"""
    critical_low = test_config.get("critical_low")
    critical_high = test_config.get("critical_high")
    
    if critical_low and value <= critical_low:
        return True
    if critical_high and value >= critical_high:
        return True
    
    return False

def is_normal_value(value, test_config, age, gender):
    """Determine if a lab value is within normal range"""
    normal_range = get_adjusted_normal_range(test_config["name"], age, gender, test_config)
    return normal_range[0] <= value <= normal_range[1]

def get_reference_range_string(test_config, age, gender):
    """Generate reference range string for display"""
    normal_range = get_adjusted_normal_range(test_config["name"], age, gender, test_config)
    units = test_config.get("units", "")
    return f"{normal_range[0]}-{normal_range[1]} {units}".strip()

def generate_routine_observations(patient, encounters, min_obs, max_obs):
    """Generate basic vital signs and measurements"""
    n = random.randint(min_obs, max_obs)
    observations = []
    
    for _ in range(n):
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        obs_type = random.choice(OBSERVATION_TYPES)
        value = None
        value_numeric = None
        
        if obs_type == "Height":
            value = f"{round(random.uniform(140, 200), 1)}"
            value_numeric = float(value)
        elif obs_type == "Weight":
            value = f"{round(random.uniform(40, 150), 1)}"
            value_numeric = float(value)
        elif obs_type == "Blood Pressure":
            systolic = random.randint(90, 180)
            diastolic = random.randint(60, 110)
            value = f"{systolic}/{diastolic}"
            value_numeric = systolic
        elif obs_type == "Heart Rate":
            value_numeric = random.randint(50, 120)
            value = str(value_numeric)
        elif obs_type == "Temperature":
            value = f"{round(random.uniform(36.0, 39.0), 1)}"
            value_numeric = float(value)
        elif obs_type == "Hemoglobin A1c":
            value = f"{round(random.uniform(4.5, 12.0), 1)}"
            value_numeric = float(value)
        elif obs_type == "Cholesterol":
            value_numeric = random.randint(120, 300)
            value = str(value_numeric)

        observations.append({
            "observation_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "type": obs_type,
            "value": value,
            "value_numeric": value_numeric,
            "date": date,
        })
    
    return observations

def _baseline_mortality_probability(age: int, gender: Optional[str]) -> float:
    if age >= 95:
        base = 0.45
    elif age >= 85:
        base = 0.28
    elif age >= 75:
        base = 0.18
    elif age >= 65:
        base = 0.11
    elif age >= 55:
        base = 0.06
    elif age >= 45:
        base = 0.035
    elif age >= 30:
        base = 0.02
    else:
        base = 0.01

    normalized_gender = (gender or "").lower()
    if normalized_gender.startswith("m"):
        base *= 1.1
    elif normalized_gender.startswith("f"):
        base *= 0.95

    return min(base, 0.9)


# PHASE 1: Clinically accurate death generation with ICD-10-CM coding
def generate_death(patient, conditions=None, family_history=None):
    """Generate clinically accurate death with proper ICD-10-CM coding and age stratification"""

    age = int(patient.get("age", 0) or 0)
    gender = patient.get("gender", "")
    base_probability = _baseline_mortality_probability(age, gender)

    sdoh_score = patient.get("sdoh_risk_score", 0.0) or 0.0
    base_probability *= 1 + min(sdoh_score * 0.6, 0.4)

    if patient.get("smoking_status") == "Current":
        base_probability *= 1.2
    if patient.get("alcohol_use") == "Heavy":
        base_probability *= 1.1

    death_risk_multiplier = 1.0
    likely_causes: List[Dict[str, Any]] = []
    contributing_causes: List[str] = []

    if conditions:
        for condition in conditions:
            name = condition.get("name") or condition.get("condition")
            if not name:
                continue
            risk_data = CONDITION_MORTALITY_RISK.get(name, {})
            death_risk_multiplier *= risk_data.get("relative_risk", 1.0)
            likely_causes.extend(risk_data.get("likely_deaths", []))
            contributing_causes.append(name)

    if family_history:
        for entry in family_history:
            boost = entry.get("risk_modifier")
            if boost:
                death_risk_multiplier *= 1 + min(float(boost), 0.25)
            condition_name = entry.get("condition_display") or entry.get("condition")
            if condition_name:
                history_risk = CONDITION_MORTALITY_RISK.get(condition_name, {})
                likely_causes.extend(history_risk.get("likely_deaths", []))

    death_probability = min(base_probability * death_risk_multiplier, 0.95)
    if random.random() >= death_probability:
        return None

    birth = datetime.strptime(patient["birthdate"], "%Y-%m-%d").date()
    if age <= 1:
        death_age = 1
    else:
        mean_death_age = max(1, age - random.randint(0, 4))
        death_age = max(1, min(age, int(random.gauss(mean_death_age, 3))))

    death_date = birth + timedelta(days=death_age * 365)
    if death_date > datetime.now().date():
        death_date = datetime.now().date()

    age_group = None
    for (min_age, max_age), causes in DEATH_CAUSES_BY_AGE.items():
        if min_age <= age <= max_age:
            age_group = (min_age, max_age)
            break
    if not age_group:
        age_group = (65, 120)
    age_appropriate_causes = DEATH_CAUSES_BY_AGE[age_group]

    cause_pool = likely_causes if likely_causes else age_appropriate_causes
    primary_cause = weighted_choice(cause_pool)

    manner_of_death = "Natural"
    icd_code = primary_cause.get("icd10", "")
    if icd_code.startswith(("V", "W", "X", "Y")):
        if icd_code.startswith("X8"):
            manner_of_death = "Suicide"
        elif icd_code.startswith("X9") or icd_code.startswith("Y0"):
            manner_of_death = "Homicide"
        else:
            manner_of_death = "Accident"

    contributing_joined = "; ".join(dict.fromkeys(contributing_causes))

    return {
        "patient_id": patient.get("patient_id"),
        "death_date": death_date.isoformat(),
        "age_at_death": death_age,
        "primary_cause_code": icd_code,
        "primary_cause_description": primary_cause.get("description", ""),
        "contributing_causes": contributing_joined,
        "manner_of_death": manner_of_death,
        "death_certificate_type": "Standard" if manner_of_death == "Natural" else "Coroner",
        "risk_multiplier": round(death_risk_multiplier, 3),
    }

def weighted_choice(choices):
    """Select an item from choices based on weight"""
    total = sum(choice["weight"] for choice in choices)
    r = random.uniform(0, total)
    upto = 0
    for choice in choices:
        if upto + choice["weight"] >= r:
            return choice
        upto += choice["weight"]
    return choices[-1]  # Fallback

def generate_family_history(
    patient: Dict[str, Any],
    min_fam: int = 0,
    max_fam: int = 4,
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """Generate structured family history entries and risk adjustments."""

    if max_fam < min_fam:
        max_fam = min_fam

    entries: List[Dict[str, Any]] = []
    adjustments: Dict[str, float] = {}
    patient_id = patient.get("patient_id", "")

    if max_fam == 0:
        patient["family_history_entries"] = []
        patient["family_history_adjustments"] = {}
        return [], {}

    candidate_profiles = FAMILY_HISTORY_PROFILES.copy()
    random.shuffle(candidate_profiles)

    def _record_entry(
        profile: Dict[str, Any],
        relation: str,
        source: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        normalized_condition, catalog_entry = _resolve_condition_catalog_entry(profile.get("condition", ""))
        relation_code = RELATION_ROLE_CODES.get(relation, "")
        relation_factor = FAMILY_RELATIONSHIP_FACTORS.get(relation, 0.85)
        risk_modifier = float(profile.get("risk_boost", 0.05) or 0.05) * relation_factor
        onset_age = _sample_family_history_onset(profile)

        entry = _build_family_history_entry(
            patient,
            profile,
            relation,
            relation_code,
            onset_age,
            risk_modifier,
            normalized_condition,
            catalog_entry,
            source=source,
        )

        if extra_fields:
            entry.update(extra_fields)

        if any(existing.get("condition_code") == entry.get("condition_code") and existing.get("relation") == relation for existing in entries):
            return None

        entries.append(entry)
        existing_boost = adjustments.get(normalized_condition, 0.0)
        adjustments[normalized_condition] = round(min(existing_boost + risk_modifier, 0.3), 4)
        return entry

    for profile in candidate_profiles:
        if len(entries) >= max_fam:
            break
        probability = _family_history_probability(profile, patient)
        if random.random() > probability:
            continue
        relation = _choose_family_relation(profile.get("relations", {}))
        if not relation:
            continue
        created = _record_entry(profile, relation, source="profile")
        if created and len(entries) < max_fam and random.random() < 0.25:
            alt_relations = {rel: weight for rel, weight in profile.get("relations", {}).items() if rel != relation}
            alt_relation = _choose_family_relation(alt_relations) if alt_relations else None
            if alt_relation:
                _record_entry(profile, alt_relation, source="profile")

    if len(entries) < min_fam:
        profiles_by_weight = sorted(
            candidate_profiles,
            key=lambda p: _family_history_probability(p, patient),
            reverse=True,
        )
        for profile in profiles_by_weight:
            if len(entries) >= min_fam:
                break
            if any(_normalize_condition_display(e.get("condition_display", "")) == _normalize_condition_display(profile.get("condition", "")) for e in entries):
                continue
            relation = _choose_family_relation(profile.get("relations", {})) or "Mother"
            _record_entry(profile, relation, source="forced")

    genetic_markers = patient.get("genetic_markers", [])
    for marker in genetic_markers:
        if len(entries) >= max_fam:
            break
        marker_name = marker.get("name") if isinstance(marker, dict) else str(marker)
        marker_config = GENETIC_RISK_FACTORS.get(marker_name, {})
        family_conditions = marker_config.get("family_history_conditions", [])
        if not family_conditions:
            continue
        for condition in family_conditions:
            if len(entries) >= max_fam:
                break
            normalized_condition, catalog_entry = _resolve_condition_catalog_entry(condition)
            if any(_normalize_condition_display(entry.get("condition_display", "")) == normalized_condition for entry in entries):
                continue
            relation = random.choice(["Mother", "Father", "Sibling"])
            relation_code = RELATION_ROLE_CODES.get(relation, "")
            relation_factor = FAMILY_RELATIONSHIP_FACTORS.get(relation, 0.85)
            risk_modifier = 0.1 * relation_factor
            profile_stub = {
                "condition": condition,
                "category": catalog_entry.get("category") if catalog_entry else None,
                "risk_boost": risk_modifier,
                "notes": f"Genetic risk marker {marker_name}",
            }
            entry = _build_family_history_entry(
                patient,
                profile_stub,
                relation,
                relation_code,
                _sample_family_history_onset({"onset_mean": patient.get("age", 40), "onset_sd": 6}),
                risk_modifier,
                normalized_condition,
                catalog_entry,
                source="genetic_marker",
            )
            entry["genetic_marker"] = marker_name
            entries.append(entry)
            existing_boost = adjustments.get(normalized_condition, 0.0)
            adjustments[normalized_condition] = round(min(existing_boost + risk_modifier, 0.3), 4)

    patient["family_history_entries"] = entries
    patient["family_history_adjustments"] = adjustments
    return entries, adjustments
