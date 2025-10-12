#!/usr/bin/env python3
"""Evaluate module-specific KPI specifications using Monte Carlo generation outputs."""

from __future__ import annotations

import argparse
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import yaml
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.module_monte_carlo_check import run_generator, load_csv  # noqa: E402

DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "output" / "module_kpi_validation"


@dataclass
class KPIResult:
    name: str
    metric: str
    target: Any
    actual: Any
    tolerance: float
    within_tolerance: bool


def load_kpi_spec(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not payload.get("jobs"):
        raise ValueError(f"KPI spec at {path} is missing 'jobs'")
    return payload


def _concat_frames(run_dirs: Sequence[Path], filename: str) -> pl.DataFrame:
    frames: List[pl.DataFrame] = []
    for run_dir in run_dirs:
        path = run_dir / f"{filename}.csv"
        if not path.exists():
            continue
        frames.append(load_csv(path))
    if not frames:
        return pl.DataFrame()
    if len(frames) == 1:
        return frames[0]
    return pl.concat(frames, how="diagonal_relaxed")


def load_run_data(run_dirs: Sequence[Path]) -> Dict[str, pl.DataFrame]:
    data = {
        "patients": _concat_frames(run_dirs, "patients"),
        "observations": _concat_frames(run_dirs, "observations"),
        "medications": _concat_frames(run_dirs, "medications"),
        "attributes": _concat_frames(run_dirs, "module_attributes"),
    }
    return data


def compute_proportion_split(kpi: Dict[str, Any], data: Dict[str, pl.DataFrame]) -> KPIResult:
    attribute_groups = kpi.get("groups", [])
    if not attribute_groups:
        raise ValueError(f"KPI '{kpi.get('name')}' missing groups definition")
    attributes_df = data.get("attributes", pl.DataFrame())
    attribute_name = attribute_groups[0]["attribute"]
    relevant = attributes_df.filter(pl.col("attribute") == attribute_name)
    if not relevant.is_empty():
        relevant = relevant.unique(["patient_id", "attribute"], keep="last")
    total = relevant.height
    actual_split: Dict[str, float] = {}
    for group in attribute_groups:
        value = group["value"]
        count = (
            relevant.filter(pl.col("value") == value).height
            if total
            else 0
        )
        actual_split[value] = count / total if total else 0.0

    targets: Dict[str, float] = kpi.get("targets", {})
    tolerance = float(kpi.get("tolerance_abs", 0.0))
    within = True
    for label, target_value in targets.items():
        actual = actual_split.get(label, 0.0)
        if math.fabs(actual - target_value) > tolerance:
            within = False
    return KPIResult(
        name=kpi.get("name", attribute_name),
        metric="proportion_split",
        target=targets,
        actual=actual_split,
        tolerance=tolerance,
        within_tolerance=within,
    )


def _patient_count(data: Dict[str, pl.DataFrame]) -> int:
    patients = data.get("patients", pl.DataFrame())
    if patients.is_empty():
        return 0
    if "patient_id" in patients.columns:
        return patients["patient_id"].n_unique()
    return patients.height


def compute_event_rate_per_year(kpi: Dict[str, Any], data: Dict[str, pl.DataFrame]) -> KPIResult:
    event = kpi.get("event")
    if not event:
        raise ValueError(f"KPI '{kpi.get('name')}' missing 'event'")
    observations = data.get("observations", pl.DataFrame())
    events = observations.filter(pl.col("panel") == event).height if "panel" in observations.columns else 0
    patient_count = _patient_count(data)
    actual = events / patient_count if patient_count else 0.0
    target = float(kpi.get("target", 0.0))
    tolerance = float(kpi.get("tolerance_abs", 0.0))
    within = math.fabs(actual - target) <= tolerance
    return KPIResult(
        name=kpi.get("name", event),
        metric="event_rate_per_year",
        target=target,
        actual=actual,
        tolerance=tolerance,
        within_tolerance=within,
    )


def compute_ed_visits_per_100_ptyears(kpi: Dict[str, Any], data: Dict[str, pl.DataFrame]) -> KPIResult:
    event = kpi.get("event")
    observations = data.get("observations", pl.DataFrame())
    events = observations.filter(pl.col("panel") == event).height if "panel" in observations.columns else 0
    patient_count = _patient_count(data)
    actual = (events / patient_count * 100.0) if patient_count else 0.0
    target = float(kpi.get("target", 0.0))
    tolerance = float(kpi.get("tolerance_abs", 0.0))
    within = math.fabs(actual - target) <= tolerance
    return KPIResult(
        name=kpi.get("name", event),
        metric="ed_visits_per_100_ptyears",
        target=target,
        actual=actual,
        tolerance=tolerance,
        within_tolerance=within,
    )


def compute_rescue_therapy_fraction(kpi: Dict[str, Any], data: Dict[str, pl.DataFrame]) -> KPIResult:
    observations = data.get("observations", pl.DataFrame())
    medications = data.get("medications", pl.DataFrame())
    events = observations.filter(pl.col("panel") == "copd_exacerbation").height if "panel" in observations.columns else 0
    antibiotics = 0
    if not medications.is_empty() and "therapy_category" in medications.columns:
        antibiotics = medications.filter(pl.col("therapy_category") == "antibiotic").height
    actual = antibiotics / events if events else 0.0
    target = float(kpi.get("target", 0.0))
    tolerance = float(kpi.get("tolerance_abs", 0.0))
    within = math.fabs(actual - target) <= tolerance
    return KPIResult(
        name=kpi.get("name", "rescue_therapy_fraction"),
        metric="rescue_therapy_fraction",
        target=target,
        actual=actual,
        tolerance=tolerance,
        within_tolerance=within,
    )


METRIC_HANDLERS = {
    "proportion_split": compute_proportion_split,
    "event_rate_per_year": compute_event_rate_per_year,
    "ed_visits_per_100_ptyears": compute_ed_visits_per_100_ptyears,
    "rescue_therapy_fraction": compute_rescue_therapy_fraction,
}

__all__ = [
    "compute_proportion_split",
    "compute_event_rate_per_year",
    "compute_ed_visits_per_100_ptyears",
    "compute_rescue_therapy_fraction",
    "evaluate_kpis",
    "load_kpi_spec",
]


def evaluate_kpis(run_dirs: Sequence[Path], kpis: Sequence[Dict[str, Any]]) -> List[KPIResult]:
    data = load_run_data(run_dirs)
    results: List[KPIResult] = []
    for kpi in kpis:
        metric = kpi.get("metric")
        handler = METRIC_HANDLERS.get(metric)
        if handler is None:
            raise ValueError(f"Unsupported KPI metric '{metric}'")
        results.append(handler(kpi, data))
    return results


def run_kpi_jobs(spec: Dict[str, Any], *, output_root: Path) -> List[KPIResult]:
    results: List[KPIResult] = []
    module_name = spec.get("module", "module")
    jobs = spec.get("jobs", [])
    for index, job in enumerate(jobs):
        job_root = output_root / f"{module_name}_{index:02d}"
        job_root.mkdir(parents=True, exist_ok=True)
        run_dirs: List[Path] = []
        try:
            iterations = int(job.get("iterations", 1))
            for i in range(iterations):
                run_dir = run_generator(
                    scenario=job.get("scenario"),
                    modules=job.get("modules", []),
                    num_records=int(job.get("num_records", 100)),
                    seed=job.get("seed"),
                    iteration=i,
                    output_dir=job_root,
                )
                run_dirs.append(run_dir)
            results.extend(evaluate_kpis(run_dirs, job.get("kpis", [])))
        finally:
            shutil.rmtree(job_root, ignore_errors=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate module KPI specifications.")
    parser.add_argument(
        "--spec",
        action="append",
        dest="specs",
        required=True,
        help="Path to a KPI specification YAML file (can be provided multiple times).",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory used for intermediate Monte Carlo outputs.",
    )
    args = parser.parse_args()

    overall_ok = True
    output_root: Path = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        for spec_path_str in args.specs:
            spec_path = Path(spec_path_str)
            spec = load_kpi_spec(spec_path)
            print(f"Evaluating KPI spec: {spec_path}")
            kpi_results = run_kpi_jobs(spec, output_root=output_root)
            for result in kpi_results:
                status = "PASS" if result.within_tolerance else "FAIL"
                print(
                    f"  [{status}] {result.name} ({result.metric}) "
                    f"actual={result.actual} target={result.target} tol={result.tolerance}"
                )
                if not result.within_tolerance:
                    overall_ok = False
    finally:
        shutil.rmtree(output_root, ignore_errors=True)

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
