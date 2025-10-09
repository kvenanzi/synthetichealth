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


def run_module(module_name: str, patient: dict, seed: int = 1):
    random.seed(seed)
    engine = ModuleEngine([module_name], modules_root=Path("modules"))
    return engine.execute(patient)


def test_module_engine_generates_structured_events():
    patient = {
        "patient_id": "test-patient",
        "birthdate": "1970-01-01",
        "age": 54,
        "gender": "male",
        "race": "White",
    }
    result = run_module("cardiometabolic_intensive", patient, seed=0)

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
    patient = {
        "patient_id": "child-1",
        "birthdate": "2010-03-15",
        "age": 13,
        "gender": "female",
        "race": "Black",
    }
    result = run_module("pediatric_asthma_management", patient, seed=1)

    assert result.immunizations, "module should track immunizations"
    assert any(immun["cvx_code"] == "140" for immun in result.immunizations)

    assert result.procedures, "exacerbation branch should emit nebulizer procedure"
    assert any(proc["code"] == "94640" for proc in result.procedures)

    assert result.care_plans, "module should add asthma action plan"
    assert any(plan["name"] == "Asthma Action Plan" for plan in result.care_plans)


def test_prenatal_module_handles_risk_branching():
    patient = {
        "patient_id": "prenatal-1",
        "birthdate": "1995-08-01",
        "age": 29,
        "gender": "female",
        "race": "Hispanic",
    }
    result = run_module("prenatal_care_management", patient, seed=1)

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


def test_oncology_survivorship_module_generates_surveillance_plan():
    patient = {
        "patient_id": "onc-1",
        "birthdate": "1978-06-01",
        "age": 46,
        "gender": "female",
        "race": "White",
    }
    result = run_module("oncology_survivorship", patient, seed=1)

    condition_names = {cond["name"] for cond in result.conditions}
    assert {"History of Breast Cancer", "Endocrine Therapy Monitoring"}.issubset(condition_names)

    medication_names = {med["name"] for med in result.medications}
    assert {"Tamoxifen", "Letrozole"}.issubset(medication_names)

    assert any(plan["name"] == "Breast Cancer Survivorship Plan" for plan in result.care_plans)
    assert any(proc["code"] == "78815" for proc in result.procedures)


def test_ckd_module_creates_dialysis_access_procedure():
    patient = {
        "patient_id": "ckd-1",
        "birthdate": "1965-02-11",
        "age": 59,
        "gender": "male",
        "race": "Black",
    }
    result = run_module("ckd_dialysis_planning", patient, seed=1)

    assert any(cond["icd10_code"] == "N18.4" for cond in result.conditions)
    assert any(proc["code"] == "36821" for proc in result.procedures)
    assert any(obs["loinc_code"] == "33914-3" for obs in result.observations)


def test_copd_module_adds_immunizations_and_rescue_medications():
    patient = {
        "patient_id": "copd-1",
        "birthdate": "1956-09-20",
        "age": 68,
        "gender": "male",
        "race": "White",
    }
    result = run_module("copd_home_oxygen", patient, seed=1)

    condition_names = {cond["name"] for cond in result.conditions}
    assert "Severe COPD" in condition_names

    immunization_codes = {imm["cvx_code"] for imm in result.immunizations}
    assert {"140", "33"}.issubset(immunization_codes)

    medication_names = {med["name"] for med in result.medications}
    assert {"Fluticasone/Salmeterol", "Tiotropium"}.issubset(medication_names)


def test_mental_health_module_captures_care_plan_and_procedure():
    patient = {
        "patient_id": "mh-1",
        "birthdate": "1990-04-04",
        "age": 34,
        "gender": "female",
        "race": "Hispanic",
    }
    result = run_module("mental_health_integrated_care", patient, seed=1)

    assert any(plan["name"] == "Collaborative Care Plan" for plan in result.care_plans)
    assert any(obs["loinc_code"] == "44261-6" for obs in result.observations)
    assert any(proc["code"] == "99492" for proc in result.procedures)


def test_geriatric_module_models_polypharmacy():
    patient = {
        "patient_id": "ger-1",
        "birthdate": "1942-11-15",
        "age": 82,
        "gender": "female",
        "race": "White",
    }
    result = run_module("geriatric_polypharmacy", patient, seed=1)

    condition_codes = {cond["icd10_code"] for cond in result.conditions}
    assert {"I50.32", "N18.30", "M17.11"}.issubset(condition_codes)

    medication_names = {med["name"] for med in result.medications}
    assert {"Furosemide", "Metoprolol"}.issubset(medication_names)

    observation_codes = {obs["loinc_code"] for obs in result.observations}
    assert {"718-7", "2160-0", "10998-3"}.issubset(observation_codes)

    procedure_codes = {proc["code"] for proc in result.procedures}
    assert "73502" in procedure_codes


def test_sepsis_module_covers_follow_up_paths():
    patient = {
        "patient_id": "sep-1",
        "birthdate": "1980-05-20",
        "age": 44,
        "gender": "male",
        "race": "Black",
    }
    result = run_module("sepsis_survivorship", patient, seed=1)

    condition_codes = {cond["icd10_code"] for cond in result.conditions}
    assert "A41.9" in condition_codes

    observation_codes = {obs["loinc_code"] for obs in result.observations}
    assert {"6690-2", "1975-2", "8302-2"}.issubset(observation_codes)

    encounter_types = {enc["type"] for enc in result.encounters}
    assert {"Telehealth", "Post-Sepsis Clinic"} & encounter_types

    # ED branch is probabilistic; ensure lactate observation exists regardless
    assert "1975-2" in observation_codes


def test_pregnancy_loss_support_module_generates_bereavement_path():
    patient = {
        "patient_id": "loss-1",
        "birthdate": "1992-02-12",
        "age": 32,
        "gender": "female",
        "race": "Hispanic",
    }
    result = run_module("pregnancy_loss_support", patient, seed=2)

    condition_codes = {cond["icd10_code"] for cond in result.conditions}
    assert {"O03.9", "F43.21"}.issubset(condition_codes)

    medication_names = {med["name"] for med in result.medications}
    assert {"Ibuprofen", "Docusate Sodium"}.issubset(medication_names)

    care_plan_names = {plan["name"] for plan in result.care_plans}
    assert "Bereavement Support Plan" in care_plan_names

    observation_codes = {obs.get("loinc_code") for obs in result.observations}
    assert {"718-7", "44249-1"}.intersection(observation_codes)


def test_hiv_prep_module_supports_both_cohorts():
    patient = {
        "patient_id": "hiv-1",
        "birthdate": "1992-03-10",
        "age": 32,
        "gender": "male",
        "race": "Hispanic",
    }
    result = run_module("hiv_prep_management", patient, seed=1)

    condition_codes = {cond.get("icd10_code") for cond in result.conditions}
    assert ("B20" in condition_codes) or ("Z20.6" in condition_codes)

    medication_names = {med["name"] for med in result.medications}
    assert {"Bictegravir/Emtricitabine/Tenofovir", "Emtricitabine/Tenofovir"} & medication_names

    observation_codes = {obs["loinc_code"] for obs in result.observations}
    assert "25836-8" in observation_codes
