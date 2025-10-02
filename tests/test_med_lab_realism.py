import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.terminology.loaders import load_medication_entries, load_lab_test_entries
from src.core.lifecycle.generation.clinical import (
    create_medication_record,
    determine_lab_panels,
)


def test_medication_loader_variety():
    entries = load_medication_entries()
    assert len(entries) >= 25
    classes = {entry.metadata.get("therapeutic_class") for entry in entries}
    assert "statin" in classes
    assert "anticoagulant" in classes


def test_lab_loader_contains_advanced_markers():
    lab_entries = load_lab_test_entries()
    names = {entry["name"] for entry in lab_entries}
    assert "High Sensitivity Troponin I" in names
    assert "Prothrombin Time" in names


def test_create_medication_record_enriches_metadata():
    patient = {"patient_id": "p1", "birthdate": "1980-01-01"}
    encounters = [{"encounter_id": "enc1", "date": "2023-05-01"}]
    condition = {"name": "Asthma"}
    record = create_medication_record(patient, condition, encounters, "Albuterol", "controller")
    assert record["route"] == "inhaled"
    assert record["therapeutic_class"]
    assert "Bronch" in record["therapeutic_class"].lower() or record["therapeutic_class"].lower() == "bronchodilator"
    assert record["monitoring_panels"]


def test_determine_lab_panels_reflects_medications():
    patient = {"age": 60}
    panels = determine_lab_panels(
        patient,
        conditions=[],
        medications=[{"therapeutic_class": "anticoagulant", "monitoring_panels": ["Coagulation_Panel"]}],
    )
    assert "Coagulation_Panel" in panels
