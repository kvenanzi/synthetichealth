"""Migration simulation dataclasses and configuration primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MigrationStageResult:
    """Result of a migration stage execution."""

    stage: str
    substage: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    data_quality_impact: float = 0.0

    def __post_init__(self) -> None:
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()


@dataclass
class BatchMigrationStatus:
    """Migration status container for a batch of patients."""

    batch_id: str
    batch_size: int
    source_system: str = "vista"
    target_system: str = "oracle_health"
    migration_strategy: str = "staged"  # staged, big_bang, parallel
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_stage: str = "pending"
    stage_results: List[MigrationStageResult] = field(default_factory=list)
    patient_statuses: Dict[str, str] = field(default_factory=dict)
    overall_success_rate: float = 0.0
    average_quality_score: float = 1.0
    total_errors: int = 0
    sdoh_summary: Dict[str, Any] = field(default_factory=dict)
    care_pathway_summary: Dict[str, Any] = field(default_factory=dict)
    patient_failures: List[Dict[str, Any]] = field(default_factory=list)
    retry_summary: Dict[str, Any] = field(default_factory=dict)

    def get_stage_result(self, stage: str, substage: Optional[str] = None) -> Optional[MigrationStageResult]:
        for result in self.stage_results:
            if result.stage == stage and result.substage == substage:
                return result
        return None

    def calculate_metrics(self) -> None:
        if self.stage_results:
            successful_patients = sum(1 for status in self.patient_statuses.values() if status != "failed")
            total_patients = len(self.patient_statuses)
            if total_patients > 0:
                self.overall_success_rate = successful_patients / total_patients
            self.total_errors = sum(r.records_failed for r in self.stage_results)


@dataclass
class MigrationConfig:
    """Configuration inputs for the migration simulation."""

    stage_success_rates: Dict[str, float] = field(
        default_factory=lambda: {
            "extract": 0.98,
            "transform": 0.95,
            "validate": 0.92,
            "load": 0.90,
        }
    )
    substage_success_rates: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {
            "extract": {"connect": 0.99, "query": 0.98, "export": 0.97},
            "transform": {"parse": 0.98, "map": 0.95, "standardize": 0.93},
            "validate": {"schema_check": 0.96, "business_rules": 0.92, "data_integrity": 0.89},
            "load": {"staging": 0.95, "production": 0.88, "verification": 0.92},
        }
    )
    stage_base_duration: Dict[str, float] = field(
        default_factory=lambda: {"extract": 2.5, "transform": 4.0, "validate": 3.5, "load": 5.0}
    )
    duration_variance: float = 0.3
    quality_degradation_per_failure: float = 0.15
    quality_degradation_per_success: float = 0.02
    network_failure_rate: float = 0.05
    system_overload_rate: float = 0.03
    data_corruption_rate: float = 0.01
    max_concurrent_patients: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    retry_failures: bool = False


__all__ = [
    "MigrationStageResult",
    "BatchMigrationStatus",
    "MigrationConfig",
]
