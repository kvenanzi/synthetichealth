#!/usr/bin/env python3
"""Convenience harness for Phase 3 validation checks.

Runs the module linter and a small Monte Carlo sweep across representative
scenarios so contributors and CI can execute a single command.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

LINTER_CMD = [PYTHON, "tools/module_linter.py", "--modules-root", "modules", "--all"]

MONTE_CARLO_JOBS = [
    {
        "scenario": "sepsis_survivorship",
        "modules": [],
        "num_records": "10",
        "iterations": "2",
        "required_loinc": ["6690-2", "1975-2"],
        "required_icd10": ["A41.9"],
        "max_med_std": "0.75",
    },
    {
        "scenario": "hiv_prep",
        "modules": [],
        "num_records": "10",
        "iterations": "2",
        "required_loinc": ["25836-8"],
        "required_icd10": ["B20", "Z20.6"],
        "max_med_std": "0.75",
    },
    {
        "scenario": None,
        "modules": ["adult_primary_care_wellness"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["13457-7", "2093-3"],
        "required_icd10": ["Z00.00", "E78.2"],
        "max_med_std": "0.6",
    },
    {
        "scenario": None,
        "modules": ["pregnancy_loss_support"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["44249-1", "718-7"],
        "required_icd10": ["O03.9", "F43.21"],
        "max_med_std": "0.6",
    },
    {
        "scenario": None,
        "modules": ["asthma_v2"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["2019-8", "44261-6"],
        "required_icd10": ["J45.40"],
        "max_med_std": "0.7",
    },
    {
        "scenario": None,
        "modules": ["copd_v2"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["19926-5", "59408-5"],
        "required_icd10": ["J44.9"],
        "max_med_std": "0.7",
    },
    {
        "scenario": None,
        "modules": ["type2_diabetes_management"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["4548-4", "26515-7"],
        "required_icd10": ["E11.9"],
        "max_med_std": "0.7",
    },
    {
        "scenario": None,
        "modules": ["mental_health_integrated_care", "geriatric_polypharmacy"],
        "num_records": "8",
        "iterations": "2",
        "required_loinc": ["44261-6", "69730-0"],
        "required_icd10": ["F33.1", "M17.11"],
        "max_med_std": "0.7",
    },
]

KPI_SPECS = [
    PROJECT_ROOT / "validation" / "module_kpis" / "asthma.yaml",
    PROJECT_ROOT / "validation" / "module_kpis" / "copd.yaml",
]

def run(cmd: list[str]) -> None:
    print("→", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    run(LINTER_CMD)

    for job in MONTE_CARLO_JOBS:
        cmd = [
            PYTHON,
            "tools/module_monte_carlo_check.py",
        ]
        if job["scenario"]:
            cmd.extend(["--scenario", job["scenario"]])
        for module in job.get("modules", []):
            cmd.extend(["--module", module])
        cmd.extend(
            [
                "--num-records",
                job["num_records"],
                "--iterations",
                job["iterations"],
                "--max-med-std",
                job.get("max_med_std", "0.5"),
            ]
        )
        for code in job["required_loinc"]:
            cmd.extend(["--required-loinc", code])
        for code in job["required_icd10"]:
            cmd.extend(["--required-icd10", code])
        run(cmd)
    kpi_cmd = [PYTHON, "tools/module_kpi_validator.py"]
    for spec in KPI_SPECS:
        kpi_cmd.extend(["--spec", str(spec)])
    run(kpi_cmd)
    print("Phase 3 validation suite completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
