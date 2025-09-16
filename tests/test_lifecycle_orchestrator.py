from datetime import datetime

from src.core.lifecycle.orchestrator import LifecycleOrchestrator


def minimal_patient_dict():
    return {
        "patient_id": "123",
        "first_name": "Test",
        "last_name": "Patient",
        "birthdate": "1980-01-01",
        "gender": "male",
        "race": "White",
        "ethnicity": "Not Hispanic or Latino",
    }


def test_orchestrator_builds_patient_with_metadata():
    orchestrator = LifecycleOrchestrator(
        scenario_name="general",
        scenario_details={"description": "Balanced demographic distribution"},
    )

    patient = orchestrator.build_patient(
        minimal_patient_dict(),
        encounters=[],
        conditions=[],
        medications=[],
        immunizations=[],
        observations=[],
        allergies=[],
        procedures=[],
        metadata={"care_plan_total": 2},
    )

    assert patient.metadata["scenario"] == "general"
    assert patient.metadata["scenario_details"]["description"] == "Balanced demographic distribution"
    assert patient.care_plan.total == 2

