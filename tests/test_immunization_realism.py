import random
from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import patch

from faker import Faker

from src.core.lifecycle.generation import clinical


def seed_random(seed: int = 2025) -> None:
    random.seed(seed)
    Faker.seed(seed)


def build_patient(patient_id: str, age_years: int) -> dict:
    today = datetime.now().date()
    birthdate = today - timedelta(days=age_years * 365)
    return {
        "patient_id": patient_id,
        "birthdate": birthdate.isoformat(),
        "age": age_years,
        "gender": "female",
        "race": "White",
        "ethnicity": "Not Hispanic or Latino",
    }


def sample_encounters(patient_id: str, birthdate_iso: str) -> list:
    birthdate = datetime.fromisoformat(birthdate_iso).date()
    return [
        {
            "encounter_id": f"{patient_id}-well-{index}",
            "patient_id": patient_id,
            "date": (birthdate + delta).isoformat(),
            "time": "09:00",
            "type": "Preventive Care",
            "reason": "Well child visit",
            "provider": "Dr. Rivera",
            "location": "Pediatrics Clinic",
            "clinic_stop": "322",
            "service_category": "A",
            "related_conditions": "",
        }
        for index, delta in enumerate(
            [
                timedelta(days=60),
                timedelta(days=120),
                timedelta(days=365),
                timedelta(days=365 * 2),
            ],
            start=1,
        )
    ]


def test_generate_immunizations_childhood_schedule_has_metadata():
    seed_random(73)
    patient = build_patient("child-001", age_years=2)
    encounters = sample_encounters(patient["patient_id"], patient["birthdate"])

    immunizations, followups = clinical.generate_immunizations(
        patient,
        encounters,
        allergies=[],
        conditions=[],
    )

    assert immunizations, "Expected immunizations for a toddler patient"
    # Ensure at least one childhood series is present
    childhood_series = {
        series["series_id"]
        for series in clinical.IMMUNIZATION_SERIES_DEFINITIONS
        if series.get("series_type") == "childhood"
    }
    recorded_childhood = {record["series_id"] for record in immunizations if record.get("series_id")}
    assert recorded_childhood.intersection(childhood_series), "Missing childhood vaccine coverage"

    series_doses = defaultdict(set)
    for record in immunizations:
        series_id = record.get("series_id")
        dose_number = record.get("dose_number")
        series_total = record.get("series_total")
        assert record.get("cvx_code"), "Immunization should include a CVX code"
        assert record.get("status") == "completed"
        if series_id:
            assert 1 <= dose_number <= series_total
            assert dose_number not in series_doses[series_id], "Duplicate dose number within a series"
            series_doses[series_id].add(dose_number)

    # Follow-up observations may not always occur, but when present they must include immunization titers
    for observation in followups:
        assert observation.get("panel") == "Immunization_Titers"
        assert observation.get("loinc_code")
        assert observation.get("value")


def test_generate_immunizations_produces_titer_followup_when_probability_hit():
    patient = build_patient("hepB-001", age_years=1)
    encounters = sample_encounters(patient["patient_id"], patient["birthdate"])

    with patch("src.core.lifecycle.generation.clinical.random.random", lambda: 0.0):
        seed_random(11)
        immunizations, followups = clinical.generate_immunizations(
            patient,
            encounters,
            allergies=[],
            conditions=[],
        )

    assert any(record["series_id"] == "hepB_primary" for record in immunizations)
    assert followups, "Expected antibody titer follow-up when probability threshold is forced"
    for observation in followups:
        assert observation.get("panel") == "Immunization_Titers"
        assert observation.get("loinc_code")
        assert observation.get("status") in {"normal", "abnormal"}
