"""Tests for the DuckDB terminology warehouse builder."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.build_terminology_db import build_database


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _seed_minimal_terminology(root: Path) -> None:
    _write_csv(
        root / "icd10/icd10_conditions.csv",
        ["code", "description", "chapter", "ncbi_url"],
        [["A00", "Cholera", "Certain infectious and parasitic diseases", "https://ncbi.example/A00"]],
    )
    _write_csv(
        root / "loinc/loinc_labs.csv",
        ["loinc_code", "long_common_name", "component", "property", "system", "ncbi_url"],
        [["1234-5", "Glucose [Mass/volume] in Blood", "Glucose", "MCnc", "Bld", "https://ncbi.example/loinc"]],
    )
    _write_csv(
        root / "snomed/snomed_conditions.csv",
        ["snomed_id", "pt_name", "icd10_mapping", "ncbi_url"],
        [["123456", "Diabetes mellitus", "E11", "https://ncbi.example/snomed"]],
    )
    _write_csv(
        root / "rxnorm/rxnorm_medications.csv",
        ["rxnorm_cui", "tty", "ingredient_name", "ndc_example", "ncbi_url"],
        [["12345", "IN", "Metformin", "00000-0000", "https://ncbi.example/rxnorm"]],
    )


def test_build_creates_optional_tables_when_missing(tmp_path: Path) -> None:
    root = tmp_path / "terminology"
    _seed_minimal_terminology(root)
    output = root / "terminology.duckdb"

    build_database(root, output, force=True)

    con = duckdb.connect(str(output))
    try:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert "vsac_value_sets" in tables
        assert "umls_concepts" in tables
        vsac_count = con.execute("SELECT COUNT(*) FROM vsac_value_sets").fetchone()[0]
        umls_count = con.execute("SELECT COUNT(*) FROM umls_concepts").fetchone()[0]
    finally:
        con.close()

    assert vsac_count == 0
    assert umls_count == 0


def test_build_requires_force_when_database_exists(tmp_path: Path) -> None:
    root = tmp_path / "terminology"
    _seed_minimal_terminology(root)
    output = root / "terminology.duckdb"

    build_database(root, output, force=True)

    with pytest.raises(SystemExit):
        build_database(root, output)
