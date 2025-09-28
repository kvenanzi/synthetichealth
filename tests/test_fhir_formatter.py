from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core.lifecycle.models import Observation
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
