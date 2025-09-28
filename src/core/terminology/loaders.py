"""Terminology loading utilities for Phase 2.

These helpers read normalized CSV extracts located under ``data/terminology`` by
default, but callers can pass alternate paths to point at the full NCBI/NLM
releases or institutional vocabularies.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:  # optional dependency for DuckDB-backed lookups
    import duckdb  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional import
    duckdb = None

TERMINOLOGY_ROOT_ENV = "TERMINOLOGY_ROOT"
TERMINOLOGY_DB_ENV = "TERMINOLOGY_DB_PATH"
DEFAULT_TERMINOLOGY_DIR = Path("data/terminology")
DEFAULT_TERMINOLOGY_DB = DEFAULT_TERMINOLOGY_DIR / "terminology.duckdb"


@dataclass
class TerminologyEntry:
    """Simple structure representing a single terminology row."""

    code: str
    display: str
    metadata: Dict[str, str]


@dataclass
class ValueSetMember:
    """Represents a single VSAC value set membership."""

    value_set_oid: str
    value_set_name: str
    code: str
    display: str
    metadata: Dict[str, str]


@dataclass
class UmlsConcept:
    """Represents a normalized UMLS concept atom."""

    cui: str
    preferred_name: str
    semantic_type: str
    tui: str
    sab: str
    code: str
    tty: str
    metadata: Dict[str, str]


def _resolve_path(relative_path: str | Path, root_override: Optional[str] = None) -> Path:
    root = Path(root_override or os.environ.get(TERMINOLOGY_ROOT_ENV, DEFAULT_TERMINOLOGY_DIR))
    return root / relative_path


def _resolve_db_path(root_override: Optional[str]) -> Optional[Path]:
    if db_env := os.environ.get(TERMINOLOGY_DB_ENV):
        candidate = Path(db_env)
        if candidate.exists():
            return candidate
    if root_override:
        candidate = Path(root_override)
        if candidate.is_dir():
            db_candidate = candidate / "terminology.duckdb"
            if db_candidate.exists():
                return db_candidate
        elif candidate.exists():
            return candidate
    if DEFAULT_TERMINOLOGY_DB.exists():
        return DEFAULT_TERMINOLOGY_DB
    return None


def _fetch_table_records(table: str, root_override: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """Fetch all rows from a DuckDB table, returning ``None`` on failure."""

    if duckdb is None:
        return None
    db_path = _resolve_db_path(root_override)
    if not db_path:
        return None
    try:
        con = duckdb.connect(str(db_path))
    except Exception:  # pragma: no cover - connection failure
        return None
    try:
        try:
            df = con.execute(f"SELECT * FROM {table}").fetchdf()
        except Exception:
            return None
    finally:
        con.close()
    return df.to_dict(orient="records") if not df.empty else []


def _load_from_db(
    table: str,
    code_field: str,
    display_field: str,
    root_override: Optional[str],
) -> Optional[List[TerminologyEntry]]:
    records = _fetch_table_records(table, root_override)
    if records is None:
        return None
    entries: List[TerminologyEntry] = []
    for row in records:
        code = row.get(code_field)
        display = row.get(display_field)
        if not code or not display:
            continue
        metadata = {k: ("" if v is None else str(v)) for k, v in row.items() if k not in {code_field, display_field}}
        entries.append(TerminologyEntry(code=str(code), display=str(display), metadata=metadata))
    return entries if entries else None


def _load_csv(path: Path, code_field: str, display_field: str) -> List[TerminologyEntry]:
    if not path.exists():
        raise FileNotFoundError(f"Terminology file not found: {path}")

    entries: List[TerminologyEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = row.get(code_field)
            display = row.get(display_field)
            if not code or not display:
                continue
            metadata = {k: v for k, v in row.items() if k not in {code_field, display_field}}
            entries.append(TerminologyEntry(code=code, display=display, metadata=metadata))
    return entries


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]


def load_icd10_conditions(root: Optional[str] = None) -> List[TerminologyEntry]:
    """Load ICD-10-CM condition concepts."""

    db_entries = _load_from_db("icd10", "code", "description", root)
    if db_entries is not None:
        return db_entries
    normalized_path = _resolve_path("icd10/icd10_full.csv", root)
    if normalized_path.exists():
        path = normalized_path
        code_field = "code"
        display_field = "description"
    else:
        path = _resolve_path("icd10/icd10_conditions.csv", root)
        code_field = "code"
        display_field = "description"
    return _load_csv(path, code_field=code_field, display_field=display_field)


def load_loinc_labs(root: Optional[str] = None) -> List[TerminologyEntry]:
    """Load LOINC laboratory observations.

    Prefers the normalized ``loinc_full.csv`` produced by ``tools/import_loinc.py``
    but falls back to the seed file committed in the repository.
    """

    db_entries = _load_from_db("loinc", "loinc_code", "long_common_name", root)
    if db_entries is not None:
        return db_entries
    normalized_path = _resolve_path("loinc/loinc_full.csv", root)
    if normalized_path.exists():
        path = normalized_path
    else:
        path = _resolve_path("loinc/loinc_labs.csv", root)
    return _load_csv(path, code_field="loinc_code", display_field="long_common_name")


def load_snomed_conditions(root: Optional[str] = None) -> List[TerminologyEntry]:
    db_entries = _load_from_db("snomed", "snomed_id", "pt_name", root)
    if db_entries is not None:
        return db_entries
    normalized_path = _resolve_path("snomed/snomed_full.csv", root)
    if normalized_path.exists():
        path = normalized_path
    else:
        path = _resolve_path("snomed/snomed_conditions.csv", root)
    return _load_csv(path, code_field="snomed_id", display_field="pt_name")


def load_rxnorm_medications(root: Optional[str] = None) -> List[TerminologyEntry]:
    db_entries = _load_from_db("rxnorm", "rxnorm_cui", "ingredient_name", root)
    if db_entries is not None:
        return db_entries
    normalized_path = _resolve_path("rxnorm/rxnorm_full.csv", root)
    if normalized_path.exists():
        path = normalized_path
    else:
        path = _resolve_path("rxnorm/rxnorm_medications.csv", root)
    return _load_csv(path, code_field="rxnorm_cui", display_field="ingredient_name")


def load_vsac_value_sets(root: Optional[str] = None) -> List[ValueSetMember]:
    """Load VSAC value set members from DuckDB or CSV files.

    Returns an empty list when neither a DuckDB table nor CSV export is present.
    """

    rows = _fetch_table_records("vsac_value_sets", root)
    if rows is None:
        normalized_path = _resolve_path("vsac/vsac_value_sets_full.csv", root)
        seed_path = _resolve_path("vsac/vsac_value_sets.csv", root)
        if normalized_path.exists():
            rows = _read_csv_rows(normalized_path)
        elif seed_path.exists():
            rows = _read_csv_rows(seed_path)
        else:
            return []

    members: List[ValueSetMember] = []
    for row in rows:
        oid = (row.get("value_set_oid") or "").strip()
        code = (row.get("code") or "").strip()
        display = (row.get("display_name") or "").strip()
        if not oid or not code or not display:
            continue
        member = ValueSetMember(
            value_set_oid=oid,
            value_set_name=(row.get("value_set_name") or "").strip(),
            code=code,
            display=display,
            metadata={
                key: (value if value is not None else "")
                for key, value in row.items()
                if key not in {"value_set_oid", "value_set_name", "code", "display_name"}
            },
        )
        members.append(member)
    return members


def load_umls_concepts(root: Optional[str] = None) -> List[UmlsConcept]:
    """Load UMLS concept atoms from DuckDB or CSV files."""

    rows = _fetch_table_records("umls_concepts", root)
    if rows is None:
        normalized_path = _resolve_path("umls/umls_concepts_full.csv", root)
        seed_path = _resolve_path("umls/umls_concepts.csv", root)
        if normalized_path.exists():
            rows = _read_csv_rows(normalized_path)
        elif seed_path.exists():
            rows = _read_csv_rows(seed_path)
        else:
            return []

    concepts: List[UmlsConcept] = []
    for row in rows:
        cui = (row.get("cui") or "").strip()
        preferred = (row.get("preferred_name") or "").strip()
        sab = (row.get("sab") or "").strip()
        code = (row.get("code") or "").strip()
        tty = (row.get("tty") or "").strip()
        if not cui or not preferred:
            continue
        concept = UmlsConcept(
            cui=cui,
            preferred_name=preferred,
            semantic_type=(row.get("semantic_type") or "").strip(),
            tui=(row.get("tui") or "").strip(),
            sab=sab,
            code=code,
            tty=tty,
            metadata={
                key: (value if value is not None else "")
                for key, value in row.items()
                if key not in {"cui", "preferred_name", "semantic_type", "tui", "sab", "code", "tty"}
            },
        )
        concepts.append(concept)
    return concepts


def filter_by_code(entries: Iterable[TerminologyEntry], codes: Iterable[str]) -> List[TerminologyEntry]:
    wanted = set(codes)
    return [entry for entry in entries if entry.code in wanted]


def search_by_term(entries: Iterable[TerminologyEntry], term: str) -> List[TerminologyEntry]:
    term_lower = term.lower()
    return [entry for entry in entries if term_lower in entry.display.lower()]


__all__ = [
    "TerminologyEntry",
    "ValueSetMember",
    "UmlsConcept",
    "load_icd10_conditions",
    "load_loinc_labs",
    "load_snomed_conditions",
    "load_rxnorm_medications",
    "load_vsac_value_sets",
    "load_umls_concepts",
    "filter_by_code",
    "search_by_term",
]
