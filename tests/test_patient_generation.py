import random
from datetime import date

from faker import Faker

from src.core.lifecycle.generation.patient import (
    build_patient_record,
    generate_patient_demographics,
    generate_patient_profile,
)
from src.core.lifecycle.records import PatientRecord


def seed(seed_value: int = 2024) -> None:
    random.seed(seed_value)
    Faker.seed(seed_value)


def uniform_distribution(labels):
    weight = 1 / len(labels)
    return {label: weight for label in labels}


def test_generate_patient_demographics_age_and_bins():
    seed()
    demographics = generate_patient_demographics(
        {"30-39": 1.0},
        {"female": 1.0},
        {"White": 1.0},
        {"Never": 1.0},
        {"Low": 1.0},
        {"Graduate": 1.0},
        {"Employed": 1.0},
        {"Stable": 1.0},
    )

    assert 30 <= demographics["age"] <= 39
    assert demographics["birthdate"].year == date.today().year - demographics["age"]
    assert demographics["education"] == "Graduate"
    assert demographics["employment_status"] == "Employed"


def test_generate_patient_profile_includes_contact_fields():
    seed(77)
    faker = Faker()
    profile = generate_patient_profile(
        {"40-49": 1.0},
        {"male": 1.0},
        {"Asian": 1.0},
        uniform_distribution(["Never", "Former"]),
        {"Moderate": 1.0},
        {"College": 1.0},
        {"Employed": 1.0},
        {"Own": 1.0},
        faker=faker,
    )

    assert profile["gender"] == "male"
    assert profile["race"] == "Asian"
    assert profile["employment_status"] in {"Employed", "Student"}
    assert profile["phone"]
    assert profile["email"]


def test_build_patient_record_round_trips_profile():
    seed(101)
    faker = Faker()
    profile = generate_patient_profile(
        {"20-29": 1.0},
        {"female": 1.0},
        {"Black": 1.0},
        {"Never": 1.0},
        {"None": 1.0},
        {"College": 1.0},
        {"Student": 1.0},
        {"Rent": 1.0},
        faker=faker,
    )
    profile["mrn"] = "MRN12345"
    lifecycle_patient = build_patient_record(profile)

    assert lifecycle_patient.gender == "female"
    assert lifecycle_patient.identifiers["mrn"] == "MRN12345"
    assert lifecycle_patient.sdoh["employment_status"] in {"Student", "Student"}
    assert lifecycle_patient.birth_date.isoformat() == profile["birthdate"].isoformat()


def test_patient_record_metadata_defaults():
    patient = PatientRecord()

    assert patient.metadata["source_system"] == "synthetic"
    assert patient.metadata["generation_status"] == "pending"
    assert "migration_status" not in patient.metadata
