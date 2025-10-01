"""Normalize SNOMED CT snapshot tables into a loader-friendly CSV.

Usage (run inside the project virtualenv):
    python3 tools/import_snomed.py \
        --concept data/terminology/snomed/raw/.../Snapshot/Terminology/sct2_Concept_Snapshot_US1000124_20250901.txt \
        --description data/terminology/snomed/raw/.../Snapshot/Terminology/sct2_Description_Snapshot-en_US1000124_20250901.txt \
        --output data/terminology/snomed/snomed_full.csv

The script joins active concepts with their English preferred terms and exports
a CSV containing the SNOMED ID, PT name, definition status, and a lookup URL,
mirroring the seed schema used by our loaders.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import polars as pl

DEFAULT_CONCEPT_PATH = Path("data/terminology/snomed/raw/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z/Snapshot/Terminology/sct2_Concept_Snapshot_US1000124_20250901.txt")
DEFAULT_DESCRIPTION_PATH = Path("data/terminology/snomed/raw/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z/Snapshot/Terminology/sct2_Description_Snapshot-en_US1000124_20250901.txt")
DEFAULT_OUTPUT_PATH = Path("data/terminology/snomed/snomed_full.csv")

# SCTIDs used in the description file
FSN_TYPE = "900000000000003001"
PREFERRED_TYPE = "900000000000013009"
CASE_INSENSITIVE = "900000000000448009"


def normalize_snomed(concept_path: Path, description_path: Path, output_path: Path) -> None:
    if not concept_path.exists():
        raise FileNotFoundError(f"Concept snapshot not found: {concept_path}")
    if not description_path.exists():
        raise FileNotFoundError(f"Description snapshot not found: {description_path}")

    concepts = pl.read_csv(concept_path, separator="\t", quote_char=None)
    concepts = concepts.with_columns([
        pl.col("id").cast(pl.Utf8),
        pl.col("definitionStatusId").cast(pl.Utf8),
    ])
    concepts = concepts.filter((pl.col("active") == 1))

    # The US Managed Service snapshots occasionally ship description rows with
    # unbalanced quotes (for example a value such as "Morning after pill without
    # the closing quote). When the parser treats the file as a quoted TSV this
    # causes Polars to see a single row that spans the remainder of the file and
    # emit ``CSV malformed`` errors. Disabling quote handling keeps those rows
    # well-formed and we trim any stray quote characters afterwards.
    descriptions = pl.read_csv(description_path, separator="\t", quote_char=None)
    descriptions = descriptions.with_columns([
        pl.col("conceptId").cast(pl.Utf8),
        pl.col("typeId").cast(pl.Utf8),
        pl.col("caseSignificanceId").cast(pl.Utf8),
        pl.col("term").cast(pl.Utf8).str.strip_chars('"'),
    ])
    descriptions = descriptions.filter((pl.col("active") == 1))

    preferred_terms = descriptions.filter(
        (pl.col("typeId") == PREFERRED_TYPE) & (pl.col("caseSignificanceId") == CASE_INSENSITIVE)
    ).select(
        pl.col("conceptId"),
        pl.col("term").alias("pt_name"),
    )

    joined = concepts.join(preferred_terms, left_on="id", right_on="conceptId", how="left")

    joined = joined.select(
        pl.col("id").alias("snomed_id"),
        pl.col("pt_name"),
        pl.col("definitionStatusId").alias("definition_status_id"),
        pl.concat_str(
            [
                pl.lit("https://browser.ihtsdotools.org/?perspective=full&conceptId="),
                pl.col("id"),
            ]
        ).alias("ncbi_url"),
    )
    joined = joined.unique(subset="snomed_id")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joined.write_csv(output_path)
    print(f"Wrote normalized SNOMED table: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize SNOMED CT snapshot tables")
    parser.add_argument("--concept", type=Path, default=DEFAULT_CONCEPT_PATH)
    parser.add_argument("--description", type=Path, default=DEFAULT_DESCRIPTION_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalize_snomed(args.concept, args.description, args.output)


if __name__ == "__main__":
    main()
