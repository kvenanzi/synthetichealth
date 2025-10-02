import random
from unittest.mock import patch

from faker import Faker

from src.core.lifecycle.generation import clinical


def seed_random(seed: int = 1337) -> None:
    random.seed(seed)
    Faker.seed(seed)


def base_patient() -> dict:
    return {
        "patient_id": "patient-1",
        "birthdate": "1950-01-01",
        "age": 74,
        "gender": "female",
        "race": "White",
        "ethnicity": "Not Hispanic or Latino",
        "smoking_status": "Current",
        "alcohol_use": "Heavy",
        "education": "Primary",
        "employment_status": "Unemployed",
        "income": 18000,
        "housing_status": "Homeless",
    }


def test_generate_conditions_and_care_plans_summary():
    seed_random()
    patient = base_patient()
    preassigned = clinical.assign_conditions(patient)
    encounters = clinical.generate_encounters(patient, preassigned_conditions=preassigned)

    conditions = clinical.generate_conditions(
        patient,
        encounters,
        min_cond=1,
        max_cond=2,
        preassigned_conditions=preassigned,
    )
    assert isinstance(conditions, list)
    if conditions:
        for condition in conditions:
            assert condition["condition_id"], "Condition should have an identifier"
            assert condition["status"] in clinical.CONDITION_STATUSES
            # Catalog lookups should populate ICD-10 codes where available
            assert "icd10_code" in condition
            assert "stage_detail" in condition
            assert "severity_detail" in condition
    else:
        # Even when no conditions are assigned the patient profile should be initialized.
        assert patient.get("condition_profile") == []

    care_plans = clinical.generate_care_plans(patient, conditions, encounters)
    assert isinstance(care_plans, list)
    summary = patient.get("care_plan_summary")
    assert summary is not None
    assert summary["total"] == len(care_plans)


def test_generate_medications_structure():
    seed_random(2024)
    patient = base_patient()
    preassigned = clinical.assign_conditions(patient)
    encounters = clinical.generate_encounters(patient, preassigned_conditions=preassigned)
    conditions = clinical.generate_conditions(
        patient,
        encounters,
        min_cond=1,
        max_cond=3,
        preassigned_conditions=preassigned,
    )

    medications = clinical.generate_medications(patient, encounters, conditions)
    assert isinstance(medications, list)
    for med in medications:
        assert med["patient_id"] == patient["patient_id"]
        assert med["therapy_category"]
        assert med["indication"]


def test_generate_observations_has_panel_information():
    seed_random(7)
    patient = base_patient()
    preassigned = clinical.assign_conditions(patient)
    encounters = clinical.generate_encounters(patient, preassigned_conditions=preassigned)
    conditions = clinical.generate_conditions(
        patient,
        encounters,
        min_cond=1,
        max_cond=2,
        preassigned_conditions=preassigned,
    )

    observations = clinical.generate_observations(patient, encounters, conditions, min_obs=2, max_obs=4)
    assert observations, "Expected observations to be generated"
    sample = observations[0]
    assert sample["patient_id"] == patient["patient_id"]
    assert "type" in sample and sample["type"]
    if "panel" in sample:
        assert sample["panel"]
    else:
        # Routine observations do not carry a panel but should reference an encounter when available
        encounter_ids = {enc["encounter_id"] for enc in encounters}
        if encounter_ids:
            assert sample.get("encounter_id") in encounter_ids


def test_generate_encounters_includes_stop_codes():
    seed_random(11)
    patient = base_patient()
    preassigned = clinical.assign_conditions(patient)
    encounters = clinical.generate_encounters(patient, preassigned_conditions=preassigned)

    assert encounters, "Expected at least one encounter"
    for encounter in encounters:
        assert "encounter_id" in encounter
        assert encounter["patient_id"] == patient["patient_id"]
        assert encounter.get("clinic_stop"), "Encounters should include clinic stop codes"
        assert encounter.get("service_category") in {"A", "E", "I"}
        assert encounter.get("encounter_class") in {"ambulatory", "emergency", "inpatient"}
        assert "duration_minutes" in encounter


def test_generate_death_with_forced_probability():
    seed_random(99)
    patient = base_patient()

    with patch("src.core.lifecycle.generation.clinical.random.random", return_value=0.0):
        death_record = clinical.generate_death(patient, conditions=None, family_history=None)

    assert death_record is not None
    assert death_record["patient_id"] == patient["patient_id"]
    assert death_record["primary_cause_code"]


def test_parse_distribution_accepts_mapping():
    distribution = {"a": 0.5, "b": 0.5}
    parsed = clinical.parse_distribution(distribution, ["a", "b"], default_dist=None)
    assert parsed == distribution


def test_generate_immunizations_schedule():
    seed_random(321)
    patient = base_patient()
    patient["birthdate"] = "2018-01-01"
    patient["age"] = 6
    preassigned = clinical.assign_conditions(patient)
    encounters = clinical.generate_encounters(patient, preassigned_conditions=preassigned)
    allergies = clinical.generate_allergies(patient)
    condition_payload = [
        {
            "name": name,
            "condition_category": clinical.CONDITION_CATALOG.get(name, {}).get("category"),
        }
        for name in preassigned
    ]

    immunizations, followups = clinical.generate_immunizations(
        patient,
        encounters,
        allergies=allergies,
        conditions=condition_payload,
    )

    assert immunizations, "Expected schedule-driven immunizations"
    assert all(record.get("cvx_code") for record in immunizations)
    assert len(followups) <= len(immunizations)
