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

    output_file = tmp_path / "vista_globals.mumps"
    stats = VistaFormatter.export_vista_globals(
        [patient],
        [encounter],
        [condition],
        [medication],
        [observation],
        [allergy],
        str(output_file),
        export_mode=VistaFormatter.FILEMAN_INTERNAL_MODE,
    )

    assert stats["patient_records"] == 1
    assert stats["visit_records"] == 1
    assert stats["problem_records"] == 1
    assert stats["medication_records"] == 1
    assert stats["lab_records"] == 1
    assert stats["allergy_records"] == 1

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

    narrative_line = next(line for line in content if re.match(r"S \^AUPNPROB\(\d+,\.05\)=", line))
    assert re.match(r"S \^AUPNPROB\(\d+,\.05\)=\d+$", narrative_line)

    dob_index = next(line for line in content if line.startswith('S ^DPT("DOB"'))
    # FileMan date for 1980-05-17 -> years since 1700 = 280
    assert ",2800517," in dob_index


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
        str(output_file),
        export_mode=VistaFormatter.LEGACY_MODE,
    )

    content = output_file.read_text()
    # Legacy mode keeps state abbreviation and ICD text values
    assert "^DPT(1001,.11)=\"123 Main St^Boston^MA^02118\"" in content
    assert '^AUPNPROB("ICD","' in content
