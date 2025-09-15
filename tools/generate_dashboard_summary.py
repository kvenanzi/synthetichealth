import csv
import json
from pathlib import Path
from statistics import mean

import argparse


def summarize(dataset_dir: Path) -> dict:
    patients_path = dataset_dir / "patients.csv"
    care_plans_path = dataset_dir / "care_plans.csv"
    report_path = dataset_dir / "migration_quality_report.json"

    if not patients_path.exists():
        raise FileNotFoundError(f"Missing patients.csv in {dataset_dir}")

    deprivation, access, support, sdoh_risk = [], [], [], []
    care_gaps_counter = {}

    with patients_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            deprivation.append(float(row.get("community_deprivation_index", 0.0)))
            access.append(float(row.get("access_to_care_score", 0.0)))
            support.append(float(row.get("social_support_score", 0.0)))
            sdoh_risk.append(float(row.get("sdoh_risk_score", 0.0)))
            gaps = json.loads(row.get("sdoh_care_gaps", "[]"))
            for gap in gaps:
                care_gaps_counter[gap] = care_gaps_counter.get(gap, 0) + 1

    def avg(values):
        return round(mean(values), 3) if values else 0.0

    sdoh_summary = {
        "average_sdoh_risk": avg(sdoh_risk),
        "average_deprivation_index": avg(deprivation),
        "average_access_score": avg(access),
        "average_social_support": avg(support),
        "top_care_gaps": sorted(care_gaps_counter.items(), key=lambda x: x[1], reverse=True)[:5],
    }

    care_summary = {}
    if care_plans_path.exists():
        with care_plans_path.open() as f:
            reader = csv.DictReader(f)
            total = 0
            status_counter = {}
            condition_counter = {}
            for row in reader:
                total += 1
                status_counter[row["status"]] = status_counter.get(row["status"], 0) + 1
                condition_counter[row["condition"]] = condition_counter.get(row["condition"], 0) + 1
            care_summary = {
                "total_entries": total,
                "status_breakdown": status_counter,
                "condition_breakdown": condition_counter,
            }

    migration_summary = {}
    if report_path.exists():
        with report_path.open() as f:
            migration_quality = json.load(f)
        migration_summary = migration_quality.get("migration_summary", {})
        migration_summary["care_pathway_metrics"] = migration_quality.get("care_pathways", {})
        migration_summary["sdoh_metrics"] = migration_quality.get("sdoh_equity", {})

    return {
        "sdoh_summary": sdoh_summary,
        "care_plan_summary": care_summary,
        "migration_summary": migration_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate dashboard-ready summary for Phase 4 datasets")
    parser.add_argument("dataset_dir", type=str, help="Directory containing Phase 4 dataset outputs")
    parser.add_argument("--output", type=str, default="dashboard_summary.json", help="Output JSON file name")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    summary = summarize(dataset_dir)
    out_path = dataset_dir / args.output
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Dashboard summary written to {out_path}")


if __name__ == "__main__":
    main()
