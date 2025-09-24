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
    # Normalized ICD-10 tables start at chapter A; ensure at least one known code exists
    assert "A00" in codes
    assert any(entry.metadata.get("ncbi_url", "").startswith("https://icd10cmtool") for entry in entries)


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


def test_snomed_loader_prefers_normalized(monkeypatch, tmp_path: Path):
    base = tmp_path / "terminology"
    snomed_dir = base / "snomed"
    snomed_dir.mkdir(parents=True)

    normalized = snomed_dir / "snomed_full.csv"
    normalized.write_text(
        "snomed_id,pt_name,definition_status_id,ncbi_url\n"
        "123456,Test SNOMED Concept,900000000000074008,https://browser.ihtsdotools.org/?conceptId=123456\n",
        encoding="utf-8",
    )

    (snomed_dir / "snomed_conditions.csv").write_text(
        "snomed_id,pt_name,icd10_mapping,ncbi_url\n111111,Seed Concept,I10,https://example.com\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TERMINOLOGY_ROOT", str(base))
    entries = load_snomed_conditions()
    monkeypatch.delenv("TERMINOLOGY_ROOT", raising=False)

    assert entries[0].code == "123456"


def test_icd10_loader_prefers_normalized(monkeypatch, tmp_path: Path):
    base = tmp_path / "terminology"
    icd_dir = base / "icd10"
    icd_dir.mkdir(parents=True)

    normalized = icd_dir / "icd10_full.csv"
    normalized.write_text(
        "order,code,level,short_description,description,chapter,ncbi_url\n"
        "00001,A00,0,Cholera,Cholera,,https://icd10cmtool.cdc.gov/?fy=2026&code=A00\n",
        encoding="utf-8",
    )

    # Seed fallback (ignored because normalized exists)
    (icd_dir / "icd10_conditions.csv").write_text(
        "code,description,chapter,ncbi_url\nZZZ,Test,Chapter,https://example.com\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TERMINOLOGY_ROOT", str(base))
    entries = load_icd10_conditions()
    monkeypatch.delenv("TERMINOLOGY_ROOT", raising=False)

    assert entries[0].code == "A00"


def test_loinc_loader_prefers_normalized(monkeypatch, tmp_path: Path):
    base = tmp_path / "terminology"
    loinc_dir = base / "loinc"
    loinc_dir.mkdir(parents=True)

    normalized = loinc_dir / "loinc_full.csv"
    normalized.write_text(
        "loinc_code,long_common_name,component,property,system,loinc_class,ncbi_url\n"
        "9999-9,Normalized Test,COMP,PROP,SYS,CLASS,https://loinc.org/9999-9\n",
        encoding="utf-8",
    )

    # Seed fallback (should be ignored because normalized exists)
    (loinc_dir / "loinc_labs.csv").write_text(
        "loinc_code,long_common_name,component,property,system,ncbi_url\n"
        "1111-1,Seed Entry,COMP,PROP,SYS,https://loinc.org/1111-1\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TERMINOLOGY_ROOT", str(base))
    entries = load_loinc_labs()
    monkeypatch.delenv("TERMINOLOGY_ROOT", raising=False)

    assert entries[0].code == "9999-9"


def test_rxnorm_loader_prefers_normalized(monkeypatch, tmp_path: Path):
    base = tmp_path / "terminology"
    rx_dir = base / "rxnorm"
    rx_dir.mkdir(parents=True)

    normalized = rx_dir / "rxnorm_full.csv"
    normalized.write_text(
        "rxnorm_cui,tty,ingredient_name,source_code,sab,ndc_example,ncbi_url\n"
        "12345,SCD,Test Drug,,RXNORM,,https://rxnav.nlm.nih.gov/REST/rxcui/12345\n",
        encoding="utf-8",
    )

    (rx_dir / "rxnorm_medications.csv").write_text(
        "rxnorm_cui,tty,ingredient_name,ndc_example,ncbi_url\n99999,SCD,Seed Drug,,https://example.com\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("TERMINOLOGY_ROOT", str(base))
    entries = load_rxnorm_medications()
    monkeypatch.delenv("TERMINOLOGY_ROOT", raising=False)

    assert entries[0].code == "12345"
