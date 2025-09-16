"""Migration simulation engine supporting legacy VistA→Oracle workflows."""
from __future__ import annotations

import math
import random
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from faker import Faker

from .migration_models import BatchMigrationStatus, MigrationConfig, MigrationStageResult

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from .synthetic_patient_generator import PatientRecord

# Core migration simulation constants
MIGRATION_STAGES = ["extract", "transform", "validate", "load"]
ETL_SUBSTAGES = {
    "extract": ["connect", "query", "export"],
    "transform": ["parse", "map", "standardize"],
    "validate": ["schema_check", "business_rules", "data_integrity"],
    "load": ["staging", "production", "verification"],
}
FAILURE_TYPES = [
    "network_timeout",
    "data_corruption",
    "mapping_error",
    "validation_failure",
    "resource_exhaustion",
    "security_violation",
    "system_unavailable",
]


class MigrationSimulator:
    """Comprehensive migration simulator for VistA-to-Oracle Health transitions."""

    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()
        self.fake = Faker()
        self.migration_history: List[BatchMigrationStatus] = []
        self.current_batch: Optional[BatchMigrationStatus] = None

    def simulate_staged_migration(
        self,
        patients: List["PatientRecord"],
        batch_id: Optional[str] = None,
        migration_strategy: str = "staged",
    ) -> BatchMigrationStatus:
        """Simulate a complete staged migration for a batch of patients."""

        batch_id = batch_id or f"batch_{uuid.uuid4().hex[:8]}"
        batch_status = BatchMigrationStatus(
            batch_id=batch_id,
            batch_size=len(patients),
            migration_strategy=migration_strategy,
            started_at=datetime.now(),
            patient_statuses={p.patient_id: "pending" for p in patients},
        )

        self.current_batch = batch_status

        try:
            for stage in MIGRATION_STAGES:
                batch_status.current_stage = stage
                stage_success = self._execute_migration_stage(patients, stage, batch_status)
                if not stage_success and migration_strategy == "fail_fast":
                    break

            batch_status.completed_at = datetime.now()
            batch_status.calculate_metrics()
            self._calculate_quality_metrics(patients, batch_status)
        except Exception as exc:  # pragma: no cover - defensive logging path
            batch_status.current_stage = "failed"
            print(f"Migration batch {batch_id} failed with error: {exc}")

        self.migration_history.append(batch_status)
        return batch_status

    def _execute_migration_stage(
        self,
        patients: List["PatientRecord"],
        stage: str,
        batch_status: BatchMigrationStatus,
    ) -> bool:
        substages = ETL_SUBSTAGES.get(stage, [stage])
        stage_successful = True

        for substage in substages:
            substage_result = MigrationStageResult(
                stage=stage,
                substage=substage,
                status="running",
                start_time=datetime.now(),
                records_processed=len(patients),
            )

            processing_time = self._calculate_processing_time(stage, len(patients))
            time.sleep(min(processing_time, 0.1))  # Cap sleep for CLI responsiveness

            successful_count = 0
            failed_count = 0
            substage_failure_types: List[str] = []

            for patient in patients:
                max_attempts = self.config.retry_attempts if self.config.retry_failures else 1
                attempt = 1
                patient_succeeded = False
                failure_record: Optional[Dict[str, Any]] = None

                while attempt <= max_attempts:
                    result_success, failure_details = self._process_patient_stage(patient, stage, substage)
                    if result_success:
                        patient_succeeded = True
                        if failure_record:
                            failure_record["attempts"] = attempt
                            failure_record["final_status"] = "resolved"
                            batch_status.patient_failures.append(failure_record)
                        break

                    failure_type = failure_details.get("failure_type") if failure_details else "unknown"
                    substage_failure_types.append(failure_type)
                    if not failure_record:
                        failure_record = {
                            "batch_id": batch_status.batch_id,
                            "patient_id": patient.patient_id,
                            "patient_name": f"{patient.first_name} {patient.last_name}",
                            "stage": stage,
                            "substage": substage,
                            "failure_types": [],
                            "attempts": attempt,
                        }
                    failure_record["failure_types"].append(failure_type)

                    if not self.config.retry_failures or attempt >= max_attempts:
                        failure_record["final_status"] = "failed"
                        batch_status.patient_failures.append(failure_record)
                        break

                    attempt += 1
                    time.sleep(self.config.retry_delay_seconds * 0.01)

                if patient_succeeded:
                    successful_count += 1
                    if batch_status.patient_statuses[patient.patient_id] != "failed":
                        batch_status.patient_statuses[patient.patient_id] = f"{stage}_{substage}_complete"
                else:
                    failed_count += 1
                    batch_status.patient_statuses[patient.patient_id] = "failed"
                    stage_successful = False

            substage_result.end_time = datetime.now()
            substage_result.records_successful = successful_count
            substage_result.records_failed = failed_count
            substage_result.status = "completed" if failed_count == 0 else "partial_failure"

            if failed_count > 0:
                common_failure = (
                    Counter(substage_failure_types).most_common(1)[0][0]
                    if substage_failure_types
                    else random.choice(FAILURE_TYPES)
                )
                substage_result.error_type = common_failure
                substage_result.error_message = self._generate_error_message(common_failure, stage, substage)

            batch_status.stage_results.append(substage_result)

        return stage_successful

    def _process_patient_stage(
        self, patient: "PatientRecord", stage: str, substage: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        stage_rates = self.config.substage_success_rates.get(stage, {})
        success_rate = stage_rates.get(substage, self.config.stage_success_rates.get(stage, 0.9))

        if random.random() < self.config.network_failure_rate:
            success_rate *= 0.5
        if random.random() < self.config.system_overload_rate:
            success_rate *= 0.7

        patient_succeeds = random.random() < success_rate
        failure_details: Optional[Dict[str, Any]] = None

        if patient_succeeds:
            quality_impact = self.config.quality_degradation_per_success
            patient.metadata['data_quality_score'] = max(
                0.0,
                patient.metadata['data_quality_score'] - quality_impact,
            )
            patient.metadata['migration_status'] = f"{stage}_{substage}_complete"
        else:
            quality_impact = self.config.quality_degradation_per_failure
            patient.metadata['data_quality_score'] = max(
                0.0,
                patient.metadata['data_quality_score'] - quality_impact,
            )
            failure_type = random.choice(FAILURE_TYPES)
            failure_details = {
                "failure_type": failure_type,
                "message": self._generate_error_message(failure_type, stage, substage),
            }
            patient.metadata['migration_status'] = f"{stage}_{substage}_failed"

        return patient_succeeds, failure_details

    def _calculate_processing_time(self, stage: str, patient_count: int) -> float:
        base_time = self.config.stage_base_duration.get(stage, 3.0)
        scaling_factor = 1 + math.log10(max(1, patient_count / 10))
        variance = random.uniform(1 - self.config.duration_variance, 1 + self.config.duration_variance)
        return base_time * scaling_factor * variance

    def _generate_error_message(self, error_type: str, stage: str, substage: str) -> str:
        error_templates = {
            "network_timeout": f"Network timeout during {stage}/{substage}. Retry recommended.",
            "data_corruption": f"Data corruption detected while processing {substage}. Check source integrity.",
            "mapping_error": f"Mapping error in {substage}. Verify terminology dictionaries.",
            "validation_failure": f"Validation failure in {stage}. Review schema rules.",
            "resource_exhaustion": f"Resource exhaustion during {stage}. Increase system capacity.",
            "security_violation": f"Security policy violation in {substage}. Audit access controls.",
            "system_unavailable": f"Target system unavailable during {stage}. Coordinate downtime mitigation.",
        }
        return error_templates.get(error_type, f"Unexpected failure in {stage}/{substage}")

    def _calculate_quality_metrics(
        self, patients: List["PatientRecord"], batch_status: BatchMigrationStatus
    ) -> None:
        quality_scores = [p.metadata.get('data_quality_score', 1.0) for p in patients]
        if quality_scores:
            batch_status.average_quality_score = sum(quality_scores) / len(quality_scores)

        sdoh_scores = [p.metadata.get('sdoh_risk_score', 0.0) for p in patients]
        deprivation_scores = [p.metadata.get('community_deprivation_index', 0.0) for p in patients]
        access_scores = [p.metadata.get('access_to_care_score', 0.0) for p in patients]
        support_scores = [p.metadata.get('social_support_score', 0.0) for p in patients]
        care_gap_counter = Counter(
            gap
            for p in patients
            for gap in p.metadata.get('sdoh_care_gaps', [])
        )
        care_totals = [p.metadata.get('care_plan_total', 0) for p in patients]
        care_completed = [p.metadata.get('care_plan_completed', 0) for p in patients]
        care_overdue = [p.metadata.get('care_plan_overdue', 0) for p in patients]

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        batch_status.sdoh_summary = {
            "avg_sdoh_risk": avg(sdoh_scores),
            "avg_deprivation": avg(deprivation_scores),
            "avg_access": avg(access_scores),
            "avg_social_support": avg(support_scores),
            "top_care_gaps": dict(care_gap_counter.most_common(5)),
        }

        batch_status.care_pathway_summary = {
            "avg_care_plans": avg(care_totals),
            "avg_completed": avg(care_completed),
            "avg_overdue": avg(care_overdue),
        }

        failures = batch_status.patient_failures
        if failures:
            attempts = [f.get("attempts", 1) for f in failures]
            resolved = sum(1 for f in failures if f.get("final_status") == "resolved")
            unresolved = sum(1 for f in failures if f.get("final_status") != "resolved")
        else:
            attempts = []
            resolved = 0
            unresolved = 0

        batch_status.retry_summary = {
            "total_failures": len(failures),
            "resolved": resolved,
            "unresolved": unresolved,
            "average_attempts": avg(attempts),
        }

    def get_migration_analytics(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        if batch_id:
            batch = next((b for b in self.migration_history if b.batch_id == batch_id), None)
            if not batch:
                return {"error": f"Batch {batch_id} not found"}
            batches = [batch]
        else:
            batches = self.migration_history

        if not batches:
            return {"error": "No migration data available"}

        analytics = {
            "summary": {
                "total_batches": len(batches),
                "total_patients": sum(b.batch_size for b in batches),
                "overall_success_rate": sum(b.overall_success_rate for b in batches) / len(batches),
                "average_quality_score": sum(b.average_quality_score for b in batches) / len(batches),
                "total_errors": sum(b.total_errors for b in batches),
            },
            "stage_performance": self._analyze_stage_performance(batches),
            "failure_analysis": self._analyze_failures(batches),
            "quality_trends": self._analyze_quality_trends(batches),
            "timing_analysis": self._analyze_timing(batches),
            "sdoh_equity": self._aggregate_sdoh_metrics(batches),
            "care_pathways": self._aggregate_care_metrics(batches),
            "retry_statistics": self._aggregate_retry_metrics(batches),
            "recommendations": self._generate_recommendations(batches),
        }
        return analytics

    def _analyze_stage_performance(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        stage_stats: Dict[str, Any] = {}
        for stage in MIGRATION_STAGES:
            stage_results = []
            for batch in batches:
                stage_results.extend([r for r in batch.stage_results if r.stage == stage])
            if stage_results:
                successful = sum(1 for r in stage_results if r.status == "completed")
                total_duration = sum(r.duration_seconds for r in stage_results)
                avg_records_processed = sum(r.records_processed for r in stage_results) / len(stage_results)
                stage_stats[stage] = {
                    "success_rate": successful / len(stage_results),
                    "average_duration": total_duration / len(stage_results),
                    "average_records_processed": avg_records_processed,
                    "total_executions": len(stage_results),
                }
        return stage_stats

    def _analyze_failures(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        failure_types = defaultdict(int)
        failure_stages = defaultdict(int)
        for batch in batches:
            for result in batch.stage_results:
                if result.status in ["failed", "partial_failure"] and result.error_type:
                    failure_types[result.error_type] += 1
                    failure_stages[result.stage] += 1
        return {
            "failure_types": dict(failure_types),
            "failure_by_stage": dict(failure_stages),
            "most_common_failure": max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else None,
        }

    def _analyze_quality_trends(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        quality_scores = [b.average_quality_score for b in batches]
        if len(quality_scores) > 1:
            quality_trend = quality_scores[-1] - quality_scores[0]
            quality_variance = max(quality_scores) - min(quality_scores)
        else:
            quality_trend = 0.0
            quality_variance = 0.0
        return {
            "initial_quality": quality_scores[0] if quality_scores else 0.0,
            "final_quality": quality_scores[-1] if quality_scores else 0.0,
            "quality_trend": quality_trend,
            "quality_variance": quality_variance,
            "min_quality": min(quality_scores) if quality_scores else 0.0,
            "max_quality": max(quality_scores) if quality_scores else 0.0,
        }

    def _analyze_timing(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        durations = []
        for batch in batches:
            if batch.started_at and batch.completed_at:
                duration = (batch.completed_at - batch.started_at).total_seconds()
                durations.append(duration)
        if not durations:
            return {"error": "No timing data available"}
        return {
            "average_batch_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_migration_time": sum(durations),
        }

    def _aggregate_sdoh_metrics(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        if not batches:
            return {}
        avg_sdoh = [b.sdoh_summary.get("avg_sdoh_risk", 0.0) for b in batches]
        avg_deprivation = [b.sdoh_summary.get("avg_deprivation", 0.0) for b in batches]
        avg_access = [b.sdoh_summary.get("avg_access", 0.0) for b in batches]
        avg_support = [b.sdoh_summary.get("avg_social_support", 0.0) for b in batches]
        care_gap_counter = Counter()
        for batch in batches:
            care_gap_counter.update(batch.sdoh_summary.get("top_care_gaps", {}))

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "average_sdoh_risk": avg(avg_sdoh),
            "average_deprivation_index": avg(avg_deprivation),
            "average_access_score": avg(avg_access),
            "average_social_support": avg(avg_support),
            "top_care_gaps": dict(care_gap_counter.most_common(5)),
        }

    def _aggregate_care_metrics(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        if not batches:
            return {}
        avg_total = [b.care_pathway_summary.get("avg_care_plans", 0.0) for b in batches]
        avg_completed = [b.care_pathway_summary.get("avg_completed", 0.0) for b in batches]
        avg_overdue = [b.care_pathway_summary.get("avg_overdue", 0.0) for b in batches]

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "average_care_plans_per_patient": avg(avg_total),
            "average_completed": avg(avg_completed),
            "average_overdue": avg(avg_overdue),
        }

    def _aggregate_retry_metrics(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        if not batches:
            return {}
        total_failures = sum(len(batch.patient_failures) for batch in batches)
        resolved = sum(
            1
            for batch in batches
            for failure in batch.patient_failures
            if failure.get("final_status") == "resolved"
        )
        unresolved = sum(
            1
            for batch in batches
            for failure in batch.patient_failures
            if failure.get("final_status") != "resolved"
        )
        attempts = [
            failure.get("attempts", 1)
            for batch in batches
            for failure in batch.patient_failures
        ]

        def avg(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "total_failures": total_failures,
            "resolved_failures": resolved,
            "unresolved_failures": unresolved,
            "average_attempts": avg(attempts),
        }

    def _generate_recommendations(self, batches: List[BatchMigrationStatus]) -> List[str]:
        if not batches:
            return ["No data available for recommendations"]

        recommendations = []
        avg_success_rate = sum(b.overall_success_rate for b in batches) / len(batches)
        if avg_success_rate < 0.8:
            recommendations.append(
                "Overall success rate is below 80%. Consider reducing batch sizes and implementing additional error handling."
            )

        avg_quality = sum(b.average_quality_score for b in batches) / len(batches)
        if avg_quality < 0.85:
            recommendations.append(
                "Significant data quality degradation detected. Review data transformation rules and implement additional validation checkpoints."
            )

        failure_analysis = self._analyze_failures(batches)
        common_failure = failure_analysis.get("most_common_failure")
        if common_failure:
            recommendations.append(
                f"Most common failure type is '{common_failure}'. Implement specific handling for this error type."
            )

        return recommendations

    def export_migration_report(self, output_file: str, batch_id: Optional[str] = None) -> None:
        """Export a detailed migration report to disk."""

        analytics = self.get_migration_analytics(batch_id)
        report_lines: List[str] = []
        report_lines.append("=" * 80)
        report_lines.append("HEALTHCARE DATA MIGRATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if batch_id:
            report_lines.append(f"Batch ID: {batch_id}")
        else:
            report_lines.append("Report Type: Overall Migration Analytics")

        report_lines.append("")

        summary = analytics.get("summary")
        if summary:
            report_lines.append("EXECUTIVE SUMMARY")
            report_lines.append("-" * 40)
            report_lines.append(f"Total Batches Processed: {summary['total_batches']}")
            report_lines.append(f"Total Patients Migrated: {summary['total_patients']}")
            report_lines.append(f"Overall Success Rate: {summary['overall_success_rate']:.2%}")
            report_lines.append(f"Average Data Quality Score: {summary['average_quality_score']:.3f}")
            report_lines.append(f"Total Errors Encountered: {summary['total_errors']}")
            report_lines.append("")

        stage_perf = analytics.get("stage_performance", {})
        if stage_perf:
            report_lines.append("STAGE PERFORMANCE ANALYSIS")
            report_lines.append("-" * 40)
            for stage, stats in stage_perf.items():
                report_lines.append(f"Stage: {stage.upper()}")
                report_lines.append(f"  Success Rate: {stats['success_rate']:.2%}")
                report_lines.append(f"  Average Duration: {stats['average_duration']:.2f} seconds")
                report_lines.append(f"  Average Records: {stats['average_records_processed']:.0f}")
                report_lines.append("")

        failure = analytics.get("failure_analysis")
        if failure:
            report_lines.append("FAILURE ANALYSIS")
            report_lines.append("-" * 40)
            failure_types = failure.get("failure_types", {})
            if failure_types:
                report_lines.append("Failure Types:")
                for failure_type, count in failure_types.items():
                    report_lines.append(f"  {failure_type}: {count}")
                report_lines.append("")
            if failure.get("most_common_failure"):
                report_lines.append(f"Most Common Failure: {failure['most_common_failure']}")
                report_lines.append("")

        sdoh_metrics = analytics.get("sdoh_equity")
        if sdoh_metrics:
            report_lines.append("SDOH & EQUITY METRICS")
            report_lines.append("-" * 40)
            report_lines.append(f"Average SDOH Risk Score: {sdoh_metrics.get('average_sdoh_risk', 0.0):.3f}")
            report_lines.append(
                f"Average Community Deprivation Index: {sdoh_metrics.get('average_deprivation_index', 0.0):.3f}"
            )
            report_lines.append(f"Average Access-to-Care Score: {sdoh_metrics.get('average_access_score', 0.0):.3f}")
            report_lines.append(f"Average Social Support Score: {sdoh_metrics.get('average_social_support', 0.0):.3f}")
            care_gaps = sdoh_metrics.get('top_care_gaps', {})
            if care_gaps:
                report_lines.append("Top Care Gaps:")
                for gap, count in care_gaps.items():
                    report_lines.append(f"  {gap}: {count}")
            report_lines.append("")

        care_metrics = analytics.get("care_pathways")
        if care_metrics:
            report_lines.append("CARE PATHWAY METRICS")
            report_lines.append("-" * 40)
            report_lines.append(
                f"Average Care Plans per Patient: {care_metrics.get('average_care_plans_per_patient', 0.0):.2f}"
            )
            report_lines.append(f"Average Completed Milestones: {care_metrics.get('average_completed', 0.0):.2f}")
            report_lines.append(f"Average Overdue Milestones: {care_metrics.get('average_overdue', 0.0):.2f}")
            report_lines.append("")

        retry_stats = analytics.get("retry_statistics")
        if retry_stats:
            report_lines.append("RETRY METRICS")
            report_lines.append("-" * 40)
            report_lines.append(f"Total Failures Logged: {retry_stats.get('total_failures', 0)}")
            report_lines.append(f"Resolved via Retry: {retry_stats.get('resolved_failures', 0)}")
            report_lines.append(f"Unresolved Failures: {retry_stats.get('unresolved_failures', 0)}")
            report_lines.append(f"Average Attempts per Failure: {retry_stats.get('average_attempts', 0.0):.2f}")
            report_lines.append("")

        recommendations = analytics.get("recommendations", [])
        if recommendations:
            report_lines.append("RECOMMENDATIONS")
            report_lines.append("-" * 40)
            for index, rec in enumerate(recommendations, 1):
                report_lines.append(f"{index}. {rec}")
            report_lines.append("")

        with open(output_file, "w") as handle:
            handle.write("\n".join(report_lines))


__all__ = [
    "MigrationSimulator",
    "MIGRATION_STAGES",
    "ETL_SUBSTAGES",
    "FAILURE_TYPES",
]
