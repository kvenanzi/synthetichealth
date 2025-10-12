#!/usr/bin/env python3
"""Monte Carlo validation for module-driven outputs.

Runs the synthetic generator multiple times against a scenario/module combination,
aggregates counts, and asserts that required resources land in expected ranges.

Usage example:
    python tools/module_monte_carlo_check.py --scenario sepsis_survivorship \
        --module sepsis_survivorship --num-records 50 --iterations 20
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import shutil

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "monte_carlo_validation"


def run_generator(
    *,
    scenario: Optional[str],
    modules: List[str],
    num_records: int,
    seed: Optional[int],
    iteration: int,
    output_dir: Path,
    extra_args: Optional[List[str]] = None,
) -> Path:
    run_dir = output_dir / f"run_{iteration:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "src.core.synthetic_patient_generator",
        "--num-records",
        str(num_records),
        "--output-dir",
        str(run_dir),
        "--output-format",
        "csv",
    ]
    if scenario:
        cmd.extend(["--scenario", scenario])
    for module in modules:
        cmd.extend(["--module", module])
    if seed is not None:
        cmd.extend(["--seed", str(seed + iteration)])
    if extra_args:
        cmd.extend(extra_args)

    subprocess.run(cmd, check=True)
    return run_dir


def load_csv(path: Path) -> pl.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        return pl.read_csv(path)
    except pl.exceptions.ComputeError:
        # fall back to treating value columns as strings when mixed units appear
        return pl.read_csv(path, schema_overrides={"value": pl.Utf8})


def evaluate_counts(run_dirs: List[Path]) -> Dict[str, pl.DataFrame]:
    summaries = []
    for run_dir in run_dirs:
        encounters = load_csv(run_dir / "encounters.csv")
        conditions = load_csv(run_dir / "conditions.csv")
        medications = load_csv(run_dir / "medications.csv")
        observations = load_csv(run_dir / "observations.csv")

        summaries.append(
            {
                "run": run_dir.name,
                "encounters": encounters.shape[0],
                "conditions": conditions.shape[0],
                "medications": medications.shape[0],
                "observations": observations.shape[0],
            }
        )

    df = pl.DataFrame(summaries)
    metrics = ["encounters", "conditions", "medications", "observations"]
    exprs = []
    for metric in metrics:
        col = pl.col(metric)
        exprs.extend(
            [
                col.mean().alias(f"{metric}_mean"),
                col.std(ddof=0).alias(f"{metric}_std"),
                col.min().alias(f"{metric}_min"),
                col.max().alias(f"{metric}_max"),
            ]
        )
    stats = df.select(*exprs)
    return {"runs": df, "stats": stats}


def evaluate_required_codes(run_dirs: List[Path], *, required_loinc: List[str], required_icd10: List[str]) -> Dict[str, List[str]]:
    missing_loinc_runs: List[str] = []
    missing_icd_runs: List[str] = []

    for run_dir in run_dirs:
        observations = load_csv(run_dir / "observations.csv")
        conditions = load_csv(run_dir / "conditions.csv")

        loinc_present = set(observations["loinc_code"].drop_nulls())
        icd_present = set(conditions["icd10_code"].drop_nulls())

        if not set(required_loinc).issubset(loinc_present):
            missing_loinc_runs.append(run_dir.name)
        if not set(required_icd10).issubset(icd_present):
            missing_icd_runs.append(run_dir.name)

    return {"loinc": missing_loinc_runs, "icd10": missing_icd_runs}


def main() -> int:
    parser = argparse.ArgumentParser(description="Monte Carlo validation for modules")
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--module", action="append", dest="modules", default=None)
    parser.add_argument("--num-records", type=int, default=50)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--required-loinc", action="append", default=None)
    parser.add_argument("--required-icd10", action="append", default=None)
    parser.add_argument("--max-med-std", type=float, default=0.25, help="Allowable coefficient of variation for medications" )
    parser.add_argument("--skip-fhir", action="store_true", help="Skip FHIR bundle export during generation")
    parser.add_argument("--skip-hl7", action="store_true", help="Skip HL7 export during generation")
    parser.add_argument("--skip-vista", action="store_true", help="Skip VistA MUMPS export during generation")
    parser.add_argument("--skip-report", action="store_true", help="Skip textual summary report during generation")

    args = parser.parse_args()
    modules = args.modules or []
    if not modules and not args.scenario:
        parser.error("Provide --module and/or --scenario")

    args.output_root.mkdir(parents=True, exist_ok=True)

    run_dirs: List[Path] = []
    try:
        for i in range(args.iterations):
            extra_args: List[str] = []
            if args.skip_fhir:
                extra_args.append("--skip-fhir")
            if args.skip_hl7:
                extra_args.append("--skip-hl7")
            if args.skip_vista:
                extra_args.append("--skip-vista")
            if args.skip_report:
                extra_args.append("--skip-report")

            run_dir = run_generator(
                scenario=args.scenario,
                modules=modules,
                num_records=args.num_records,
                seed=args.seed,
                iteration=i,
                output_dir=args.output_root,
                extra_args=extra_args,
            )
            run_dirs.append(run_dir)

        results = evaluate_counts(run_dirs)
        stats = results["stats"]
        runs_df = results["runs"]

        if stats["medications_mean"][0] > 0:
            coeff_var = stats["medications_std"][0] / stats["medications_mean"][0]
        else:
            coeff_var = 0.0
        if coeff_var > args.max_med_std:
            raise SystemExit(f"Medication count coefficient of variation {coeff_var:.2f} exceeds threshold {args.max_med_std}")

        summary_path = args.output_root / "monte_carlo_summary.parquet"
        stats.write_parquet(summary_path)
        runs_df.write_csv(args.output_root / "monte_carlo_runs.csv")

        required_loinc = args.required_loinc or []
        required_icd10 = args.required_icd10 or []
        if required_loinc or required_icd10:
            missing = evaluate_required_codes(run_dirs, required_loinc=required_loinc, required_icd10=required_icd10)
            if missing["loinc"]:
                raise SystemExit(f"Missing required LOINC codes in runs: {missing['loinc']}")
            if missing["icd10"]:
                raise SystemExit(f"Missing required ICD-10 codes in runs: {missing['icd10']}")

        print("Monte Carlo validation completed. Stats written to", summary_path)
    finally:
        for run in run_dirs:
            if run.exists():
                shutil.rmtree(run, ignore_errors=True)
        if args.output_root.exists() and not any(args.output_root.iterdir()):
            args.output_root.rmdir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
