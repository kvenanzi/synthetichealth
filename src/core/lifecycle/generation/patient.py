"""Patient-level lifecycle generation helpers."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict

from faker import Faker

from ..models import Patient as LifecyclePatient

fake = Faker()


def generate_patient_demographics(
    age_dist,
    gender_dist,
    race_dist,
    smoking_dist,
    alcohol_dist,
    education_dist,
    employment_dist,
    housing_dist,
) -> Dict[str, object]:
    age_bin_label = sample_from_dist(age_dist)
    a_min, a_max = map(int, age_bin_label.split("-"))
    age = random.randint(a_min, a_max)
    birthdate = datetime.now().date() - timedelta(days=age * 365)

    return {
        "age": age,
        "birthdate": birthdate,
        "income": random.randint(0, 200000) if age >= 18 else 0,
        "gender": sample_from_dist(gender_dist),
        "race": sample_from_dist(race_dist),
        "smoking_status": sample_from_dist(smoking_dist),
        "alcohol_use": sample_from_dist(alcohol_dist),
        "education": sample_from_dist(education_dist) if age >= 18 else "None",
        "employment_status": sample_from_dist(employment_dist) if age >= 16 else "Student",
        "housing_status": sample_from_dist(housing_dist),
    }


def build_patient_record(demographics: Dict[str, object]) -> LifecyclePatient:
    patient = LifecyclePatient(
        patient_id=str(uuid.uuid4()),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        middle_name=fake.first_name()[:1],
        birth_date=demographics["birthdate"],
        gender=demographics["gender"],
        race=demographics["race"],
        ethnicity=random.choice(ETHNICITIES),
        language=random.choice(LANGUAGES),
        marital_status=random.choice(MARITAL_STATUSES),
        contact={"phone": fake.phone_number(), "email": fake.email(), "insurance": random.choice(INSURANCES)},
        address={
            "line": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "postal_code": fake.zipcode(),
            "country": "US",
        },
        identifiers={"mrn": f"MRN{random.randint(100000, 999999)}"},
        sdoh={
            "smoking_status": demographics["smoking_status"],
            "alcohol_use": demographics["alcohol_use"],
            "education": demographics["education"],
            "employment_status": demographics["employment_status"],
            "income": demographics["income"],
            "housing_status": demographics["housing_status"],
        },
    )
    return patient

