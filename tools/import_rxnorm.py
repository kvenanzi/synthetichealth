"""Normalize RxNorm release tables into a loader-friendly CSV.

Usage (run inside the project virtualenv):
    python3 tools/import_rxnorm.py \
        --rxnconso data/terminology/rxnorm/raw/rrf/RXNCONSO.RRF \
        --output data/terminology/rxnorm/rxnorm_full.csv

The script parses the RXNCONSO table, filters to active RxNorm terms, and
emits a CSV containing the RxCUI, term type (TTY), ingredient/description, and
an RxNav lookup URL. The loader will automatically prefer this file when it
exists.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import polars as pl

DEFAULT_RXNCONSO_PATH = Path("data/terminology/rxnorm/raw/rrf/RXNCONSO.RRF")
DEFAULT_OUTPUT_PATH = Path("data/terminology/rxnorm/rxnorm_full.csv")

RXNCONSO_COLUMNS = [
    "RXCUI",
    "LAT",
    "TS",
    "LUI",
    "STT",
    "SUI",
    "ISPREF",
    "RXAUI",
    "SAUI",
    "SCUI",
    "SDUI",
    "SAB",
    "TTY",
    "CODE",
    "STR",
    "SRL",
    "SUPPRESS",
    "CVF",
]

PREFERRED_TTYS = {"SCD", "SBD", "GPCK", "BPCK", "IN", "PIN", "MIN"}


def _parse_rxnconso(path: Path) -> List[dict]:
    records: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.rstrip("|").split("|")
            if len(parts) < len(RXNCONSO_COLUMNS):
                continue
            row = dict(zip(RXNCONSO_COLUMNS, parts))
            records.append(row)
    return records


def normalize_rxnorm(rxnconso_path: Path, output_path: Path) -> None:
    if not rxnconso_path.exists():
        raise FileNotFoundError(f"RXNCONSO file not found: {rxnconso_path}")

    rows = _parse_rxnconso(rxnconso_path)
    df = pl.DataFrame(rows)

    df = df.filter(
        (pl.col("SAB") == "RXNORM") &
        (pl.col("SUPPRESS") != "Y") &
        (pl.col("TTY").is_in(list(PREFERRED_TTYS)))
    )

    df = df.select(
        pl.col("RXCUI").alias("rxnorm_cui"),
        pl.col("TTY").alias("tty"),
        pl.col("STR").alias("ingredient_name"),
        pl.col("CODE").alias("source_code"),
        pl.col("SAB").alias("sab"),
        pl.lit("").alias("ndc_example"),
        pl.concat_str([pl.lit("https://rxnav.nlm.nih.gov/REST/rxcui/"), pl.col("RXCUI")]).alias("ncbi_url"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(output_path)
    print(f"Wrote normalized RxNorm table: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize RxNorm concepts")
    parser.add_argument("--rxnconso", type=Path, default=DEFAULT_RXNCONSO_PATH, help="Path to RXNCONSO.RRF")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Destination CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalize_rxnorm(args.rxnconso, args.output)


if __name__ == "__main__":
    main()
