"""Normalize official ICD-10-CM tabular/order files for the terminology loader.

Usage (run inside the project virtualenv):
    python3 tools/import_icd10.py \
        --raw data/terminology/icd10/raw/icd10cm-order-2026.txt \
        --output data/terminology/icd10/icd10_full.csv

The script expects the fixed-width order file published by CDC/NCHS and
produces a CSV containing the ICD code, long and short descriptions, hierarchy
level, and a direct link to the CDC ICD-10-CM lookup tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import polars as pl

DEFAULT_RAW_PATH = Path("data/terminology/icd10/raw/icd10cm-order-2026.txt")
DEFAULT_OUTPUT_PATH = Path("data/terminology/icd10/icd10_full.csv")


def _parse_line(line: str) -> dict:
    order = line[0:5]
    code = line[6:13].strip()
    level = line[13:16].strip()
    short_desc = line[16:76].strip()
    long_desc = line[76:].strip()
    return {
        "order": order,
        "code": code,
        "level": level,
        "short_description": short_desc,
        "description": long_desc or short_desc,
        "chapter": "",  # reserved for future enrichment
        "ncbi_url": f"https://icd10cmtool.cdc.gov/?fy=2026&code={code}",
    }


def normalize_icd10(raw_path: Path, output_path: Path) -> None:
    if not raw_path.exists():
        raise FileNotFoundError(f"ICD-10 order file not found: {raw_path}")

    records: List[dict] = []
    with raw_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line or len(line) < 10:
                continue
            parsed = _parse_line(line)
            if parsed["code"]:
                records.append(parsed)

    if not records:
        raise ValueError("No ICD-10 records parsed from order file")

    df = pl.DataFrame(records)
    df.write_csv(output_path)
    print(f"Wrote normalized ICD-10 table: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize ICD-10-CM order file")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_PATH, help="Path to icd10cm-order-*.txt")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Destination CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalize_icd10(args.raw, args.output)


if __name__ == "__main__":
    main()
