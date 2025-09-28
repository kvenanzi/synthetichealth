from __future__ import annotations

from datetime import datetime

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent / "tools"
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import add_project_root

add_project_root()

from src.core.lifecycle.models import MedicationOrder, Observation
from src.core.synthetic_patient_generator import (
    FHIRFormatter,
    TerminologyEntry,
    ValueSetMember,
    UmlsConcept,
    build_terminology_lookup,
)


def test_build_terminology_lookup_with_vsac_and_umls():
    loinc_entry = TerminologyEntry(
        code="2951-2",
        display="Sodium [Moles/volume] in Serum or Plasma",
        metadata={"ncbi_url": "https://example.org/loinc/2951-2"},
    )
    vsac_member = ValueSetMember(
        value_set_oid="2.16.840.1.113883.3.526.3.1567",
        value_set_name="Adolescent Depression Medications",
        code="2951-2",
        display="Sodium [Moles/volume] in Serum or Plasma",
        metadata={"value_set_version": "20210220"},
    )
    umls_concept = UmlsConcept(
        cui="C0020538",
        preferred_name="Hypertension",
        semantic_type="Disease or Syndrome",
        tui="T047",
        sab="ICD10CM",
        code="I10",
        tty="PT",
        metadata={},
    )

    context = {
        "loinc": [loinc_entry],
        "vsac": {vsac_member.value_set_oid: [vsac_member]},
        "umls": [umls_concept],
    }

    lookup = build_terminology_lookup(context)
    assert "vsac" in lookup and lookup["vsac"]
    assert any(
        entry.metadata.get("value_set_oid") == "2.16.840.1.113883.3.526.3.1567"
        for entry in lookup["vsac"].values()
    )
    assert "umls" in lookup and lookup["umls"]
    assert any(entry.code == "C0020538" for entry in lookup["umls"].values())


def test_build_coding_adds_umls_extension():
    icd_entry = TerminologyEntry(
        code="I10",
        display="Hypertension",
        metadata={},
    )
    umls_concept = UmlsConcept(
        cui="C0020538",
        preferred_name="Hypertension",
        semantic_type="Disease or Syndrome",
        tui="T047",
        sab="ICD10CM",
        code="I10",
        tty="PT",
        metadata={},
    )
    lookup = build_terminology_lookup({"icd10": [icd_entry], "umls": [umls_concept]})
    formatter = FHIRFormatter(lookup)

    coding = formatter._build_coding("http://hl7.org/fhir/sid/icd-10-cm", "I10", "Hypertension")
    umls_extensions = [
        ext
        for ext in coding.get("extension", [])
        if ext.get("url") == "http://example.org/fhir/StructureDefinition/umls-concept"
    ]
    assert umls_extensions
    nested = {item["url"]: item for item in umls_extensions[0]["extension"]}
    assert nested["cui"]["valueCode"] == "C0020538"


def test_observation_resource_includes_vsac_extension():
    loinc_entry = TerminologyEntry(
        code="2951-2",
        display="Sodium [Moles/volume] in Serum or Plasma",
        metadata={"ncbi_url": "https://example.org/loinc/2951-2"},
    )
    vsac_member = ValueSetMember(
        value_set_oid="2.16.840.1.113883.3.526.3.1567",
        value_set_name="Adolescent Depression Medications",
        code="2951-2",
        display="Sodium [Moles/volume] in Serum or Plasma",
        metadata={"value_set_version": "20210220"},
    )
    lookup = build_terminology_lookup({
        "loinc": [loinc_entry],
        "vsac": {vsac_member.value_set_oid: [vsac_member]},
    })
    formatter = FHIRFormatter(lookup)

    observation = Observation(
        observation_id="obs-1",
        patient_id="patient-1",
        name="Sodium",
        value="140",
        unit="mmol/L",
        status="normal",
        effective_datetime=datetime(2025, 5, 1, 12, 0, 0),
        metadata={"loinc_code": "2951-2", "value_numeric": 140},
    )

    resource = formatter.create_observation_resource("patient-1", observation)
    extension_urls = [ext.get("url") for ext in resource.get("extension", [])]
    assert "http://hl7.org/fhir/StructureDefinition/valueset-reference" in extension_urls


def test_medication_statement_includes_umls_extensions():
    rxnorm_entry = TerminologyEntry(
        code="12345",
        display="Sample RxNorm Drug",
        metadata={"ndc_example": "00000-0000"},
    )
    umls_concept = UmlsConcept(
        cui="C0000005",
        preferred_name="Sample RxNorm Drug",
        semantic_type="Clinical Drug",
        tui="T200",
        sab="RXNORM",
        code="12345",
        tty="IN",
        metadata={},
    )
    lookup = build_terminology_lookup({"rxnorm": [rxnorm_entry], "umls": [umls_concept]})
    formatter = FHIRFormatter(lookup)

    medication = MedicationOrder(
        medication_id="med-1",
        patient_id="patient-1",
        name="Sample RxNorm Drug",
        start_date=datetime(2025, 1, 2).date(),
        end_date=None,
        rxnorm_code="12345",
        ndc_code=None,
        therapeutic_class=None,
        metadata={},
    )

    resource = formatter.create_medication_statement_resource("patient-1", medication)
    coding = resource["medicationCodeableConcept"]["coding"][0]
    assert coding["code"] == "12345"
    extension_urls = [ext.get("url") for ext in coding.get("extension", [])]
    assert "http://example.org/fhir/StructureDefinition/umls-concept" in extension_urls
