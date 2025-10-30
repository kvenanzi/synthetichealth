"""Patient-level lifecycle generation helpers."""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict

from faker import Faker

from ..constants import (
    ETHNICITIES,
    INSURANCES,
    LANGUAGES,
    MARITAL_STATUSES,
    MAX_PATIENT_AGE,
)
from ..models import Patient as LifecyclePatient
from .clinical import sample_from_dist

fake = Faker()


def _normalize_gender_distribution(gender_dist: Dict[str, Any] | None) -> Dict[str, float]:
    """Collapse configured gender labels to male/female buckets."""

    cleaned: Dict[str, float] = {"male": 0.0, "female": 0.0}
    if not gender_dist:
        cleaned["male"] = cleaned["female"] = 0.5
        return cleaned

    for raw_label, weight in gender_dist.items():
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            continue
        label = str(raw_label).strip().lower()
        if label.startswith("m"):
            cleaned["male"] += weight_value
        elif label.startswith("f"):
            cleaned["female"] += weight_value

    if cleaned["male"] <= 0 and cleaned["female"] <= 0:
        cleaned["male"] = cleaned["female"] = 0.5
    return cleaned


def _select_binary_gender(gender_dist: Dict[str, Any] | None) -> str:
    """Sample a gender value constrained to male/female."""

    cleaned = _normalize_gender_distribution(gender_dist)
    choice = sample_from_dist(cleaned)
    return "male" if str(choice).lower().startswith("m") else "female"


def generate_patient_demographics(
    age_dist,
    gender_dist,
    race_dist,
    smoking_dist,
    alcohol_dist,
    education_dist,
    employment_dist,
    housing_dist,
) -> Dict[str, Any]:
    """Return core demographic and SDOH attributes sampled from configured distributions."""

    age_bin_label = sample_from_dist(age_dist)
    a_min, a_max = map(int, age_bin_label.split("-"))
    a_max = min(a_max, MAX_PATIENT_AGE)
    if a_min > a_max:
        a_min = max(0, min(a_min, MAX_PATIENT_AGE))
        a_max = a_min

    today = datetime.now().date()
    min_days = int(a_min * 365.25)
    max_days = int((a_max + 1) * 365.25) - 1
    if max_days < min_days:
        max_days = min_days
    age_days = random.randint(min_days, max_days)
    birthdate = today - timedelta(days=age_days)
    age = min(int((today - birthdate).days // 365), MAX_PATIENT_AGE)

    return {
        "age": age,
        "birthdate": birthdate,
        "income": random.randint(0, 200000) if age >= 18 else 0,
        "gender": _select_binary_gender(gender_dist),
        "race": sample_from_dist(race_dist),
        "smoking_status": sample_from_dist(smoking_dist),
        "alcohol_use": sample_from_dist(alcohol_dist),
        "education": sample_from_dist(education_dist) if age >= 18 else "None",
        "employment_status": sample_from_dist(employment_dist) if age >= 16 else "Student",
        "housing_status": sample_from_dist(housing_dist),
    }


def generate_patient_profile(
    age_dist,
    gender_dist,
    race_dist,
    smoking_dist,
    alcohol_dist,
    education_dist,
    employment_dist,
    housing_dist,
    *,
    faker: Faker | None = None,
) -> Dict[str, Any]:
    """Sample demographics and synthesize a patient profile dictionary.

    The resulting dictionary is compatible with ``PatientRecord`` in the legacy
    generator and can also be consumed by the lifecycle ``Patient`` model.
    """

    faker = faker or fake
    demographics = generate_patient_demographics(
        age_dist,
        gender_dist,
        race_dist,
        smoking_dist,
        alcohol_dist,
        education_dist,
        employment_dist,
        housing_dist,
    )

    gender_value = str(demographics["gender"]).lower()
    if gender_value.startswith("m"):
        gender = "male"
        first_name = faker.first_name_male()
        middle_initial = faker.first_name_male()[0].upper()
    else:
        gender = "female"
        first_name = faker.first_name_female()
        middle_initial = faker.first_name_female()[0].upper()

    profile = {
        "first_name": first_name,
        "last_name": faker.last_name(),
        "middle_name": middle_initial,
        "gender": gender,
        "birthdate": demographics["birthdate"],
        "age": demographics["age"],
        "race": demographics["race"],
        "ethnicity": random.choice(ETHNICITIES),
        "address": faker.street_address(),
        "city": faker.city(),
        "state": faker.state_abbr(),
        "zip": faker.zipcode(),
        "country": "US",
        "phone": faker.phone_number(),
        "email": faker.email(),
        "marital_status": random.choice(MARITAL_STATUSES),
        "language": random.choice(LANGUAGES),
        "insurance": random.choice(INSURANCES),
        "ssn": faker.ssn(),
        "smoking_status": demographics["smoking_status"],
        "alcohol_use": demographics["alcohol_use"],
        "education": demographics["education"],
        "employment_status": demographics["employment_status"],
        "income": demographics["income"],
        "housing_status": demographics["housing_status"],
    }

    return profile


def generate_patient_profile_for_index(
    _: int,
    *,
    age_dist,
    gender_dist,
    race_dist,
    smoking_dist,
    alcohol_dist,
    education_dist,
    employment_dist,
    housing_dist,
    faker: Faker | None = None,
) -> Dict[str, Any]:
    """Executor-friendly wrapper that delegates to ``generate_patient_profile``."""

    return generate_patient_profile(
        age_dist,
        gender_dist,
        race_dist,
        smoking_dist,
        alcohol_dist,
        education_dist,
        employment_dist,
        housing_dist,
        faker=faker,
    )


def build_patient_record(profile: Dict[str, Any]) -> LifecyclePatient:
    """Create a lifecycle ``Patient`` instance from a generated profile."""

    birthdate = profile.get("birthdate")
    if isinstance(birthdate, str):
        birth_date = datetime.fromisoformat(birthdate).date()
    elif isinstance(birthdate, datetime):
        birth_date = birthdate.date()
    elif isinstance(birthdate, date):
        birth_date = birthdate
    else:
        birth_date = datetime.utcnow().date()

    patient = LifecyclePatient(
        patient_id=str(uuid.uuid4()),
        first_name=profile.get("first_name", ""),
        last_name=profile.get("last_name", ""),
        middle_name=profile.get("middle_name"),
        birth_date=birth_date,
        gender=profile.get("gender", ""),
        race=profile.get("race", ""),
        ethnicity=profile.get("ethnicity", ""),
        language=profile.get("language"),
        marital_status=profile.get("marital_status"),
        contact={
            "phone": profile.get("phone"),
            "email": profile.get("email"),
            "insurance": profile.get("insurance"),
        },
        address={
            "line": profile.get("address"),
            "city": profile.get("city"),
            "state": profile.get("state"),
            "postal_code": profile.get("zip"),
            "country": profile.get("country"),
        },
        identifiers={
            key: profile[key]
            for key in ("mrn", "vista_id", "ssn")
            if profile.get(key)
        },
        sdoh={
            "smoking_status": profile.get("smoking_status"),
            "alcohol_use": profile.get("alcohol_use"),
            "education": profile.get("education"),
            "employment_status": profile.get("employment_status"),
            "income": profile.get("income"),
            "housing_status": profile.get("housing_status"),
        },
    )
    return patient


__all__ = [
    "generate_patient_demographics",
    "generate_patient_profile",
    "generate_patient_profile_for_index",
    "build_patient_record",
]
