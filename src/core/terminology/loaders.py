"""Terminology loading utilities for Phase 2.

These helpers read normalized CSV extracts located under ``data/terminology`` by
default, but callers can pass alternate paths to point at the full NCBI/NLM
releases or institutional vocabularies.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import polars as pl
from ..terminology_catalogs import ALLERGENS as FALLBACK_ALLERGEN_TERMS

try:  # optional dependency for DuckDB-backed lookups
    import duckdb  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional import
    duckdb = None
else:  # pragma: no cover - enable compatibility for reserved keywords
    _duckdb_execute = duckdb.DuckDBPyConnection.execute

    def _execute_with_reserved_fallback(self, query, parameters=None):
        try:
            return _duckdb_execute(self, query, parameters)
        except duckdb.ParserException as exc:
            text = str(exc).lower()
            lowered_query = (query or "").lower() if isinstance(query, str) else ""
            if "near \"order\"" in text and "create table" in lowered_query and " order " in lowered_query:
                patched_query = query.replace(" order ", ' "order" ')
                if patched_query != query:
                    return _duckdb_execute(self, patched_query, parameters)
            raise

    duckdb.DuckDBPyConnection.execute = _execute_with_reserved_fallback

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
    root_candidate = root_override or os.environ.get(TERMINOLOGY_ROOT_ENV)
    if root_candidate:
        candidate = Path(root_candidate)
        if candidate.is_dir():
            db_candidate = candidate / "terminology.duckdb"
            if db_candidate.exists():
                return db_candidate
        elif candidate.exists() and candidate.suffix.lower() == ".duckdb":
            return candidate
        # Explicit root override without a DuckDB should force CSV fallback
        return None
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
    crosswalk = load_snomed_icd10_crosswalk(root)

    def _attach_icd10_mappings(entries: List[TerminologyEntry]) -> List[TerminologyEntry]:
        if not crosswalk:
            return entries
        snomed_to_icd10: Dict[str, Set[str]] = defaultdict(set)
        for icd10_code, mappings in crosswalk.items():
            for mapping in mappings:
                snomed_to_icd10[str(mapping.code)].add(icd10_code)
        for entry in entries:
            current = entry.metadata.get("icd10_mapping")
            if current:
                continue
            codes = sorted(snomed_to_icd10.get(entry.code, []))
            if codes:
                entry.metadata["icd10_mapping"] = ";".join(codes)
        return entries

    db_entries = _load_from_db("snomed", "snomed_id", "pt_name", root)
    if db_entries is not None:
        return _attach_icd10_mappings(db_entries)
    normalized_path = _resolve_path("snomed/snomed_full.csv", root)
    if normalized_path.exists():
        path = normalized_path
    else:
        path = _resolve_path("snomed/snomed_conditions.csv", root)
    entries = _load_csv(path, code_field="snomed_id", display_field="pt_name")
    return _attach_icd10_mappings(entries)


def load_snomed_icd10_crosswalk(root: Optional[str] = None) -> Dict[str, List[TerminologyEntry]]:
    """Return mapping of ICD-10 codes to SNOMED concepts from the curated seed file."""

    path = _resolve_path("snomed/snomed_conditions.csv", root)
    if not path.exists():
        return {}

    def _normalize_icd10(raw_code: str) -> str:
        code = (raw_code or "").strip().upper()
        if not code:
            return ""
        code = code.replace(".", "")
        if len(code) > 3:
            code = f"{code[:3]}.{code[3:]}"
        return code

    crosswalk: Dict[str, List[TerminologyEntry]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            snomed_code = row.get("snomed_id")
            display = row.get("pt_name")
            icd10_mapping = row.get("icd10_mapping", "")
            if not snomed_code or not display or not icd10_mapping:
                continue
            metadata = {k: v for k, v in row.items() if k not in {"snomed_id", "pt_name", "icd10_mapping"}}
            entry = TerminologyEntry(code=str(snomed_code), display=str(display), metadata=metadata)
            for raw_code in icd10_mapping.replace(";", ",").split(","):
                normalized = _normalize_icd10(raw_code)
                if normalized:
                    crosswalk[normalized].append(entry)
    return crosswalk


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


def _value_set_contains_allergen(name: str, metadata: Dict[str, Any]) -> bool:
    tokens = [name.lower()]
    for key in ('clinical_focus', 'value_set_name'):
        value = metadata.get(key)
        if value:
            tokens.append(str(value).lower())
    haystack = ' '.join(tokens)
    keywords = [
        'allergen',
        'allergy',
        'hypersens',
        'ige',
        'anaphylaxis',
        'immunotherapy',
        'venom',
        'latex',
        'drug allergy',
        'food allergy',
    ]
    return any(keyword in haystack for keyword in keywords)


CURATED_MEDICATIONS = [
    {"display": "Lisinopril", "therapeutic_class": "ace_inhibitor", "keywords": ["lisinopril"]},
    {"display": "Enalapril", "therapeutic_class": "ace_inhibitor", "keywords": ["enalapril"]},
    {"display": "Losartan", "therapeutic_class": "arb", "keywords": ["losartan"]},
    {"display": "Valsartan", "therapeutic_class": "arb", "keywords": ["valsartan"]},
    {"display": "Amlodipine", "therapeutic_class": "calcium_channel_blocker", "keywords": ["amlodipine"]},
    {"display": "Hydrochlorothiazide", "therapeutic_class": "thiazide_diuretic", "keywords": ["hydrochlorothiazide"]},
    {"display": "Metoprolol", "therapeutic_class": "beta_blocker", "keywords": ["metoprolol"]},
    {"display": "Carvedilol", "therapeutic_class": "beta_blocker", "keywords": ["carvedilol"]},
    {"display": "Furosemide", "therapeutic_class": "loop_diuretic", "keywords": ["furosemide"]},
    {"display": "Spironolactone", "therapeutic_class": "aldosterone_antagonist", "keywords": ["spironolactone"]},
    {"display": "Atorvastatin", "therapeutic_class": "statin", "keywords": ["atorvastatin"]},
    {"display": "Rosuvastatin", "therapeutic_class": "statin", "keywords": ["rosuvastatin"]},
    {"display": "Simvastatin", "therapeutic_class": "statin", "keywords": ["simvastatin"]},
    {"display": "Metformin", "therapeutic_class": "biguanide", "keywords": ["metformin"]},
    {"display": "Glipizide", "therapeutic_class": "sulfonylurea", "keywords": ["glipizide"]},
    {"display": "Sitagliptin", "therapeutic_class": "dpp4_inhibitor", "keywords": ["sitagliptin"]},
    {"display": "Empagliflozin", "therapeutic_class": "sglt2_inhibitor", "keywords": ["empagliflozin"]},
    {"display": "Insulin Glargine", "therapeutic_class": "basal_insulin", "keywords": ["insulin glargine", "insulin, glargine"]},
    {"display": "Insulin Lispro", "therapeutic_class": "rapid_insulin", "keywords": ["insulin lispro", "lispro insulin"]},
    {"display": "Dulaglutide", "therapeutic_class": "glp1_agonist", "keywords": ["dulaglutide"]},
    {"display": "Warfarin", "therapeutic_class": "anticoagulant", "keywords": ["warfarin"]},
    {"display": "Apixaban", "therapeutic_class": "anticoagulant", "keywords": ["apixaban"]},
    {"display": "Rivaroxaban", "therapeutic_class": "anticoagulant", "keywords": ["rivaroxaban"]},
    {"display": "Aspirin", "therapeutic_class": "antiplatelet", "keywords": ["aspirin"]},
    {"display": "Clopidogrel", "therapeutic_class": "antiplatelet", "keywords": ["clopidogrel"]},
    {"display": "Sertraline", "therapeutic_class": "ssri", "keywords": ["sertraline"]},
    {"display": "Fluoxetine", "therapeutic_class": "ssri", "keywords": ["fluoxetine"]},
    {"display": "Escitalopram", "therapeutic_class": "ssri", "keywords": ["escitalopram"]},
    {"display": "Bupropion", "therapeutic_class": "antidepressant", "keywords": ["bupropion"]},
    {"display": "Duloxetine", "therapeutic_class": "snri", "keywords": ["duloxetine"]},
    {"display": "Albuterol", "therapeutic_class": "bronchodilator", "keywords": ["albuterol", "salbutamol"]},
    {"display": "Levalbuterol", "therapeutic_class": "bronchodilator", "keywords": ["levalbuterol"]},
    {"display": "Budesonide/Formoterol", "therapeutic_class": "inhaled_combo", "keywords": ["budesonide/formoterol", "budesonide and formoterol"]},
    {"display": "Fluticasone", "therapeutic_class": "inhaled_steroid", "keywords": ["fluticasone"]},
    {"display": "Tiotropium", "therapeutic_class": "long_acting_anticholinergic", "keywords": ["tiotropium"]},
    {"display": "Montelukast", "therapeutic_class": "leukotriene_modifier", "keywords": ["montelukast"]},
    {"display": "Hydroxychloroquine", "therapeutic_class": "dmard", "keywords": ["hydroxychloroquine"]},
    {"display": "Methotrexate", "therapeutic_class": "dmard", "keywords": ["methotrexate"]},
    {"display": "Adalimumab", "therapeutic_class": "biologic_dmard", "keywords": ["adalimumab"]},
    {"display": "Etanercept", "therapeutic_class": "biologic_dmard", "keywords": ["etanercept"]},
    {"display": "Epinephrine", "therapeutic_class": "emergency_anaphylaxis", "keywords": ["epinephrine"]},
    {"display": "Cetirizine", "therapeutic_class": "antihistamine", "keywords": ["cetirizine"]},
    {"display": "Loratadine", "therapeutic_class": "antihistamine", "keywords": ["loratadine"]},
    {"display": "Diphenhydramine", "therapeutic_class": "antihistamine", "keywords": ["diphenhydramine"]},
    {"display": "Paxlovid", "therapeutic_class": "antiviral", "keywords": ["paxlovid", "nirmatrelvir"]},
    {"display": "Remdesivir", "therapeutic_class": "antiviral", "keywords": ["remdesivir"]},
    {"display": "Oseltamivir", "therapeutic_class": "antiviral", "keywords": ["oseltamivir"]},
    {"display": "Zanamivir", "therapeutic_class": "antiviral", "keywords": ["zanamivir"]},
    {"display": "Prednisone", "therapeutic_class": "glucocorticoid", "keywords": ["prednisone"]},
    {"display": "Levothyroxine", "therapeutic_class": "thyroid_replacement", "keywords": ["levothyroxine"]},
    {"display": "Omeprazole", "therapeutic_class": "ppi", "keywords": ["omeprazole"]},
    {"display": "Ondansetron", "therapeutic_class": "antiemetic", "keywords": ["ondansetron"]},
    {"display": "Cyclophosphamide", "therapeutic_class": "chemotherapy", "keywords": ["cyclophosphamide"]},
    {"display": "Doxorubicin", "therapeutic_class": "chemotherapy", "keywords": ["doxorubicin"]},
    {"display": "Paclitaxel", "therapeutic_class": "chemotherapy", "keywords": ["paclitaxel"]},
    {"display": "Trastuzumab", "therapeutic_class": "targeted_therapy", "keywords": ["trastuzumab"]},
    {"display": "Bevacizumab", "therapeutic_class": "targeted_therapy", "keywords": ["bevacizumab"]},
]

CURATED_LAB_TESTS = [
    {
        "name": "Prothrombin Time",
        "loinc": "5902-2",
        "units": "s",
        "normal_range": (10, 13),
        "critical_high": 20,
        "panels": ["Coagulation_Panel"],
    },
    {
        "name": "International Normalized Ratio",
        "loinc": "34714-6",
        "units": "ratio",
        "normal_range": (0.9, 1.2),
        "critical_low": 0.5,
        "critical_high": 4.5,
        "panels": ["Coagulation_Panel"],
    },
    {
        "name": "Activated Partial Thromboplastin Time",
        "loinc": "14979-9",
        "units": "s",
        "normal_range": (25, 35),
        "critical_high": 80,
        "panels": ["Coagulation_Panel"],
    },
    {
        "name": "D-Dimer",
        "loinc": "48065-7",
        "units": "ng/mL",
        "normal_range": (0, 500),
        "critical_high": 1000,
        "panels": ["Coagulation_Panel", "Inflammatory_Markers"],
    },
    {
        "name": "B-Type Natriuretic Peptide",
        "loinc": "30934-4",
        "units": "pg/mL",
        "normal_range": (0, 100),
        "critical_high": 1000,
        "panels": ["Cardiac_Markers", "Cardiology_Followup"],
    },
    {
        "name": "N-terminal proBNP",
        "loinc": "33762-6",
        "units": "pg/mL",
        "normal_range": (0, 125),
        "critical_high": 5000,
        "panels": ["Cardiac_Markers", "Cardiology_Followup"],
    },
    {
        "name": "High Sensitivity Troponin I",
        "loinc": "67151-1",
        "units": "ng/L",
        "normal_range": (0, 14),
        "critical_high": 100,
        "panels": ["Cardiac_Markers", "Cardiac_Markers_Advanced"],
    },
    {
        "name": "Vitamin D 25-Hydroxy",
        "loinc": "1989-3",
        "units": "ng/mL",
        "normal_range": (30, 100),
        "critical_low": 10,
        "panels": ["Metabolic_Nutrition"],
    },
    {
        "name": "Ferritin",
        "loinc": "2276-4",
        "units": "ng/mL",
        "normal_range": (30, 300),
        "critical_low": 10,
        "panels": ["Hematology_Iron"],
    },
    {
        "name": "Serum Iron",
        "loinc": "2498-4",
        "units": "ug/dL",
        "normal_range": (60, 170),
        "critical_low": 30,
        "critical_high": 300,
        "panels": ["Hematology_Iron"],
    },
    {
        "name": "Total Iron Binding Capacity",
        "loinc": "2500-7",
        "units": "ug/dL",
        "normal_range": (240, 450),
        "panels": ["Hematology_Iron"],
    },
    {
        "name": "Transferrin",
        "loinc": "3034-6",
        "units": "mg/dL",
        "normal_range": (200, 350),
        "panels": ["Hematology_Iron"],
    },
    {
        "name": "C-Reactive Protein High Sensitivity",
        "loinc": "30522-7",
        "units": "mg/L",
        "normal_range": (0, 3),
        "critical_high": 50,
        "panels": ["Inflammatory_Markers"],
    },
    {
        "name": "TSH Receptor Antibody",
        "loinc": "5385-0",
        "units": "IU/L",
        "normal_range": (0, 1.75),
        "panels": ["Thyroid_Function"],
    },
    {
        "name": "Free T3",
        "loinc": "3051-0",
        "units": "pg/mL",
        "normal_range": (2.0, 4.4),
        "panels": ["Thyroid_Function", "Endocrine"]
    },
    {
        "name": "Cortisol",
        "loinc": "2153-8",
        "units": "ug/dL",
        "normal_range": (5, 23),
        "panels": ["Endocrine"],
    },
    {
        "name": "Lactate",
        "loinc": "2519-7",
        "units": "mmol/L",
        "normal_range": (0.5, 2.2),
        "critical_high": 4.0,
        "panels": ["Sepsis_Markers"],
    },
    {
        "name": "Procalcitonin",
        "loinc": "33959-8",
        "units": "ng/mL",
        "normal_range": (0, 0.5),
        "critical_high": 10,
        "panels": ["Sepsis_Markers", "Inflammatory_Markers"],
    },
    {
        "name": "Total IgE",
        "loinc": "19113-0",
        "units": "kU/L",
        "normal_range": (0, 100),
        "critical_high": 500,
        "panels": ["Allergy_IgE"],
    },
    {
        "name": "Peanut Specific IgE",
        "loinc": "39517-9",
        "units": "kU/L",
        "normal_range": (0, 0.35),
        "critical_high": 100,
        "panels": ["Allergy_IgE", "Food_Allergen_IgE"],
    },
    {
        "name": "Egg White Specific IgE",
        "loinc": "6106-7",
        "units": "kU/L",
        "normal_range": (0, 0.35),
        "critical_high": 100,
        "panels": ["Food_Allergen_IgE"],
    },
    {
        "name": "Penicillin Specific IgE",
        "loinc": "6130-2",
        "units": "kU/L",
        "normal_range": (0, 0.35),
        "critical_high": 100,
        "panels": ["Drug_Allergy_IgE"],
    },
    {
        "name": "Serum Tryptase",
        "loinc": "21582-2",
        "units": "ng/mL",
        "normal_range": (0, 11.4),
        "critical_high": 30,
        "panels": ["Anaphylaxis_Workup"],
    },
]

def load_allergen_entries(
    root: Optional[str] = None,
    *,
    max_allergens: int = 120,
) -> List[TerminologyEntry]:
    try:
        vsac_members = load_vsac_value_sets(root)
    except Exception:  # pragma: no cover - VSAC loader fallback
        vsac_members = []

    frame = _load_rxnorm_frame(root)
    fallback_lookup = {
        item["display"].lower(): item for item in FALLBACK_ALLERGEN_TERMS
    }

    allergens: Dict[str, TerminologyEntry] = {}

    def _score(metadata: Dict[str, Any]) -> int:
        score = 0
        if metadata.get("rxnorm_name"):
            score += 2
        if metadata.get("value_set_oid"):
            score += 1
        if metadata.get("snomed_code"):
            score += 1
        return score

    def _store(entry: TerminologyEntry) -> None:
        key = entry.display.lower()
        fallback = fallback_lookup.get(key)
        if fallback:
            if fallback.get("unii") and not entry.metadata.get("unii"):
                entry.metadata["unii"] = fallback["unii"]
            if fallback.get("snomed") and not entry.metadata.get("snomed_code"):
                entry.metadata["snomed_code"] = fallback["snomed"]
            if fallback.get("rxnorm") and not entry.metadata.get("rxnorm_name"):
                entry.metadata["rxnorm_name"] = fallback["display"]
        existing = allergens.get(key)
        if existing is None:
            allergens[key] = entry
            return
        if _score(entry.metadata) > _score(existing.metadata):
            allergens[key] = entry

    for member in vsac_members:
        display = _clean_allergen_display(member.display or "")
        if not display:
            continue
        context_name = f"{member.value_set_name} {member.display}"
        if not _value_set_contains_allergen(context_name, member.metadata):
            continue
        category = _classify_allergen(display, default="drug")
        metadata = {
            "category": category,
            "value_set_oid": member.value_set_oid,
            "value_set_name": member.value_set_name,
        }
        code_system = (member.metadata.get("code_system") or "").lower()
        if code_system:
            metadata["code_system"] = member.metadata.get("code_system")
        if "rxnorm" in code_system:
            metadata["rxnorm_name"] = display
        if "snomed" in code_system:
            metadata["snomed_code"] = member.code
        metadata.update(
            {
                key: value
                for key, value in member.metadata.items()
                if key not in {"code_system", "code_system_version"}
            }
        )
        entry = TerminologyEntry(code=str(member.code or display), display=display, metadata=metadata)
        _store(entry)

    if frame is not None and not frame.is_empty():
        frame = frame.with_columns(
            pl.col("rxnorm_cui").cast(pl.Utf8),
            pl.col("ingredient_name").str.strip_chars(),
        )
        frame = frame.filter(pl.col("ingredient_name").is_not_null() & (pl.col("ingredient_name") != ""))

        lowercase_name = pl.col("ingredient_name").str.to_lowercase()

        def _add_entry(row: Dict[str, Any], preferred_display: Optional[str] = None) -> None:
            if not row:
                return
            raw_name = row.get("ingredient_name") or ""
            if not raw_name:
                return
            display = _clean_allergen_display(preferred_display or raw_name)
            category = _classify_allergen(raw_name)
            metadata = {
                "category": category,
                "rxnorm_name": row.get("ingredient_name", display),
            }
            if row.get("ndc_example"):
                metadata["ndc_example"] = str(row["ndc_example"])
            if row.get("ncbi_url"):
                metadata["ncbi_url"] = str(row["ncbi_url"])
            entry = TerminologyEntry(code=str(row.get("rxnorm_cui") or display), display=display, metadata=metadata)
            _store(entry)

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
                _add_entry(row)

        curated_terms = [
            "penicillin",
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
            "insulin",
            "hydrochlorothiazide",
            "morphine",
            "oxycodone",
            "ondansetron",
            "piperacillin",
            "clindamycin",
            "vancomycin",
        ]

        lower_name = pl.col("ingredient_name").str.to_lowercase()
        for term in curated_terms:
            matches = frame.filter(lower_name == term)
            if matches.is_empty():
                matches = frame.filter(lower_name.str.contains(term))
            if matches.is_empty():
                continue
            row = matches.row(0, named=True)
            _add_entry(row, preferred_display=term)

    if max_allergens:
        critical_fallbacks = {
            "peanut",
            "peanut oil",
            "almond",
            "shrimp",
            "penicillin",
            "penicillin g",
            "penicillin v",
            "amoxicillin",
        }
        for item in FALLBACK_ALLERGEN_TERMS:
            key = item["display"].lower()
            adding_new = key not in allergens
            if adding_new and max_allergens and len(allergens) >= max_allergens and key not in critical_fallbacks:
                continue
            metadata = {
                "category": item.get("category", "fallback"),
                "unii": item.get("unii", ""),
                "snomed_code": item.get("snomed", ""),
            }
            if item.get("rxnorm"):
                metadata["rxnorm_name"] = item["display"]
            entry = TerminologyEntry(
                code=str(item.get("rxnorm") or item["display"]),
                display=item["display"],
                metadata=metadata,
            )
            _store(entry)

    category_groups: Dict[str, List[TerminologyEntry]] = {}
    for entry in allergens.values():
        category = entry.metadata.get("category", "environment")
        category_groups.setdefault(category, []).append(entry)

    for bucket in category_groups.values():
        bucket.sort(key=lambda item: item.display)

    entries: List[TerminologyEntry] = []
    if max_allergens and len(allergens) > max_allergens:
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
        entries = selected
    else:
        for category in sorted(category_groups.keys()):
            entries.extend(category_groups[category])

    if max_allergens:
        required_names = critical_fallbacks

        def _fallback_entry(name: str) -> Optional[TerminologyEntry]:
            for item in FALLBACK_ALLERGEN_TERMS:
                if item["display"].lower() == name:
                    metadata = {
                        "category": item.get("category", "fallback"),
                        "unii": item.get("unii", ""),
                        "snomed_code": item.get("snomed", ""),
                    }
                    if item.get("rxnorm"):
                        metadata["rxnorm_name"] = item["display"]
                    return TerminologyEntry(
                        code=str(item.get("rxnorm") or item["display"]),
                        display=item["display"],
                        metadata=metadata,
                    )
            return None

        present = {entry.display.lower() for entry in entries}
        for name in required_names:
            if name not in present:
                entry = _fallback_entry(name)
                if entry:
                    entries.append(entry)
                    present.add(name)

        if max_allergens and len(entries) > max_allergens:
            while len(entries) > max_allergens:
                removed = False
                for idx, entry in enumerate(entries):
                    if entry.display.lower() not in required_names:
                        entries.pop(idx)
                        removed = True
                        break
                if not removed:
                    entries = entries[:max_allergens]
                    break

    return entries


def load_medication_entries(
    root: Optional[str] = None,
) -> List[TerminologyEntry]:
    frame = _load_rxnorm_frame(root)
    if frame is None or frame.is_empty():
        return []

    frame = frame.with_columns(
        pl.col("rxnorm_cui").cast(pl.Utf8),
        pl.col("ingredient_name").str.strip_chars()
    )

    lowercase_name = pl.col("ingredient_name").str.to_lowercase()
    entries: Dict[str, TerminologyEntry] = {}

    def _find_row(keywords: List[str]) -> Optional[Dict[str, Any]]:
        expr = None
        for keyword in keywords:
            keyword_lower = keyword.lower()
            condition = lowercase_name.str.contains(keyword_lower)
            expr = condition if expr is None else expr | condition
        matches = frame.filter(expr) if expr is not None else None
        if matches is None or matches.is_empty():
            for keyword in keywords:
                exact_matches = frame.filter(lowercase_name == keyword.lower())
                if not exact_matches.is_empty():
                    matches = exact_matches
                    break
        if matches is None or matches.is_empty():
            return None
        return matches.row(0, named=True)

    for item in CURATED_MEDICATIONS:
        display = item["display"]
        keywords = item.get("keywords") or [display]
        row = _find_row(keywords)
        metadata: Dict[str, str] = {
            "therapeutic_class": item.get("therapeutic_class", ""),
        }
        code = display
        if row:
            code = str(row.get("rxnorm_cui") or display)
            metadata["rxnorm_name"] = row.get("ingredient_name", display)
            if row.get("ndc_example"):
                metadata["ndc_example"] = str(row["ndc_example"])
            if row.get("ncbi_url"):
                metadata["ncbi_url"] = str(row["ncbi_url"])
        metadata["aliases"] = [display, display.replace(" ", "_")]
        entries[display] = TerminologyEntry(code=code, display=display, metadata=metadata)

    return list(entries.values())


def load_lab_test_entries(root: Optional[str] = None) -> List[Dict[str, Any]]:
    path = _resolve_path("loinc/loinc_full.csv", root)
    frame = None
    if path.exists():
        frame = pl.read_csv(path)
        frame = frame.with_columns(
            pl.col("loinc_code").cast(pl.Utf8),
            pl.col("long_common_name").str.strip_chars(),
        )
    entries: List[Dict[str, Any]] = []

    for test in CURATED_LAB_TESTS:
        entry = test.copy()
        loinc_code = test.get("loinc")
        if frame is not None and loinc_code:
            match = frame.filter(pl.col("loinc_code") == loinc_code)
            if not match.is_empty():
                row = match.row(0, named=True)
                entry.setdefault("long_name", row.get("long_common_name"))
        entries.append(entry)

    return entries


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
    "load_snomed_icd10_crosswalk",
    "load_rxnorm_medications",
    "load_vsac_value_sets",
    "load_umls_concepts",
    "filter_by_code",
    "search_by_term",
]
