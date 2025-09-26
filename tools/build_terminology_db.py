"""Build a DuckDB database containing normalized terminology tables.

Usage (run inside the project virtualenv):
    python3 tools/build_terminology_db.py \
        --root data/terminology \
        --output data/terminology/terminology.duckdb \
        --force

The script looks for normalized CSV exports (``*_full.csv``) and falls back to
the seed CSVs when necessary. Resulting tables are:
    - icd10 (code, descriptions, hierarchy metadata)
    - loinc (laboratory observation concepts)
    - snomed (preferred terms)
    - rxnorm (medication concepts)
    - vsac_value_sets (VSAC membership + metadata; empty when no exports)
    - umls_concepts (UMLS CUIs with preferred terms; empty when no exports)
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict

import duckdb
import pandas as pd
import polars as pl

DEFAULT_ROOT = Path("data/terminology")
DEFAULT_DB_PATH = DEFAULT_ROOT / "terminology.duckdb"


def _ensure_columns(frame: pl.DataFrame, required: Dict[str, str]) -> pl.DataFrame:
    columns = frame.columns
    for name, default in required.items():
        if name not in columns:
            frame = frame.with_columns(pl.lit(default).alias(name))
    return frame.select(list(required.keys()))


def _empty_frame(required: Dict[str, str]) -> pl.DataFrame:
    return pl.DataFrame({name: pl.Series(name, [], dtype=pl.Utf8) for name in required})


def load_icd10(root: Path) -> pl.DataFrame:
    normalized = root / "icd10/icd10_full.csv"
    seed = root / "icd10/icd10_conditions.csv"
    if normalized.exists():
        df = pl.read_csv(normalized)
        required = {
            "code": "",
            "description": "",
            "short_description": "",
            "level": "",
            "order": "",
            "chapter": "",
            "ncbi_url": "",
        }
        df = _ensure_columns(df, required)
    else:
        df = pl.read_csv(seed)
        df = df.with_columns(
            pl.lit("0").alias("level"),
            pl.lit("").alias("short_description"),
            pl.col("description").alias("order"),
        )
        df = df.select(
            pl.col("code"),
            pl.col("description"),
            pl.col("description").alias("short_description"),
            pl.col("level"),
            pl.col("order"),
            pl.col("chapter"),
            pl.col("ncbi_url"),
        )
    return df


def load_loinc(root: Path) -> pl.DataFrame:
    normalized = root / "loinc/loinc_full.csv"
    seed = root / "loinc/loinc_labs.csv"
    if normalized.exists():
        df = pl.read_csv(normalized)
        required = {
            "loinc_code": "",
            "long_common_name": "",
            "component": "",
            "property": "",
            "system": "",
            "loinc_class": "",
            "ncbi_url": "",
        }
        df = _ensure_columns(df, required)
    else:
        df = pl.read_csv(seed)
        df = df.with_columns(pl.lit("").alias("loinc_class"))
        df = df.select(
            "loinc_code",
            "long_common_name",
            "component",
            "property",
            "system",
            "loinc_class",
            "ncbi_url",
        )
    return df


def load_snomed(root: Path) -> pl.DataFrame:
    normalized = root / "snomed/snomed_full.csv"
    seed = root / "snomed/snomed_conditions.csv"
    if normalized.exists():
        df = pl.read_csv(normalized)
        required = {
            "snomed_id": "",
            "pt_name": "",
            "definition_status_id": "",
            "icd10_mapping": "",
            "ncbi_url": "",
        }
        df = _ensure_columns(df, required)
    else:
        df = pl.read_csv(seed)
        df = df.with_columns(pl.lit("").alias("definition_status_id"))
        df = df.select(
            "snomed_id",
            "pt_name",
            "definition_status_id",
            "icd10_mapping",
            "ncbi_url",
        )
    return df


def load_rxnorm(root: Path) -> pl.DataFrame:
    normalized = root / "rxnorm/rxnorm_full.csv"
    seed = root / "rxnorm/rxnorm_medications.csv"
    if normalized.exists():
        df = pl.read_csv(normalized)
        required = {
            "rxnorm_cui": "",
            "tty": "",
            "ingredient_name": "",
            "source_code": "",
            "sab": "",
            "ndc_example": "",
            "ncbi_url": "",
        }
        df = _ensure_columns(df, required)
    else:
        df = pl.read_csv(seed)
        df = df.with_columns(
            pl.lit("").alias("source_code"),
            pl.lit("RXNORM").alias("sab"),
        )
        df = df.select(
            "rxnorm_cui",
            "tty",
            "ingredient_name",
            "source_code",
            "sab",
            "ndc_example",
            "ncbi_url",
        )
    return df


def load_vsac_value_sets(root: Path) -> pl.DataFrame:
    normalized = root / "vsac/vsac_value_sets_full.csv"
    seed = root / "vsac/vsac_value_sets.csv"
    required = {
        "value_set_oid": "",
        "value_set_name": "",
        "value_set_version": "",
        "release_date": "",
        "clinical_focus": "",
        "concept_status": "",
        "code": "",
        "code_system": "",
        "code_system_version": "",
        "display_name": "",
    }
    if normalized.exists():
        df = pl.read_csv(normalized)
        return _ensure_columns(df, required)
    if seed.exists():
        df = pl.read_csv(seed)
        return _ensure_columns(df, required)
    return _empty_frame(required)


def load_umls_concepts(root: Path) -> pl.DataFrame:
    normalized = root / "umls/umls_concepts_full.csv"
    seed = root / "umls/umls_concepts.csv"
    required = {
        "cui": "",
        "preferred_name": "",
        "semantic_type": "",
        "tui": "",
        "sab": "",
        "code": "",
        "tty": "",
        "aui": "",
        "source_atom_name": "",
    }
    if normalized.exists():
        df = pl.read_csv(normalized)
        return _ensure_columns(df, required)
    if seed.exists():
        df = pl.read_csv(seed)
        return _ensure_columns(df, required)
    return _empty_frame(required)


LOADERS = {
    "icd10": load_icd10,
    "loinc": load_loinc,
    "snomed": load_snomed,
    "rxnorm": load_rxnorm,
    "vsac_value_sets": load_vsac_value_sets,
    "umls_concepts": load_umls_concepts,
}


def build_database(root: Path, output: Path, *, force: bool = False) -> None:
    tables = {name: loader(root) for name, loader in LOADERS.items()}
    if output.exists():
        if not force:
            raise SystemExit(
                f"{output} already exists. Re-run with --force to overwrite the current warehouse."
            )
        output.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(output))
    try:
        for name, frame in tables.items():
            pandas_df = pd.DataFrame(frame.to_dict(as_series=False))
            con.register(name, pandas_df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM {name}")
            con.unregister(name)
        con.commit()
    finally:
        con.close()
    print(f"DuckDB terminology warehouse saved to {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build DuckDB terminology warehouse")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Terminology directory root")
    parser.add_argument("--output", type=Path, default=DEFAULT_DB_PATH, help="Output DuckDB path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the existing DuckDB file when it already exists",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_database(args.root, args.output, force=args.force)


if __name__ == "__main__":
    main()
