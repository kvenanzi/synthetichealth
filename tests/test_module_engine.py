from __future__ import annotations

import random
import sys
from pathlib import Path
import textwrap

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core.lifecycle.modules import ModuleEngine, ModuleValidationError


def run_module(
    module_name: str,
    patient: dict,
    seed: int = 1,
    *,
    modules_root: Path = Path("modules"),
):
    random.seed(seed)
    engine = ModuleEngine([module_name], modules_root=modules_root)
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


def test_asthma_v2_module_generates_events():
    patient = {
        "patient_id": "asthma-1",
        "birthdate": "1988-04-12",
        "age": 36,
        "gender": "female",
        "race": "White",
    }
    result = run_module("asthma_v2", patient, seed=2)

    assert any(cond["icd10_code"] == "J45.40" for cond in result.conditions)
    assert any(plan["name"] == "Asthma Action Plan" for plan in result.care_plans)
    assert any(enc["type"] == "Asthma Intake Visit" for enc in result.encounters)
    assert any(med["name"] == "Budesonide/Formoterol" for med in result.medications)
    assert any(obs["loinc_code"] == "2019-8" for obs in result.observations)


def test_copd_v2_module_generates_events():
    patient = {
        "patient_id": "copd-2",
        "birthdate": "1955-11-03",
        "age": 69,
        "gender": "male",
        "race": "Black",
    }
    result = run_module("copd_v2", patient, seed=3)

    assert any(cond["icd10_code"] == "J44.9" for cond in result.conditions)
    assert any(enc["type"] == "COPD Baseline Assessment" for enc in result.encounters)
    assert any(med["name"] == "Tiotropium" for med in result.medications)
    assert any(obs["loinc_code"] == "19926-5" for obs in result.observations)


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
    # Gestational diabetes branch occurs probabilistically; ensure pathway executes when present.
    medication_names = {med["name"] for med in result.medications}
    if "Gestational Diabetes" in condition_names:
        assert "Insulin NPH" in medication_names
        assert any(proc["code"] == "82950" for proc in result.procedures)
    else:
        assert "Insulin NPH" not in medication_names


def test_type2_diabetes_module_invokes_titration_submodule():
    patient = {
        "patient_id": "dm-1",
        "birthdate": "1975-02-20",
        "age": 49,
        "gender": "female",
        "race": "Asian",
    }
    result = run_module("type2_diabetes_management", patient, seed=4)

    medication_names = {med["name"] for med in result.medications}
    assert {"Empagliflozin", "Semaglutide"}.intersection(medication_names)

    encounter_types = {enc["type"] for enc in result.encounters}
    assert "Endocrinology Follow-up" in encounter_types

    loincs = {obs.get("loinc_code") for obs in result.observations}
    assert "4548-4" in loincs


def test_hyperlipidemia_module_generates_followups():
    patient = {
        "patient_id": "lipid-1",
        "birthdate": "1972-09-12",
        "age": 52,
        "gender": "male",
        "race": "White",
    }
    result = run_module("hyperlipidemia_management", patient, seed=3)

    assert any(cond["icd10_code"] == "E78.2" for cond in result.conditions)
    assert any(enc["type"] == "Lipid Follow-up" for enc in result.encounters)
    assert any(med["name"] in {"Atorvastatin", "Rosuvastatin"} for med in result.medications)
    assert any(obs["loinc_code"] == "2089-1" for obs in result.observations)


def test_heart_failure_module_generates_gdmt():
    patient = {
        "patient_id": "hf-1",
        "birthdate": "1968-04-22",
        "age": 56,
        "gender": "male",
        "race": "Black",
    }
    result = run_module("heart_failure_management", patient, seed=5)

    assert any(cond["icd10_code"] == "I50.2" for cond in result.conditions)
    assert any(enc["type"] == "HF Follow-up" for enc in result.encounters)
    assert any(med["name"] in {"Lisinopril", "Sacubitril/Valsartan", "Carvedilol"} for med in result.medications)
    assert any(obs["loinc_code"] == "33914-3" for obs in result.observations)


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


def test_call_submodule_merges_outputs_and_attributes(tmp_path):
    modules_root = tmp_path
    submodule_content = textwrap.dedent(
        """
        name: test_submodule
        description: Submodule that adds a condition
        categories:
          conditions: replace
        states:
          start:
            type: start
            transitions:
              - to: sub_encounter
          sub_encounter:
            type: encounter
            encounter_type: "Submodule Visit"
            transitions:
              - to: onset
          onset:
            type: condition_onset
            assign_to_attribute: sub_condition_id
            conditions:
              - name: "Test Condition"
                icd10: "A00"
            transitions:
              - to: end
          end:
            type: terminal
        """
    )
    (modules_root / "test_submodule.yaml").write_text(submodule_content)

    parent_content = textwrap.dedent(
        """
        name: base_module
        description: Calls a submodule and resolves the resulting condition
        categories: {}
        states:
          start:
            type: start
            transitions:
              - to: invoke_submodule
          invoke_submodule:
            type: call_submodule
            module: test_submodule
            transitions:
              - to: resolve_condition
          resolve_condition:
            type: condition_end
            referenced_by_attribute: sub_condition_id
            status: resolved
            transitions:
              - to: followup_encounter
          followup_encounter:
            type: encounter
            encounter_type: "Follow Up"
            transitions:
              - to: end
          end:
            type: terminal
        """
    )
    (modules_root / "base_module.yaml").write_text(parent_content)

    patient = {
        "patient_id": "sub-1",
        "birthdate": "1990-01-01",
        "age": 34,
        "gender": "female",
        "race": "White",
    }

    engine = ModuleEngine(["base_module"], modules_root=modules_root)
    result = engine.execute(patient)

    encounter_types = {enc["type"] for enc in result.encounters}
    assert "Submodule Visit" in encounter_types
    assert "Follow Up" in encounter_types

    assert result.conditions, "submodule should create a condition"
    condition = result.conditions[0]
    assert condition["icd10_code"] == "A00"
    assert condition["status"] == "resolved"
    assert condition["end_date"] is not None

    assert "conditions" in result.replacements


def test_call_submodule_requires_module_reference(tmp_path):
    invalid_content = textwrap.dedent(
        """
        name: invalid_submodule_call
        description: Missing module reference
        categories: {}
        states:
          start:
            type: start
            transitions:
              - to: missing_reference
          missing_reference:
            type: call_submodule
            transitions:
              - to: end
          end:
            type: terminal
        """
    )
    (tmp_path / "invalid_submodule_call.yaml").write_text(invalid_content)

    with pytest.raises(ModuleValidationError):
        ModuleEngine(["invalid_submodule_call"], modules_root=tmp_path)


def test_call_submodule_prevents_recursive_execution(tmp_path):
    recursive_content = textwrap.dedent(
        """
        name: recursive_module
        description: Calls itself recursively
        categories: {}
        states:
          start:
            type: start
            transitions:
              - to: recurse
          recurse:
            type: call_submodule
            module: recursive_module
            transitions:
              - to: final_encounter
          final_encounter:
            type: encounter
            encounter_type: "Final Visit"
            transitions:
              - to: end
          end:
            type: terminal
        """
    )
    (tmp_path / "recursive_module.yaml").write_text(recursive_content)

    patient = {
        "patient_id": "cycle-1",
        "birthdate": "1985-02-01",
        "age": 39,
        "gender": "male",
        "race": "Asian",
    }

    engine = ModuleEngine(["recursive_module"], modules_root=tmp_path)
    result = engine.execute(patient)

    encounter_types = [enc["type"] for enc in result.encounters]
    assert encounter_types == ["Final Visit"]

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


def test_adult_primary_care_module_covers_preventive_services():
    patient = {
        "patient_id": "well-1",
        "birthdate": "1987-07-22",
        "age": 37,
        "gender": "female",
        "race": "Asian",
    }
    result = run_module("adult_primary_care_wellness", patient, seed=3)

    condition_codes = {cond["icd10_code"] for cond in result.conditions}
    assert {"Z00.00", "E78.2"}.issubset(condition_codes)

    observation_codes = {obs.get("loinc_code") for obs in result.observations}
    assert {"13457-7", "2093-3", "39156-5"}.issubset(observation_codes)

    immunization_codes = {imm["cvx_code"] for imm in result.immunizations}
    assert {"115", "140"}.issubset(immunization_codes)

    procedure_codes = {proc["code"] for proc in result.procedures}
    assert {"45378", "77067"}.issubset(procedure_codes)

    medication_names = {med["name"] for med in result.medications}
    assert "Atorvastatin" in medication_names


def test_module_engine_handles_v2_states(tmp_path: Path):
    module_yaml = """
name: test_v2_module
description: Test module covering v2 features
categories: {}
states:
  start:
    type: start
    transitions:
      - to: encounter_state
  encounter_state:
    type: encounter
    encounter_type: "Pulmonology Visit"
    transitions:
      - to: condition_onset_state
  condition_onset_state:
    type: condition_onset
    assign_to_attribute: asthma_condition_attr
    attach_to_last_encounter: true
    conditions:
      - name: "Test Asthma"
        icd10: "J45.909"
        snomed: "195967001"
        category: "respiratory"
    transitions:
      - to: set_flag_state
  set_flag_state:
    type: set_attribute
    attribute: risk_level
    value: high
    transitions:
      - to: decision_state
  decision_state:
    type: decision
    transitions:
      - to: resolve_state
        condition:
          condition_type: Attribute
          attribute: risk_level
          operator: ==
          value: high
      - to: terminal_state
        probability: 1.0
  resolve_state:
    type: condition_end
    referenced_by_attribute: asthma_condition_attr
    transitions:
      - to: medication_state
  medication_state:
    type: medication_start
    assign_to_attribute: controller_rx
    medications:
      - name: "Controller Inhaler"
        rxnorm: "859038"
        therapy_category: controller
    transitions:
      - to: medication_end_state
  medication_end_state:
    type: medication_end
    referenced_by_attribute: controller_rx
    transitions:
      - to: symptom_state
  symptom_state:
    type: symptom
    symptom: Wheezing
    units: "score"
    range:
      low: 10
      high: 20
    transitions:
      - to: encounter_end_state
  encounter_end_state:
    type: encounter_end
    transitions:
      - to: end
  terminal_state:
    type: terminal
  end:
    type: terminal
"""
    module_path = tmp_path / "test_v2_module.yaml"
    module_path.write_text(module_yaml, encoding="utf-8")

    patient = {
        "patient_id": "v2-1",
        "birthdate": "1985-05-05",
        "age": 39,
        "gender": "female",
        "race": "Asian",
    }

    result = run_module("test_v2_module", patient, seed=3, modules_root=tmp_path)

    condition = result.conditions[0]
    assert condition["status"] == "resolved"
    assert condition["end_date"] is not None

    medication = result.medications[0]
    assert medication["end_date"] is not None

    observation_names = {obs["type"] for obs in result.observations}
    assert "Wheezing" in observation_names

    encounters = result.encounters
    assert encounters[0].get("end_date") is not None
