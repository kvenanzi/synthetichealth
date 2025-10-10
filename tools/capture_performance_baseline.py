#!/usr/bin/env python3
"""Capture baseline generator performance metrics for regression comparison.

This helper runs the lifecycle generator against a curated set of scenarios
and modules, measures wall-clock execution time, and persists a summary JSON
payload (including throughput and environment details). Downstream workflows
can diff the resulting metrics file to detect unexpected performance drift.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


@dataclass
class PerformanceJob:
    name: str
    num_records: int
    scenario: Optional[str] = None
    modules: Optional[List[str]] = None

    def assemble_command(self, output_dir: Path) -> List[str]:
        cmd = [
            PYTHON,
            "-m",
            "src.core.synthetic_patient_generator",
            "--num-records",
            str(self.num_records),
            "--output-dir",
            str(output_dir),
            "--csv",
        ]
        if self.scenario:
            cmd.extend(["--scenario", self.scenario])
        for module in self.modules or []:
            cmd.extend(["--module", module])
        return cmd


def build_default_jobs(num_records: int) -> List[PerformanceJob]:
    """Return the default job matrix for baseline measurements."""
    return [
        PerformanceJob(
            name="multi_module_combo",
            num_records=num_records,
            scenario="sepsis_survivorship",
            modules=[
                "cardiometabolic_intensive",
                "adult_primary_care_wellness",
                "pregnancy_loss_support",
            ],
        ),
    ]


def git_revision() -> Optional[str]:
    try:
        rev = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
        )
        return rev.decode().strip()
    except Exception:
        return None


def capture_metrics(jobs: List[PerformanceJob]) -> Dict[str, object]:
    results = []
    for job in jobs:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = job.assemble_command(Path(tmpdir))
            start = time.perf_counter()
            subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            elapsed = time.perf_counter() - start
        records_per_second = job.num_records / elapsed if elapsed > 0 else 0.0
        results.append(
            {
                "job": job.name,
                "scenario": job.scenario,
                "modules": job.modules or [],
                "num_records": job.num_records,
                "elapsed_seconds": round(elapsed, 4),
                "records_per_second": round(records_per_second, 2),
            }
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_revision": git_revision(),
        "jobs": results,
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture baseline generator performance metrics.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "performance" / "baseline_metrics.json",
        help="Path to write the metrics JSON file (default: performance/baseline_metrics.json)",
    )
    parser.add_argument(
        "--num-records",
        type=int,
        default=8,
        help="Number of records to generate for the baseline job (default: 8)",
    )
    parser.add_argument(
        "--jobs-config",
        type=Path,
        default=None,
        help="Optional JSON file describing custom jobs.",
    )
    return parser.parse_args()


def load_jobs(args: argparse.Namespace) -> List[PerformanceJob]:
    if not args.jobs_config:
        return build_default_jobs(args.num_records)

    data = json.loads(Path(args.jobs_config).read_text())
    jobs = []
    for entry in data:
        jobs.append(
            PerformanceJob(
                name=entry["name"],
                num_records=int(entry.get("num_records", args.num_records)),
                scenario=entry.get("scenario"),
                modules=entry.get("modules"),
            )
        )
    return jobs


def main() -> int:
    args = parse_args()
    jobs = load_jobs(args)
    metrics = capture_metrics(jobs)

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2))

    print(f"Baseline metrics captured for {len(jobs)} jobs → {output_path}")
    for job in metrics["jobs"]:
        print(
            f"  - {job['job']}: {job['elapsed_seconds']}s "
            f"({job['records_per_second']} rec/s, n={job['num_records']})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
