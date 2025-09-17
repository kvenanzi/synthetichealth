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
from typing import Dict, Iterable, List, Optional

TERMINOLOGY_ROOT_ENV = "TERMINOLOGY_ROOT"
DEFAULT_TERMINOLOGY_DIR = Path("data/terminology")


@dataclass
class TerminologyEntry:
    """Simple structure representing a single terminology row."""

    code: str
    display: str
    metadata: Dict[str, str]


def _resolve_path(relative_path: str | Path, root_override: Optional[str] = None) -> Path:
    root = Path(root_override or os.environ.get(TERMINOLOGY_ROOT_ENV, DEFAULT_TERMINOLOGY_DIR))
    return root / relative_path


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


def load_icd10_conditions(root: Optional[str] = None) -> List[TerminologyEntry]:
    """Load ICD-10-CM condition concepts."""

    path = _resolve_path("icd10/icd10_conditions.csv", root)
    return _load_csv(path, code_field="code", display_field="description")


def load_loinc_labs(root: Optional[str] = None) -> List[TerminologyEntry]:
    """Load LOINC laboratory observations."""

    path = _resolve_path("loinc/loinc_labs.csv", root)
    return _load_csv(path, code_field="loinc_code", display_field="long_common_name")


def load_snomed_conditions(root: Optional[str] = None) -> List[TerminologyEntry]:
    path = _resolve_path("snomed/snomed_conditions.csv", root)
    return _load_csv(path, code_field="snomed_id", display_field="pt_name")


def load_rxnorm_medications(root: Optional[str] = None) -> List[TerminologyEntry]:
    path = _resolve_path("rxnorm/rxnorm_medications.csv", root)
    return _load_csv(path, code_field="rxnorm_cui", display_field="ingredient_name")


def filter_by_code(entries: Iterable[TerminologyEntry], codes: Iterable[str]) -> List[TerminologyEntry]:
    wanted = set(codes)
    return [entry for entry in entries if entry.code in wanted]


def search_by_term(entries: Iterable[TerminologyEntry], term: str) -> List[TerminologyEntry]:
    term_lower = term.lower()
    return [entry for entry in entries if term_lower in entry.display.lower()]


__all__ = [
    "TerminologyEntry",
    "load_icd10_conditions",
    "load_loinc_labs",
    "load_snomed_conditions",
    "load_rxnorm_medications",
    "filter_by_code",
    "search_by_term",
]
