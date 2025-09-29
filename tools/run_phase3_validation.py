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
        "num_records": "20",
        "iterations": "4",
        "required_loinc": ["6690-2", "1975-2"],
        "required_icd10": ["A41.9"],
    },
    {
        "scenario": "hiv_prep",
        "num_records": "20",
        "iterations": "4",
        "required_loinc": ["25836-8"],
        "required_icd10": ["B20", "Z20.6"],
    },
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
            "--scenario",
            job["scenario"],
            "--num-records",
            job["num_records"],
            "--iterations",
            job["iterations"],
            "--max-med-std",
            "0.5",
        ]
        for code in job["required_loinc"]:
            cmd.extend(["--required-loinc", code])
        for code in job["required_icd10"]:
            cmd.extend(["--required-icd10", code])
        run(cmd)
    print("Phase 3 validation suite completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
