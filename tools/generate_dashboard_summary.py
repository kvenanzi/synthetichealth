import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List

try:  # Prefer rich for human readable output but fall back silently if unavailable
    from rich.console import Console
    from rich.table import Table

    console: "Console | None" = Console()
except Exception:  # pragma: no cover - rich is an optional enhancement for CLI output
    console = None


def _average(values: Iterable[float]) -> float:
    data = list(values)
    return round(mean(data), 3) if data else 0.0


def _load_sdoh_profiles(patients_path: Path) -> Dict[str, float]:
    deprivation: List[float] = []
    access: List[float] = []
    support: List[float] = []
    sdoh_risk: List[float] = []
    care_gaps_counter: Counter[str] = Counter()
    transportation_modes: Counter[str] = Counter()
    language_preferences: Counter[str] = Counter()

    with patients_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            deprivation.append(float(row.get("community_deprivation_index", 0.0) or 0.0))
            access.append(float(row.get("access_to_care_score", 0.0) or 0.0))
            support.append(float(row.get("social_support_score", 0.0) or 0.0))
            sdoh_risk.append(float(row.get("sdoh_risk_score", 0.0) or 0.0))

            gaps = json.loads(row.get("sdoh_care_gaps", "[]"))
            for gap in gaps:
                care_gaps_counter[gap] += 1

            transportation = row.get("transportation_access")
            if transportation:
                transportation_modes[transportation] += 1

            language = row.get("preferred_language")
            if language:
                language_preferences[language] += 1

    total_patients = max(1, sum(transportation_modes.values()) or len(sdoh_risk) or 1)

    return {
        "average_sdoh_risk": _average(sdoh_risk),
        "average_deprivation_index": _average(deprivation),
        "average_access_score": _average(access),
        "average_social_support": _average(support),
        "transportation_access_distribution": {
            mode: round(count / total_patients, 3)
            for mode, count in transportation_modes.most_common()
        },
        "language_access_distribution": {
            lang: round(count / total_patients, 3)
            for lang, count in language_preferences.most_common()
        },
        "top_care_gaps": care_gaps_counter.most_common(5),
    }


def _load_care_plan_summary(care_plans_path: Path) -> Dict[str, Dict[str, int]]:
    with care_plans_path.open() as f:
        reader = csv.DictReader(f)
        total = 0
        status_counter: Counter[str] = Counter()
        condition_counter: Counter[str] = Counter()
        for row in reader:
            total += 1
            status_counter[row["status"]] += 1
            condition_counter[row["condition"]] += 1

    return {
        "total_entries": total,
        "status_breakdown": dict(status_counter),
        "condition_breakdown": dict(condition_counter),
    }


def summarize(dataset_dir: Path) -> Dict[str, Dict[str, object]]:
    patients_path = dataset_dir / "patients.csv"
    care_plans_path = dataset_dir / "care_plans.csv"
    report_path = dataset_dir / "migration_quality_report.json"

    if not patients_path.exists():
        raise FileNotFoundError(f"Missing patients.csv in {dataset_dir}")

    sdoh_summary = _load_sdoh_profiles(patients_path)

    care_summary: Dict[str, Dict[str, int]] = {}
    if care_plans_path.exists():
        care_summary = _load_care_plan_summary(care_plans_path)

    clinical_quality: Dict[str, object] = {}
    if report_path.exists():
        migration_quality = json.loads(report_path.read_text())
        summary = migration_quality.get("summary", {})
        quality_metrics = migration_quality.get("quality_metrics", {})
        alert_metrics = migration_quality.get("alert_metrics", {})

        total_patients = summary.get("total_patients", 0) or 1

        clinical_quality = {
            "average_quality_score": round(summary.get("average_quality_score", 0.0), 3),
            "success_rate": round(summary.get("success_rate", 0.0), 3),
            "quality_distribution": quality_metrics.get("quality_score_distribution", {}),
            "dimension_averages": quality_metrics.get("dimension_averages", {}),
            "critical_data_intact_rate": round(
                1 - (quality_metrics.get("quality_degradation_events", 0) / max(total_patients, 1)),
                3,
            ),
            "alert_density_per_patient": round(alert_metrics.get("total_alerts", 0) / max(total_patients, 1), 3),
            "critical_alert_rate": round(alert_metrics.get("critical_alerts", 0) / max(total_patients, 1), 3),
        }

    analytics = {
        "sdoh_equity": sdoh_summary,
        "care_coordination": care_summary,
        "clinical_quality": clinical_quality,
    }

    return analytics


def _render_cli(summary: Dict[str, Dict[str, object]]) -> None:
    if console is None:
        print(json.dumps(summary, indent=2))
        return

    console.print("[bold cyan]Clinical & SDOH Analytics Summary[/bold cyan]")

    sdoh = summary["sdoh_equity"]
    table = Table(title="SDOH Equity Signals")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Average SDOH Risk", f"{sdoh['average_sdoh_risk']:.3f}")
    table.add_row("Average Deprivation", f"{sdoh['average_deprivation_index']:.3f}")
    table.add_row("Average Access", f"{sdoh['average_access_score']:.3f}")
    table.add_row("Average Social Support", f"{sdoh['average_social_support']:.3f}")
    console.print(table)

    if summary.get("clinical_quality"):
        cq = summary["clinical_quality"]
        table = Table(title="Clinical Quality Signals")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Average Quality Score", f"{cq['average_quality_score']:.3f}")
        table.add_row("Success Rate", f"{cq['success_rate']:.3f}")
        table.add_row("Critical Data Intact", f"{cq['critical_data_intact_rate']:.3f}")
        table.add_row("Alert Density / Patient", f"{cq['alert_density_per_patient']:.3f}")
        table.add_row("Critical Alert Rate", f"{cq['critical_alert_rate']:.3f}")
        console.print(table)

    care = summary.get("care_coordination")
    if care:
        table = Table(title="Care Coordination Overview")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Care Plans", str(care.get("total_entries", 0)))
        table.add_row("Statuses", json.dumps(care.get("status_breakdown", {})))
        table.add_row("Top Conditions", json.dumps(care.get("condition_breakdown", {})))
        console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Generate clinical and SDOH analytics summary for Phase 4 datasets"
    )
    parser.add_argument("dataset_dir", type=str, help="Directory containing Phase 4 dataset outputs")
    parser.add_argument(
        "--output",
        type=str,
        default="equity_analytics_summary.json",
        help="Output JSON file name",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Pretty-print the analytics summary to the console",
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    summary = summarize(dataset_dir)
    out_path = dataset_dir / args.output
    out_path.write_text(json.dumps(summary, indent=2))

    if args.print:
        _render_cli(summary)

    message = "Clinical/SDOH analytics summary written to"
    print(f"{message} {out_path}")


if __name__ == "__main__":
    main()
