import importlib
import re
import sys
from pathlib import Path

tests_dir = Path(__file__).resolve().parent
repo_root = tests_dir.parent
sys.path.insert(0, str(repo_root))

records_module = importlib.import_module("src.core.lifecycle.records")
generator_module = importlib.import_module("src.core.synthetic_patient_generator")

PatientRecord = records_module.PatientRecord
VistaFormatter = generator_module.VistaFormatter


def _build_patient() -> PatientRecord:
    patient = PatientRecord(
        first_name="Alice",
        last_name="Smith",
        gender="female",
        birthdate="1980-05-17",
        ssn="123-45-6789",
        address="123 Main St",
        city="Boston",
        state="MA",
        zip="02118",
        phone="555-0101",
        marital_status="Married",
        race="White",
    )
    patient.vista_id = "1001"
    return patient


def test_fileman_internal_generates_numeric_pointers(tmp_path):
    patient = _build_patient()
    patient.smoking_status = "Current"
    patient.alcohol_use = "Heavy"
    patient.metadata["sdoh_risk_factors"] = ["Housing instability"]
    patient.metadata["phq9_score"] = 15
    encounter = {
        "patient_id": patient.patient_id,
        "encounter_id": "enc-1",
        "date": "2023-11-29",
        "type": "Wellness Visit",
        "location": "Primary Care Clinic",
    }
    condition = {
        "patient_id": patient.patient_id,
        "condition_id": "cond-1",
        "name": "Hypertension",
        "status": "active",
        "onset_date": "2023-10-01",
    }
    medication = {
        "patient_id": patient.patient_id,
        "medication_id": "med-1",
        "encounter_id": "enc-1",
        "name": "Lisinopril",
        "indication": "Hypertension",
        "start_date": "2023-11-29",
        "rxnorm_code": "617314",
        "dose": 10,
        "dose_unit": "mg",
        "frequency": "daily",
    }
    observation = {
        "patient_id": patient.patient_id,
        "observation_id": "obs-1",
        "encounter_id": "enc-1",
        "type": "Hemoglobin_A1c",
        "loinc_code": "4548-4",
        "value": "6.4",
        "units": "%",
        "status": "abnormal",
        "date": "2023-11-29",
        "panel": "Diabetes_Monitoring",
    }
    allergy = {
        "patient_id": patient.patient_id,
        "allergy_id": "allergy-1",
        "substance": "Peanuts",
        "reaction": "Anaphylaxis",
        "reaction_code": "39579001",
        "reaction_system": "http://snomed.info/sct",
        "severity": "severe",
        "severity_code": "24484000",
        "severity_system": "http://snomed.info/sct",
        "rxnorm_code": "12345",
        "category": "food",
        "recorded_date": "2023-11-01",
    }
    procedure = {
        "patient_id": patient.patient_id,
        "procedure_id": "proc-1",
        "encounter_id": "enc-1",
        "name": "Cardiac Stress Test",
        "cpt_code": "93017",
        "date": "2023-11-29",
    }
    care_plan = {
        "care_plan_id": "cp-1",
        "patient_id": patient.patient_id,
        "condition": "Hypertension",
        "pathway_stage": "Lifestyle Coaching",
        "scheduled_date": "2023-11-15",
        "due_date": "2023-12-15",
        "status": "in-progress",
        "progress": 0.5,
        "notes": "Working on salt reduction.",
        "activities": [
            {"type": "observation", "name": "BP Check", "status": "pending", "planned": "2023-12-10"}
        ],
        "linked_encounters": ["enc-1"],
    }

    output_file = tmp_path / "vista_globals.mumps"
    stats = VistaFormatter.export_vista_globals(
        [patient],
        [encounter],
        [condition],
        [procedure],
        [medication],
        [observation],
        [allergy],
        [],
        [],
        [care_plan],
        [],
        str(output_file),
        export_mode=VistaFormatter.FILEMAN_INTERNAL_MODE,
    )

    assert stats["patient_records"] == 1
    assert stats["visit_records"] == 1
    assert stats["problem_records"] == 1
    assert stats["medication_records"] == 1
    assert stats["lab_records"] == 1
    assert stats["allergy_records"] == 1
    assert stats["procedure_records"] == 1
    assert stats["care_plan_records"] == 1
    assert stats["measurement_records"] >= 1
    assert stats["health_factor_records"] >= 1

    content = output_file.read_text().splitlines()
    header_line = next(line for line in content if line.startswith("S ^DPT(0)="))
    assert re.search(r"\^DPT\(0\)=\"PATIENT\^2\^1001", header_line)

    address_line = next(line for line in content if line.startswith("S ^DPT(1001,.11)="))
    # State field should be encoded as numeric pointer (Massachusetts=22)
    assert "^22^" in address_line

    visit_pointer_line = next(line for line in content if re.match(r"S \^AUPNVSIT\(\d+,\.06\)=", line))
    assert re.match(r"S \^AUPNVSIT\(\d+,\.06\)=\d+$", visit_pointer_line)

    med_zero = next(line for line in content if re.match(r'S \^AUPNVMED\(\d+,0\)=', line))
    assert re.search(r'"1001\^\d+\^', med_zero)

    lab_zero = next(line for line in content if re.match(r'S \^AUPNVLAB\(\d+,0\)=', line))
    assert re.search(r'"1001\^\d+\^', lab_zero)
    lab_dict_line = next(line for line in content if re.match(r'S \^LAB\(60,\d+,0\)=', line))
    assert "^4548-4^%" in lab_dict_line

    allergy_zero = next(line for line in content if re.match(r'S \^GMR\(120\.8,\d+,0\)=', line))
    assert re.search(r'"1001\^\d+\^\^o\^', allergy_zero)
    reaction_line = next(line for line in content if re.match(r'S \^GMR\(120\.8,\d+,1\)=', line))
    assert "39579001" in reaction_line
    severity_line = next(line for line in content if re.match(r'S \^GMR\(120\.8,\d+,3\)=', line))
    assert "24484000" in severity_line

    allergen_dict_line = next(line for line in content if re.match(r'S \^GMR\(120\.82,\d+,0\)=', line))
    assert allergen_dict_line.count("^") >= 5
    assert "PEANUTS" in allergen_dict_line.upper()
    assert "12345" in allergen_dict_line

    drug_pointer = next(line for line in content if re.match(r'S \^PSDRUG\(\d+,0\)=', line))
    assert 'LISINOPRIL' in drug_pointer.upper() or '617314' in drug_pointer
    assert "10 mg" in drug_pointer.lower()
    assert "daily" in drug_pointer.lower()

    narrative_line = next(line for line in content if re.match(r"S \^AUPNPROB\(\d+,\.05\)=", line))
    assert re.match(r"S \^AUPNPROB\(\d+,\.05\)=\d+$", narrative_line)

    dob_index = next(line for line in content if line.startswith('S ^DPT("DOB"'))
    # FileMan date for 1980-05-17 -> years since 1700 = 280
    assert ",2800517," in dob_index

    procedure_zero = next(line for line in content if re.match(r'S \^AUPNVCPT\(\d+,0\)=', line))
    proc_match = re.search(r'"1001\^(\d+)\^(\d+)\^', procedure_zero)
    assert proc_match, "Procedure zero node does not contain expected patient/visit/CPT pointers"
    visit_pointer = proc_match.group(1)
    cpt_pointer = proc_match.group(2)
    assert visit_pointer.isdigit() and cpt_pointer.isdigit()
    assert any(
        re.match(fr'S \^AUPNVCPT\("C",{cpt_pointer},\d+\)=', line) for line in content
    ), "Missing CPT cross-reference for procedure"
    cpt_stub = next(
        line for line in content if re.match(fr'S \^ICPT\({cpt_pointer},0\)=', line)
    )
    assert "93017" in cpt_stub

    measurement_zero = next(line for line in content if re.match(r'S \^AUPNVMSR\(\d+,0\)=', line))
    assert re.search(r'"1001\^\d+\^', measurement_zero)

    health_factor_zero = next(line for line in content if re.match(r'S \^AUPNVHF\(\d+,0\)=', line))
    factor_match = re.search(r'"1001\^(\d+)\^', health_factor_zero)
    assert factor_match, "Health factor zero node missing patient/dictionary pointer"
    health_factor_dict = factor_match.group(1)
    assert health_factor_dict.isdigit()
    health_factor_stub = next(
        line for line in content if re.match(fr'S \^AUTTHF\({health_factor_dict},0\)=', line)
    )
    assert any(
        keyword in health_factor_stub.upper()
        for keyword in ["HOUSING", "SMOKER", "ALCOHOL", "PHQ", "SDOH"]
    ), "Health factor stub does not contain expected taxonomy keyword"

    tiu_zero = next(line for line in content if re.match(r'S \^TIU\(8925,\d+,0\)=', line))
    tiu_match = re.search(r'"1001\^[^\\^]*\^(\d+)\^', tiu_zero)
    assert tiu_match, "TIU zero node missing title pointer"
    tiu_title_ptr = tiu_match.group(1)
    title_stub = next(
        line for line in content if re.match(fr'S \^TIU\(8925\.1,{tiu_title_ptr},0\)=', line)
    )
    assert "CARE PLAN" in title_stub.upper()
    assert any(
        re.match(r'S \^TIU\(8925,\d+,"TEXT",\d+,0\)=', line) for line in content
    ), "TIU note missing TEXT multiple"
    tiu_title_stub = next(line for line in content if re.match(r'S \^TIU\(8925\.1,\d+,0\)=', line))
    assert "CARE PLAN" in tiu_title_stub.upper()


def test_legacy_mode_preserves_string_fields(tmp_path):
    patient = _build_patient()
    encounter = {
        "patient_id": patient.patient_id,
        "encounter_id": "enc-legacy",
        "date": "2021-01-05",
        "type": "Lab",
        "location": "City Lab",
    }
    condition = {
        "patient_id": patient.patient_id,
        "condition_id": "cond-legacy",
        "name": "Diabetes",
        "status": "active",
        "onset_date": "2020-12-01",
    }

    output_file = tmp_path / "vista_legacy.mumps"
    VistaFormatter.export_vista_globals(
        [patient],
        [encounter],
        [condition],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        str(output_file),
        export_mode=VistaFormatter.LEGACY_MODE,
    )

    content = output_file.read_text()
    # Legacy mode keeps state abbreviation and ICD text values
    assert "^DPT(1001,.11)=\"123 Main St^Boston^MA^02118\"" in content
    assert '^AUPNPROB("ICD","' in content
