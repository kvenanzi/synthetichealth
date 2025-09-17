import os
from pathlib import Path

from src.core.terminology import (
    filter_by_code,
    load_icd10_conditions,
    load_loinc_labs,
    load_rxnorm_medications,
    load_snomed_conditions,
    search_by_term,
)


def test_load_icd10_conditions_returns_entries():
    entries = load_icd10_conditions()
    codes = {entry.code for entry in entries}
    assert "E11.9" in codes
    assert any(entry.metadata["chapter"] == "Endocrine" for entry in entries)


def test_filter_by_code_subset():
    entries = load_loinc_labs()
    filtered = filter_by_code(entries, ["2951-2"])
    assert len(filtered) == 1
    assert filtered[0].display.startswith("Sodium")


def test_search_by_term_case_insensitive():
    entries = load_rxnorm_medications()
    results = search_by_term(entries, "lisinopril")
    assert results and results[0].code == "197361"


def test_environment_override(tmp_path: Path, monkeypatch):
    custom_dir = tmp_path / "terminology"
    custom_dir.mkdir()
    csv_path = custom_dir / "icd10" / "icd10_conditions.csv"
    csv_path.parent.mkdir()
    csv_path.write_text("code,description,chapter,ncbi_url\nA00,Cholera,Infectious,https://example.com\n", encoding="utf-8")

    monkeypatch.setenv("TERMINOLOGY_ROOT", str(custom_dir))
    entries = load_icd10_conditions()
    assert entries[0].code == "A00"
    monkeypatch.delenv("TERMINOLOGY_ROOT", raising=False)


def test_load_snomed_conditions_metadata_contains_mapping():
    entries = load_snomed_conditions()
    assert any(entry.metadata.get("icd10_mapping") == "I10" for entry in entries)
