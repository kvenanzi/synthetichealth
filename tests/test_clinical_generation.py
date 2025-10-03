import random
from collections import Counter
from datetime import datetime, timedelta
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


def find_condition_display(keyword: str) -> str:
    lowered = keyword.lower()
    for entry in clinical.CONDITION_CATALOG.values():
        display = entry.get("display", "")
        if lowered in display.lower():
            return entry["display"]
    raise AssertionError(f"Condition containing '{keyword}' not found in catalog")


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
            "condition_category": "mental_health",
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


def test_condition_assignment_has_breadth_and_severity_profiles():
    seed_random(314)
    today = datetime.now().date()
    unique_conditions = set()
    severity_or_stage_counter = 0

    for idx in range(60):
        patient = base_patient()
        patient["patient_id"] = f"patient-{idx}"
        age = random.randint(2, 90)
        patient["age"] = age
        patient["birthdate"] = (today - timedelta(days=age * 365)).isoformat()
        patient["gender"] = random.choice(["male", "female"])
        patient["sdoh_risk_score"] = random.uniform(0.0, 0.9)
        patient["genetic_risk_score"] = random.uniform(0.0, 2.0)

        assigned = clinical.assign_conditions(patient)
        condition_records = clinical.generate_conditions(
            patient,
            encounters=[],
            preassigned_conditions=assigned,
            min_cond=1,
            max_cond=6,
        )
        unique_conditions.update(
            record["name"] for record in condition_records if record.get("name")
        )
        if any(record.get("stage_detail") or record.get("severity_detail") for record in condition_records):
            severity_or_stage_counter += 1

    assert len(unique_conditions) >= 40, f"Expected >= 40 conditions, got {len(unique_conditions)}"
    assert severity_or_stage_counter > 0, "Expected at least one condition with stage or severity detail"


def test_encounter_volume_scales_with_condition_burden():
    seed_random(902)
    today = datetime.now().date()

    low_patient = base_patient()
    low_patient["patient_id"] = "patient-low"
    low_patient["age"] = 35
    low_patient["birthdate"] = (today - timedelta(days=35 * 365)).isoformat()
    low_patient["sdoh_risk_score"] = 0.1
    low_patient["genetic_risk_score"] = 0.3
    low_conditions = clinical.assign_conditions(low_patient)[:1]
    low_encounters = clinical.generate_encounters(
        low_patient,
        preassigned_conditions=low_conditions,
        max_enc=6,
    )

    seed_random(903)
    high_patient = base_patient()
    high_patient["patient_id"] = "patient-high"
    high_patient["age"] = 72
    high_patient["birthdate"] = (today - timedelta(days=72 * 365)).isoformat()
    high_patient["sdoh_risk_score"] = 0.85
    high_patient["genetic_risk_score"] = 2.1
    high_patient["transportation_access"] = "limited"
    high_conditions = [
        find_condition_display("heart failure"),
        find_condition_display("chronic kidney disease"),
        find_condition_display("copd"),
        find_condition_display("diabetes"),
        find_condition_display("hypertension"),
        find_condition_display("depression"),
    ]
    high_encounters = clinical.generate_encounters(
        high_patient,
        preassigned_conditions=high_conditions,
        max_enc=30,
    )

    assert len(high_encounters) >= len(low_encounters) + 5

    non_primary_departments = {
        enc.get("department")
        for enc in high_encounters
        if enc.get("department") not in {"Primary Care", "Preventive Medicine"}
    }
    assert "Behavioral Health" in non_primary_departments, "Behavioral health specialty visits expected"
    assert "Pulmonology" in non_primary_departments, "Pulmonology encounters expected for COPD"
    assert any(enc.get("related_conditions") for enc in high_encounters), "Related conditions should annotate encounters"


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
