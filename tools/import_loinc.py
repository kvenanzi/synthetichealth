"""Normalize official LOINC tables into the format consumed by the loader.

Usage (run inside the project virtualenv):
    python3 tools/import_loinc.py \
        --raw data/terminology/loinc/raw/LoincTable/Loinc.csv \
        --output data/terminology/loinc/loinc_full.csv

The script expects the standard LOINC CSV delivered in the official zip
archive and filters to ACTIVE concepts while retaining common fields used by
our generator. A `ncbi_url` column is appended pointing to the public LOINC
concept page (https://loinc.org/<code>/).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

DEFAULT_RAW_PATH = Path("data/terminology/loinc/raw/LoincTable/Loinc.csv")
DEFAULT_OUTPUT_PATH = Path("data/terminology/loinc/loinc_full.csv")


def normalize_loinc(raw_path: Path, output_path: Path) -> None:
    if not raw_path.exists():
        raise FileNotFoundError(f"LOINC source file not found: {raw_path}")

    columns = [
        "LOINC_NUM",
        "LONG_COMMON_NAME",
        "COMPONENT",
        "PROPERTY",
        "SYSTEM",
        "CLASS",
        "STATUS",
    ]

    df = pl.read_csv(raw_path, columns=columns)
    if "STATUS" in df.columns:
        df = df.filter(pl.col("STATUS") == "ACTIVE")

    df = df.with_columns(
        pl.col("LOINC_NUM").cast(str),
        pl.col("LONG_COMMON_NAME").cast(str),
        pl.col("COMPONENT").cast(str),
        pl.col("PROPERTY").cast(str),
        pl.col("SYSTEM").cast(str),
        pl.col("CLASS").cast(str),
    )

    df = df.with_columns(
        pl.concat_str([pl.lit("https://loinc.org/"), pl.col("LOINC_NUM")]).alias("ncbi_url")
    )

    df = df.select(
        pl.col("LOINC_NUM").alias("loinc_code"),
        pl.col("LONG_COMMON_NAME").alias("long_common_name"),
        pl.col("COMPONENT").alias("component"),
        pl.col("PROPERTY").alias("property"),
        pl.col("SYSTEM").alias("system"),
        pl.col("CLASS").alias("loinc_class"),
        pl.col("ncbi_url"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(output_path)
    print(f"Wrote normalized LOINC table: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize official LOINC tables")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_PATH, help="Path to Loinc.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Destination CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalize_loinc(args.raw, args.output)


if __name__ == "__main__":
    main()
