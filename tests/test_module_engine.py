from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core.lifecycle.modules import ModuleEngine, ModuleValidationError


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


def test_pediatric_module_covers_immunizations_and_procedures():
    random.seed(1)
    engine = ModuleEngine(["pediatric_asthma_management"], modules_root=Path("modules"))
    patient = {
        "patient_id": "child-1",
        "birthdate": "2010-03-15",
        "age": 13,
        "gender": "female",
        "race": "Black",
    }
    result = engine.execute(patient)

    assert result.immunizations, "module should track immunizations"
    assert any(immun["cvx_code"] == "140" for immun in result.immunizations)

    assert result.procedures, "exacerbation branch should emit nebulizer procedure"
    assert any(proc["code"] == "94640" for proc in result.procedures)

    assert result.care_plans, "module should add asthma action plan"
    assert any(plan["name"] == "Asthma Action Plan" for plan in result.care_plans)


def test_prenatal_module_handles_risk_branching():
    random.seed(1)
    engine = ModuleEngine(["prenatal_care_management"], modules_root=Path("modules"))
    patient = {
        "patient_id": "prenatal-1",
        "birthdate": "1995-08-01",
        "age": 29,
        "gender": "female",
        "race": "Hispanic",
    }
    result = engine.execute(patient)

    condition_names = {cond["name"] for cond in result.conditions}
    assert "Normal Pregnancy" in condition_names
    assert "Gestational Diabetes" in condition_names

    medication_names = {med["name"] for med in result.medications}
    assert "Insulin NPH" in medication_names

    assert any(proc["code"] == "82950" for proc in result.procedures)


def test_module_validation_rejects_invalid_decisions(tmp_path):
    invalid_module = tmp_path / "invalid_module.yaml"
    invalid_module.write_text(
        """
name: invalid_module
description: Invalid decision probabilities
categories: {}
states:
  start:
    type: start
    transitions:
      - to: decision_state
  decision_state:
    type: decision
    branches:
      - to: end
        probability: 0.8
  end:
    type: terminal
"""
    )

    with pytest.raises(ModuleValidationError):
        ModuleEngine(["invalid_module"], modules_root=tmp_path)
