from __future__ import annotations

import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core.lifecycle.modules import ModuleEngine


def test_module_engine_generates_structured_events():
    random.seed(0)
    engine = ModuleEngine(["cardiometabolic_intensive"], modules_root=Path("modules"))
    patient = {
        "patient_id": "test-patient",
        "birthdate": "1970-01-01",
        "age": 54,
        "gender": "male",
        "race": "White",
    }
    result = engine.execute(patient)

    assert "encounters" in result.replacements
    assert "conditions" in result.replacements
    assert "medications" in result.replacements

    assert result.encounters, "module should generate encounters"
    assert result.conditions, "module should generate conditions"
    assert result.medications, "module should generate medications"
    # Observations are augment, so no replacement but should contain entries
    assert result.observations, "module should generate observations"

    encounter = result.encounters[0]
    assert encounter["patient_id"] == "test-patient"
    assert encounter["type"]

    condition_names = {cond["name"] for cond in result.conditions}
    assert {"Diabetes", "Hypertension", "Hyperlipidemia"}.issubset(condition_names)

    medication_names = {med["name"] for med in result.medications}
    assert "Metformin" in medication_names
