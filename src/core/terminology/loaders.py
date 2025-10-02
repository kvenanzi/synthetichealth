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

import polars as pl

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


def _read_frame(
    table: str,
    csv_path: Path,
    root_override: Optional[str],
    required_columns: Optional[Dict[str, str]] = None,
) -> Optional[pl.DataFrame]:
    records = _fetch_table_records(table, root_override)
    if records is not None:
        return pl.DataFrame(records)
    if not csv_path.exists():
        return None
    frame = pl.read_csv(csv_path)
    if required_columns:
        missing = {col: default for col, default in required_columns.items() if col not in frame.columns}
        if missing:
            frame = frame.with_columns(
                [pl.lit(default).alias(col) for col, default in missing.items()]
            )
    return frame


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


def _load_rxnorm_frame(root_override: Optional[str] = None) -> Optional[pl.DataFrame]:
    path = _resolve_path("rxnorm/rxnorm_full.csv", root_override)
    required = {
        "rxnorm_cui": "",
        "tty": "",
        "ingredient_name": "",
        "source_code": "",
        "sab": "",
        "ndc_example": "",
        "ncbi_url": "",
    }
    return _read_frame("rxnorm", path, root_override, required)


def _load_snomed_frame(root_override: Optional[str] = None) -> Optional[pl.DataFrame]:
    path = _resolve_path("snomed/snomed_full.csv", root_override)
    required = {
        "snomed_id": "",
        "pt_name": "",
        "definition_status_id": "",
        "icd10_mapping": "",
        "ncbi_url": "",
    }
    return _read_frame("snomed", path, root_override, required)


def _clean_allergen_display(raw: str) -> str:
    name = raw.strip()
    lowered = name.lower()
    replacements = {
        "allergenic extract": "",
        "venom protein": "venom",
        "dander extract": "dander",
        "hair extract": "hair",
        "pollen extract": "pollen",
        "extract": "",
    }
    for old, new in replacements.items():
        if old in lowered:
            lowered = lowered.replace(old, new)
    lowered = lowered.replace("  ", " ")
    cleaned = " ".join(part for part in lowered.split() if part)
    if not cleaned:
        cleaned = raw.strip()
    display = cleaned.title()
    title_fixes = {
        "Ace": "ACE",
        "Arb": "ARB",
        "Ig": "Ig",
        "Ii": "II",
    }
    for needle, replacement in title_fixes.items():
        display = display.replace(needle, replacement)
    return display


def _classify_allergen(raw: str, default: str = "environment") -> str:
    lowered = raw.lower()
    food_terms = [
        "peanut",
        "shellfish",
        "shrimp",
        "crab",
        "lobster",
        "fish",
        "salmon",
        "tuna",
        "cod",
        "halibut",
        "egg",
        "milk",
        "soy",
        "wheat",
        "almond",
        "cashew",
        "hazelnut",
        "pistachio",
        "walnut",
        "pecan",
        "sesame",
        "banana",
        "strawberry",
        "avocado",
    ]
    insect_terms = [
        "venom",
        "bee",
        "wasp",
        "hornet",
        "yellow jacket",
    ]
    environment_terms = [
        "dander",
        "hair",
        "pollen",
        "dust",
        "mite",
        "mold",
        "fungus",
        "smut",
    ]

    if any(term in lowered for term in food_terms):
        return "food"
    if any(term in lowered for term in insect_terms):
        return "insect"
    if any(term in lowered for term in environment_terms):
        return "environment"
    return default


def load_allergen_entries(
    root: Optional[str] = None,
    *,
    max_allergens: int = 120,
) -> List[TerminologyEntry]:
    frame = _load_rxnorm_frame(root)
    if frame is None or frame.is_empty():
        return []

    frame = frame.with_columns(
        pl.col("rxnorm_cui").cast(pl.Utf8),
        pl.col("ingredient_name").str.strip_chars(),
    )
    frame = frame.filter(pl.col("ingredient_name").is_not_null() & (pl.col("ingredient_name") != ""))

    allergens: Dict[str, TerminologyEntry] = {}

    def _add_entry(row: Dict[str, Any], category: str, preferred_display: Optional[str] = None) -> None:
        if row is None:
            return
        raw_name = row.get("ingredient_name") or ""
        if not raw_name:
            return
        display = preferred_display or raw_name
        cleaned = _clean_allergen_display(display)
        key = cleaned.lower()
        if key in allergens:
            return
        code = str(row.get("rxnorm_cui") or cleaned)
        metadata = {
            "category": category,
            "rxnorm_name": raw_name,
        }
        if row.get("ndc_example"):
            metadata["ndc_example"] = str(row["ndc_example"])
        if row.get("ncbi_url"):
            metadata["ncbi_url"] = str(row["ncbi_url"])
        allergens[key] = TerminologyEntry(code=code, display=cleaned, metadata=metadata)

    lowercase_name = pl.col("ingredient_name").str.to_lowercase()
    candidates: List[pl.DataFrame] = [
        frame.filter(lowercase_name.str.contains("allergenic extract")),
        frame.filter(lowercase_name.str.contains("venom")),
        frame.filter(lowercase_name.str.contains("dander")),
        frame.filter(lowercase_name.str.contains("pollen")),
        frame.filter(lowercase_name.str.contains("mite")),
    ]

    for candidate in candidates:
        if candidate.is_empty():
            continue
        for row in candidate.to_dicts():
            category = _classify_allergen(row.get("ingredient_name", ""), "environment")
            _add_entry(row, category)

    curated_drugs = [
        "penicillin g",
        "penicillin v",
        "amoxicillin",
        "ampicillin",
        "cephalexin",
        "ceftriaxone",
        "sulfamethoxazole",
        "trimethoprim",
        "azithromycin",
        "erythromycin",
        "ibuprofen",
        "acetaminophen",
        "aspirin",
        "ketorolac",
        "naproxen",
        "lisinopril",
        "losartan",
        "metformin",
        "insulin lispro",
        "hydrochlorothiazide",
        "morphine",
        "oxycodone",
        "ondansetron",
        "piperacillin",
        "clindamycin",
        "vancomycin",
    ]

    lower_name = pl.col("ingredient_name").str.to_lowercase()
    for term in curated_drugs:
        matches = frame.filter(lower_name == term)
        if matches.is_empty():
            matches = frame.filter(lower_name.str.contains(term))
        if matches.is_empty():
            continue
        row = matches.row(0, named=True)
        _add_entry(row, "drug")

    food_terms = [
        "peanut allergenic extract",
        "egg white (chicken) allergenic extract",
        "egg yolk (chicken) allergenic extract",
        "goat milk allergenic extract",
        "cow milk allergenic extract",
        "soybean allergenic extract",
        "wheat allergenic extract",
        "shrimp allergenic extract",
        "crab allergenic extract",
        "lobster allergenic extract",
        "tuna allergenic extract",
        "salmon allergenic extract",
        "cashew nut allergenic extract",
        "pistachio nut allergenic extract",
        "almond allergenic extract",
        "hazelnut allergenic extract",
        "pecan allergenic extract",
        "walnut allergenic extract",
        "sesame seed allergenic extract",
        "banana allergenic extract",
        "strawberry allergenic extract",
        "avocado allergenic extract",
    ]

    for term in food_terms:
        matches = frame.filter(lower_name == term)
        if matches.is_empty():
            matches = frame.filter(lower_name.str.contains(term.split()[0]))
        if matches.is_empty():
            continue
        row = matches.row(0, named=True)
        _add_entry(row, "food")

    # Manual additions for common allergens not present in RxNorm ingredient list
    manual_allergens = [
        TerminologyEntry(
            code="latex",
            display="Natural Rubber Latex",
            metadata={
                "category": "environment",
                "snomed_code": "1003754000",
            },
        ),
    ]

    for entry in manual_allergens:
        key = entry.display.lower()
        if key not in allergens:
            allergens[key] = entry

    category_groups: Dict[str, List[TerminologyEntry]] = {}
    for entry in allergens.values():
        category = entry.metadata.get("category", "environment")
        category_groups.setdefault(category, []).append(entry)

    for bucket in category_groups.values():
        bucket.sort(key=lambda item: item.display)

    total_entries = sum(len(bucket) for bucket in category_groups.values())
    if max_allergens and total_entries > max_allergens:
        selected: List[TerminologyEntry] = []
        categories = [cat for cat, bucket in category_groups.items() if bucket]
        index = 0
        while categories and len(selected) < max_allergens:
            category = categories[index % len(categories)]
            bucket = category_groups[category]
            if bucket:
                selected.append(bucket.pop(0))
            if not bucket:
                categories = [cat for cat in categories if category_groups[cat]]
                index = 0
                continue
            index += 1
        return selected

    ordered: List[TerminologyEntry] = []
    for category in sorted(category_groups.keys()):
        ordered.extend(category_groups[category])
    return ordered


def load_allergy_reaction_entries(root: Optional[str] = None) -> List[Dict[str, str]]:
    snomed_frame = _load_snomed_frame(root)
    reactions: List[Dict[str, str]] = []

    reaction_definitions = [
        ("Anaphylaxis", "39579001"),
        ("Urticaria", "126485001"),
        ("Angioedema", "41291007"),
        ("Bronchospasm", "427461000"),
        ("Wheezing", "56018004"),
        ("Shortness of breath", "267036007"),
        ("Nausea", "422587007"),
        ("Vomiting", "422400008"),
        ("Rash", "271807003"),
        ("Itching", "418290006"),
        ("Hypotension", "45007003"),
        ("Tachycardia", "3424008"),
    ]

    valid_codes: Dict[str, str] = {}
    if snomed_frame is not None and not snomed_frame.is_empty():
        snomed_frame = snomed_frame.with_columns(pl.col("snomed_id").cast(pl.Utf8))
        lookup = {row[0]: row[1] for row in snomed_frame.select(["snomed_id", "pt_name"]).to_numpy()}
        valid_codes = lookup

    for display, code in reaction_definitions:
        if valid_codes and code not in valid_codes:
            continue
        reactions.append(
            {
                "display": display,
                "code": code,
                "system": "http://snomed.info/sct",
            }
        )

    return reactions


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
