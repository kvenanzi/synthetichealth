import random
from collections import Counter
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
    patient = base_patient()
    patient["birthdate"] = "1990-01-01"
    patient_id = patient["patient_id"]
    conditions = [
        {
            "condition_id": "cond-dep",
            "patient_id": patient_id,
            "name": "Depression",
            "status": "active",
            "onset_date": "2024-01-01",
            "icd10_code": "F33.1",
            "snomed_code": "370143000",
            "condition_category": "behavioral_health",
        }
    ]
    encounters = [
        {
            "encounter_id": "enc-therapy",
            "patient_id": patient_id,
            "date": "2024-02-15",
            "time": "10:00",
            "type": "Behavioral Health Session",
            "reason": "Therapy follow-up",
            "provider": "Dr. Rowe",
            "location": "Behavioral Health - Downtown Clinic",
            "clinic_stop": "167",
            "service_category": "A",
            "related_conditions": "Depression",
        },
        {
            "encounter_id": "enc-follow",
            "patient_id": patient_id,
            "date": "2024-05-20",
            "time": "09:30",
            "type": "Telehealth Check-in",
            "reason": "Medication follow-up",
            "provider": "Dr. Rowe",
            "location": "Telehealth",
            "clinic_stop": "179",
            "service_category": "A",
            "related_conditions": "Depression",
        },
    ]
    medications = [
        {
            "medication_id": "med-ssri",
            "patient_id": patient_id,
            "encounter_id": "enc-therapy",
            "name": "Sertraline",
            "indication": "Depression",
            "therapy_category": "ssri",
            "therapeutic_class": "ssri",
            "start_date": "2024-02-15",
            "status": "active",
        }
    ]
    procedures = []
    observations = [
        {
            "observation_id": "obs-phq9",
            "patient_id": patient_id,
            "encounter_id": "enc-therapy",
            "type": "PHQ9_Score",
            "loinc_code": "44249-1",
            "value": "8",
            "value_numeric": 8,
            "units": "score",
            "reference_range": "0-4 score",
            "status": "final",
            "date": "2024-02-15",
            "panel": "Behavioral_Health_Assessments",
        }
    ]

    care_plans = clinical.generate_care_plans(
        patient,
        conditions,
        encounters,
        medications=medications,
        procedures=procedures,
        observations=observations,
    )

    assert care_plans, "Expected care plans to be generated"
    statuses = Counter(plan["status"] for plan in care_plans)
    summary = patient.get("care_plan_summary")
    assert summary is not None
    assert summary["total"] == len(care_plans)
    assert summary["completed"] == statuses.get("completed", 0)
    assert summary["overdue"] == statuses.get("overdue", 0)
    expected_scheduled = statuses.get("scheduled", 0) + statuses.get("in-progress", 0)
    assert summary["scheduled"] == expected_scheduled
    assert summary.get("in_progress", 0) == statuses.get("in-progress", 0)

    for plan in care_plans:
        assert plan["care_plan_id"], "Care plan should have an identifier"
        assert plan["status"] in {"completed", "scheduled", "overdue", "in-progress"}
        assert plan["scheduled_date"], "Care plan requires a scheduled date"
        assert plan["due_date"], "Care plan requires a due date"
        assert "activities" in plan
        if isinstance(plan["activities"], list):
            assert all(isinstance(activity, dict) for activity in plan["activities"])


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


def test_generate_death_incorporates_family_history_risk():
    seed_random(5)
    patient = base_patient()
    patient["age"] = 72
    patient["birthdate"] = "1951-01-01"
    family_history = [
        {
            "patient_id": patient["patient_id"],
            "condition": "Heart Disease",
            "condition_display": "Heart Disease",
            "risk_modifier": 0.2,
            "recorded_date": "2020-01-01",
        }
    ]
    conditions = [{"name": "Hypertension"}]

    with patch("src.core.lifecycle.generation.clinical.random.random", return_value=0.0), patch(
        "src.core.lifecycle.generation.clinical.random.uniform", return_value=0.0
    ), patch("src.core.lifecycle.generation.clinical.random.randint", return_value=1), patch(
        "src.core.lifecycle.generation.clinical.random.gauss", side_effect=lambda mean, _: mean
    ):
        death_record = clinical.generate_death(patient, conditions=conditions, family_history=family_history)

    assert death_record is not None
    assert death_record["risk_multiplier"] > 1.0


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


def test_generate_family_history_returns_entries_and_adjustments():
    seed_random(100)
    patient = base_patient()
    patient["age"] = 55
    def pick(options):
        if isinstance(options, (list, tuple)):
            return options[0]
        if isinstance(options, set):
            return next(iter(options))
        return options

    with patch("src.core.lifecycle.generation.clinical.random.random", return_value=0.0), patch(
        "src.core.lifecycle.generation.clinical.random.choice",
        side_effect=pick,
    ):
        entries, adjustments = clinical.generate_family_history(patient, min_fam=1, max_fam=1)

    assert entries, "Expected at least one family history entry"
    entry = entries[0]
    assert entry["patient_id"] == patient["patient_id"]
    assert entry.get("relation")
    assert entry.get("condition")
    assert adjustments, "Expected risk adjustments"
    assert any(value > 0 for value in adjustments.values())


def test_assign_conditions_respects_family_history_adjustments():
    seed_random(200)
    patient = base_patient()
    patient["family_history_adjustments"] = {"Heart Disease": 0.5}
    with patch("src.core.lifecycle.generation.clinical.random.random", return_value=0.0):
        assigned = clinical.assign_conditions(patient)

    assert "Heart Disease" in assigned
