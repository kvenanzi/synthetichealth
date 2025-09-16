#!/usr/bin/env python3
"""
Enhanced Healthcare Migration Simulator

This module extends the original MigrationSimulator with comprehensive healthcare data quality management,
patient-level tracking, HIPAA compliance monitoring, and real-time quality alerts.

Key Enhancements:
- Granular patient-level migration tracking with clinical context
- Healthcare-specific data quality degradation simulation
- Real-time quality monitoring and alerting system
- HIPAA compliance tracking and audit trails
- Clinical data validation metrics and reporting
- Production-ready dashboard and monitoring capabilities

Integration with existing MigrationSimulator architecture while adding enterprise-grade
healthcare data migration capabilities.

Author: Healthcare Data Quality Engineer  
Date: 2025-09-09
"""

import json
import logging
import random
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
import uuid

# Import our enhanced tracking components
from .enhanced_migration_tracker import (
    PatientMigrationStatus,
    HealthcareDataQualityScorer,
    ClinicalDataDegradationSimulator, 
    MigrationQualityMonitor,
    DataQualityDimension,
    ClinicalDataCriticality,
    AlertSeverity,
    QualityAlert,
    MigrationStageStatus
)

# Import original components (assuming they exist in synthetic_patient_generator.py)
try:
    from synthetic_patient_generator import (
        PatientRecord, 
        MigrationConfig,
        BatchMigrationStatus,
        MIGRATION_STAGES,
        ETL_SUBSTAGES,
        FAILURE_TYPES
    )
except ImportError:
    # Provide fallback definitions if import fails
    from dataclasses import dataclass, field
    from typing import Dict
    
    MIGRATION_STAGES = ["extract", "transform", "validate", "load"]
    ETL_SUBSTAGES = {
        "extract": ["connect", "query", "export"],
        "transform": ["parse", "map", "standardize"],
        "validate": ["schema_check", "business_rules", "data_integrity"],
        "load": ["staging", "production", "verification"]
    }
    FAILURE_TYPES = [
        "network_timeout", "data_corruption", "mapping_error", "validation_failure", 
        "resource_exhaustion", "security_violation", "system_unavailable"
    ]
    
    @dataclass
    class MigrationConfig:
        """Fallback MigrationConfig if import fails"""
        stage_success_rates: Dict[str, float] = field(default_factory=lambda: {
            "extract": 0.98,
            "transform": 0.95,
            "validate": 0.92,
            "load": 0.90
        })
        network_failure_rate: float = 0.05
        system_overload_rate: float = 0.03
        quality_degradation_per_failure: float = 0.15
    
    @dataclass
    class PatientRecord:
        """Fallback PatientRecord if import fails"""
        patient_id: str = ""
        mrn: str = ""
        first_name: str = ""
        last_name: str = ""
        
        def __post_init__(self):
            if not self.patient_id:
                import uuid
                self.patient_id = str(uuid.uuid4())

logger = logging.getLogger(__name__)

@dataclass
class HIPAAComplianceTracker:
    """HIPAA compliance tracking during migration"""
    patient_id: str
    mrn: str
    
    # PHI inventory
    phi_elements: Dict[str, str] = field(default_factory=dict)
    phi_access_log: List[Dict[str, Any]] = field(default_factory=list)
    
    # Compliance status
    encryption_status: Dict[str, bool] = field(default_factory=dict)
    access_controls_verified: bool = False
    audit_trail_complete: bool = True
    minimum_necessary_applied: bool = True
    
    # Violation tracking
    violations: List[Dict[str, Any]] = field(default_factory=list)
    compliance_score: float = 1.0
    
    def log_phi_access(self, user_id: str, access_type: str, phi_element: str, 
                      justification: str) -> None:
        """Log PHI access for audit trail"""
        access_event = {
            "timestamp": datetime.now(),
            "user_id": user_id,
            "access_type": access_type,  # read, write, modify, delete
            "phi_element": phi_element,
            "justification": justification
        }
        self.phi_access_log.append(access_event)
        logger.info(f"PHI Access - Patient {self.patient_id}: {access_type} {phi_element} by {user_id}")
    
    def record_violation(self, violation_type: str, description: str, severity: str) -> None:
        """Record HIPAA compliance violation"""
        violation = {
            "timestamp": datetime.now(),
            "violation_type": violation_type,
            "description": description,
            "severity": severity,  # low, medium, high, critical
            "resolved": False
        }
        self.violations.append(violation)
        
        # Adjust compliance score based on severity
        severity_impact = {"low": 0.05, "medium": 0.15, "high": 0.30, "critical": 0.50}
        self.compliance_score = max(0.0, self.compliance_score - severity_impact.get(severity, 0.15))
        
        logger.warning(f"HIPAA Violation - Patient {self.patient_id}: {violation_type} - {description}")

@dataclass 
class EnhancedMigrationMetrics:
    """Comprehensive migration metrics for healthcare environments"""
    
    # Basic migration metrics
    total_patients: int = 0
    total_batches: int = 0
    successful_migrations: int = 0
    failed_migrations: int = 0
    
    # Quality metrics
    average_quality_score: float = 0.0
    quality_score_distribution: Dict[str, int] = field(default_factory=dict)
    dimension_quality_scores: Dict[str, float] = field(default_factory=dict)
    
    # Alert metrics
    total_alerts: int = 0
    critical_alerts: int = 0
    unresolved_alerts: int = 0
    alerts_by_dimension: Dict[str, int] = field(default_factory=dict)
    
    # HIPAA compliance metrics
    hipaa_compliance_rate: float = 1.0
    phi_exposure_incidents: int = 0
    access_violations: int = 0
    
    # Performance metrics
    average_migration_time: float = 0.0
    stage_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Clinical data metrics
    critical_data_integrity: float = 1.0
    medication_accuracy: float = 1.0
    allergy_completeness: float = 1.0
    
    # Trend data
    quality_trend_data: List[Tuple[datetime, float]] = field(default_factory=list)
    alert_trend_data: List[Tuple[datetime, int]] = field(default_factory=list)

class EnhancedMigrationSimulator:
    """
    Enhanced healthcare migration simulator with comprehensive quality management.
    
    This class extends the original MigrationSimulator with:
    - Granular patient-level tracking
    - Healthcare-specific quality scoring
    - Real-time monitoring and alerting
    - HIPAA compliance tracking
    - Clinical data validation
    - Production-ready reporting
    """
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        # Initialize base configuration
        self.config = config or self._create_default_config()
        
        # Initialize enhanced components
        self.quality_scorer = HealthcareDataQualityScorer()
        self.degradation_simulator = ClinicalDataDegradationSimulator()
        self.quality_monitor = MigrationQualityMonitor(self.quality_scorer)
        
        # Patient tracking
        self.patient_statuses: Dict[str, PatientMigrationStatus] = {}
        self.hipaa_trackers: Dict[str, HIPAAComplianceTracker] = {}
        
        # Migration tracking
        self.migration_history: List[Any] = []  # Batch results
        self.current_batch: Optional[Any] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics and monitoring
        self.metrics = EnhancedMigrationMetrics()
        self.real_time_dashboard_data: Dict[str, Any] = {}
        
        # Initialize dashboard with default data
        self._update_dashboard_data()
        
        logger.info("Enhanced Healthcare Migration Simulator initialized")
    
    def _create_default_config(self):
        """Create default configuration if not provided"""
        # This would normally import MigrationConfig, but providing fallback
        @dataclass
        class DefaultConfig:
            stage_success_rates: Dict[str, float] = field(default_factory=lambda: {
                "extract": 0.98,
                "transform": 0.95,
                "validate": 0.92,
                "load": 0.90
            })
            network_failure_rate: float = 0.05
            system_overload_rate: float = 0.03
            quality_degradation_per_failure: float = 0.15
        
        return DefaultConfig()
    
    def simulate_patient_migration(self, patient: 'PatientRecord', 
                                  batch_id: str) -> PatientMigrationStatus:
        """
        Simulate migration for a single patient with comprehensive tracking.
        
        Args:
            patient: Patient record to migrate
            batch_id: Batch identifier for this migration
            
        Returns:
            PatientMigrationStatus with detailed tracking information
        """
        # Initialize patient tracking
        patient_status = PatientMigrationStatus(
            patient_id=patient.patient_id,
            mrn=patient.mrn,
            patient_name=f"{patient.first_name} {patient.last_name}",
            migration_batch_id=batch_id
        )
        
        # Initialize HIPAA compliance tracking
        hipaa_tracker = HIPAAComplianceTracker(
            patient_id=patient.patient_id,
            mrn=patient.mrn
        )
        
        # Store tracking objects
        self.patient_statuses[patient.patient_id] = patient_status
        self.hipaa_trackers[patient.patient_id] = hipaa_tracker
        
        # Initialize PHI inventory
        self._initialize_phi_inventory(patient, hipaa_tracker)
        
        # Calculate initial quality score
        patient_data = self._patient_to_dict(patient)
        initial_score, initial_dimensions = self.quality_scorer.calculate_patient_quality_score(patient_data)
        patient_status.initial_quality_score = initial_score
        patient_status.current_quality_score = initial_score
        patient_status.quality_by_dimension = initial_dimensions
        
        # Log migration start
        patient_status.log_event("migration_started", {
            "batch_id": batch_id,
            "initial_quality_score": initial_score
        })
        
        # Execute migration stages
        for stage in MIGRATION_STAGES:
            self._execute_migration_stage(patient, patient_status, hipaa_tracker, stage)
        
        # Final quality assessment
        self._perform_final_quality_assessment(patient, patient_status)
        
        # Generate alerts based on final state
        alerts = self.quality_monitor.monitor_patient_quality(patient_status, patient_data)
        
        # Log completion
        patient_status.log_event("migration_completed", {
            "final_quality_score": patient_status.current_quality_score,
            "alerts_generated": len(alerts),
            "hipaa_compliance_score": hipaa_tracker.compliance_score
        })
        
        return patient_status
    
    def _initialize_phi_inventory(self, patient: 'PatientRecord', 
                                 hipaa_tracker: HIPAAComplianceTracker) -> None:
        """Initialize PHI inventory for HIPAA tracking"""
        phi_elements = {
            "ssn": getattr(patient, 'ssn', ''),
            "phone": getattr(patient, 'phone', ''),
            "email": getattr(patient, 'email', ''),
            "address": f"{getattr(patient, 'address', '')} {getattr(patient, 'city', '')} {getattr(patient, 'state', '')}",
            "mrn": patient.mrn,
            "birthdate": getattr(patient, 'birthdate', '')
        }
        
        hipaa_tracker.phi_elements = phi_elements
        hipaa_tracker.encryption_status = {
            element: self._is_element_encrypted(value) 
            for element, value in phi_elements.items()
        }
    
    def _is_element_encrypted(self, value: str) -> bool:
        """Check if PHI element is properly encrypted"""
        # Simple heuristic - in production this would be more sophisticated
        return (not value or 
                value.startswith('ENCRYPTED_') or 
                '*' in value or 
                'X' in value)
    
    def _execute_migration_stage(self, patient: 'PatientRecord',
                                patient_status: PatientMigrationStatus,
                                hipaa_tracker: HIPAAComplianceTracker,
                                stage: str) -> None:
        """Execute a single migration stage with comprehensive tracking"""
        
        patient_status.current_stage = stage
        patient_status.stage_timestamps[stage] = datetime.now()
        patient_status.stage_statuses[stage] = MigrationStageStatus.IN_PROGRESS
        
        stage_start_time = time.time()
        stage_success = True
        
        # Execute substages
        for substage in ETL_SUBSTAGES.get(stage, [stage]):
            patient_status.current_substage = substage
            
            # Log PHI access for audit trail
            hipaa_tracker.log_phi_access(
                user_id="migration_system",
                access_type="read",
                phi_element=f"{stage}_{substage}",
                justification=f"Healthcare data migration - {stage} stage"
            )
            
            # Simulate substage execution
            substage_success = self._execute_substage(
                patient, patient_status, hipaa_tracker, stage, substage
            )
            
            if not substage_success:
                stage_success = False
                patient_status.stage_error_counts[stage] += 1
        
        # Record stage completion
        stage_duration = time.time() - stage_start_time
        patient_status.stage_durations[stage] = stage_duration
        
        if stage_success:
            patient_status.stage_statuses[stage] = MigrationStageStatus.COMPLETED
        else:
            patient_status.stage_statuses[stage] = MigrationStageStatus.FAILED
        
        # Log stage completion
        patient_status.log_event(f"{stage}_completed", {
            "success": stage_success,
            "duration": stage_duration,
            "error_count": patient_status.stage_error_counts[stage]
        })
    
    def _execute_substage(self, patient: 'PatientRecord',
                         patient_status: PatientMigrationStatus,
                         hipaa_tracker: HIPAAComplianceTracker,
                         stage: str, substage: str) -> bool:
        """Execute migration substage with failure simulation and quality degradation"""
        
        # Determine if substage should fail
        success_rate = self.config.stage_success_rates.get(stage, 0.95)
        
        # Adjust success rate based on previous failures
        failure_adjustment = patient_status.stage_error_counts[stage] * 0.1
        adjusted_success_rate = max(0.1, success_rate - failure_adjustment)
        
        substage_success = random.random() < adjusted_success_rate
        
        if not substage_success:
            # Simulate failure and data degradation
            failure_type = random.choice(FAILURE_TYPES)
            
            # Create failure context
            failure_context = {
                "failure_type": failure_type,
                "stage": stage,
                "substage": substage,
                "severity": random.uniform(0.3, 0.8)
            }
            
            # Apply data degradation
            patient_data = self._patient_to_dict(patient)
            degraded_data, degradation_events = self.degradation_simulator.simulate_degradation(
                patient_data, failure_context
            )
            
            # Update patient quality score
            new_score, new_dimensions = self.quality_scorer.calculate_patient_quality_score(degraded_data)
            
            # Record quality degradation event
            quality_change = patient_status.current_quality_score - new_score
            patient_status.quality_degradation_events.append({
                "timestamp": datetime.now(),
                "stage": stage,
                "substage": substage,
                "failure_type": failure_type,
                "quality_change": quality_change,
                "degradation_events": degradation_events,
                "previous_score": patient_status.current_quality_score,
                "new_score": new_score
            })
            
            patient_status.current_quality_score = new_score
            patient_status.quality_by_dimension = new_dimensions
            
            # Check for HIPAA violations
            self._check_hipaa_violations(degraded_data, hipaa_tracker, failure_context)
            
            # Log failure event
            patient_status.log_event("substage_failed", {
                "stage": stage,
                "substage": substage,
                "failure_type": failure_type,
                "quality_degradation": quality_change,
                "degradation_events": degradation_events
            })
        
        # Simulate processing time
        base_time = 0.5 + random.uniform(0.1, 2.0)
        time.sleep(base_time * 0.01)  # Scaled down for simulation
        
        return substage_success
    
    def _check_hipaa_violations(self, patient_data: Dict[str, Any],
                               hipaa_tracker: HIPAAComplianceTracker,
                               failure_context: Dict[str, Any]) -> None:
        """Check for HIPAA violations during migration"""
        
        # Check for PHI exposure
        phi_fields = ['ssn', 'phone', 'email', 'address']
        for field in phi_fields:
            value = patient_data.get(field, '')
            if value and not self._is_element_encrypted(str(value)):
                hipaa_tracker.record_violation(
                    violation_type="phi_exposure",
                    description=f"PHI field '{field}' not properly protected",
                    severity="critical"
                )
        
        # Check for unauthorized access patterns
        if failure_context.get("failure_type") == "security_violation":
            hipaa_tracker.record_violation(
                violation_type="unauthorized_access",
                description="Security violation detected during migration",
                severity="high"
            )
        
        # Check audit trail integrity
        if len(hipaa_tracker.phi_access_log) == 0:
            hipaa_tracker.record_violation(
                violation_type="audit_trail_incomplete",
                description="Missing audit trail entries for PHI access",
                severity="medium"
            )
    
    def _perform_final_quality_assessment(self, patient: 'PatientRecord',
                                         patient_status: PatientMigrationStatus) -> None:
        """Perform comprehensive final quality assessment"""
        
        patient_data = self._patient_to_dict(patient)
        
        # Clinical data validation
        self._validate_clinical_data_integrity(patient_data, patient_status)
        
        # Calculate final metrics
        quality_score_change = (patient_status.initial_quality_score - 
                               patient_status.current_quality_score)
        
        # Determine if critical data is intact
        critical_dimensions = [
            DataQualityDimension.ACCURACY,
            DataQualityDimension.HIPAA_COMPLIANCE,
            DataQualityDimension.CLINICAL_RELEVANCE
        ]
        
        patient_status.critical_data_intact = all(
            patient_status.quality_by_dimension.get(dim.value, 1.0) >= 0.9
            for dim in critical_dimensions
        )
        
        # Log final assessment
        patient_status.log_event("final_assessment", {
            "quality_score_change": quality_score_change,
            "critical_data_intact": patient_status.critical_data_intact,
            "total_errors": sum(patient_status.stage_error_counts.values()),
            "degradation_events": len(patient_status.quality_degradation_events)
        })
    
    def _validate_clinical_data_integrity(self, patient_data: Dict[str, Any],
                                         patient_status: PatientMigrationStatus) -> None:
        """Validate integrity of clinical data elements"""
        
        validation_errors = []
        
        # Check critical medical information
        if not patient_data.get('allergies') and not patient_data.get('no_known_allergies'):
            validation_errors.append("Missing allergy information")
        
        # Validate medication data
        medications = patient_data.get('medications', [])
        for med in medications:
            if not med.get('dosage') or not med.get('frequency'):
                validation_errors.append(f"Incomplete medication record: {med.get('medication', 'unknown')}")
        
        # Check vital signs consistency
        observations = patient_data.get('observations', [])
        for obs in observations:
            if obs.get('type') == 'Blood Pressure':
                try:
                    bp_value = str(obs.get('value', ''))
                    if '/' not in bp_value:
                        validation_errors.append("Invalid blood pressure format")
                except:
                    validation_errors.append("Blood pressure value parsing error")
        
        patient_status.clinical_validation_errors = validation_errors
        
        if validation_errors:
            patient_status.log_event("clinical_validation_failed", {
                "errors": validation_errors,
                "error_count": len(validation_errors)
            })
    
    def _patient_to_dict(self, patient: 'PatientRecord') -> Dict[str, Any]:
        """Convert PatientRecord to dictionary for quality scoring"""
        # This would normally use the patient's actual data structure
        # Providing a basic conversion for simulation
        return {
            "patient_id": patient.patient_id,
            "mrn": patient.mrn,
            "first_name": getattr(patient, 'first_name', ''),
            "last_name": getattr(patient, 'last_name', ''),
            "birthdate": getattr(patient, 'birthdate', ''),
            "phone": getattr(patient, 'phone', ''),
            "email": getattr(patient, 'email', ''),
            "address": getattr(patient, 'address', ''),
            "allergies": getattr(patient, 'allergies', []),
            "medications": getattr(patient, 'medications', []),
            "conditions": getattr(patient, 'conditions', []),
            "observations": getattr(patient, 'observations', []),
            "encounters": getattr(patient, 'encounters', [])
        }
    
    def simulate_batch_migration(self, patients: List['PatientRecord'],
                               batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate migration for a batch of patients with comprehensive tracking.
        
        Args:
            patients: List of patient records to migrate
            batch_id: Optional batch identifier
            
        Returns:
            Comprehensive batch migration results
        """
        batch_id = batch_id or f"batch_{uuid.uuid4().hex[:8]}"
        batch_start_time = datetime.now()
        
        logger.info(f"Starting batch migration {batch_id} with {len(patients)} patients")
        
        # Initialize batch tracking
        patient_results = {}
        batch_alerts = []
        
        # Process each patient
        for i, patient in enumerate(patients, 1):
            logger.info(f"Processing patient {i}/{len(patients)}: {patient.patient_id}")
            
            try:
                patient_status = self.simulate_patient_migration(patient, batch_id)
                patient_results[patient.patient_id] = patient_status
                
                # Generate alerts for this patient
                patient_data = self._patient_to_dict(patient)
                alerts = self.quality_monitor.monitor_patient_quality(patient_status, patient_data)
                batch_alerts.extend(alerts)
                
            except Exception as e:
                logger.error(f"Failed to process patient {patient.patient_id}: {e}")
                # Create failure status
                failure_status = PatientMigrationStatus(
                    patient_id=patient.patient_id,
                    mrn=getattr(patient, 'mrn', 'unknown'),
                    patient_name=f"{getattr(patient, 'first_name', '')} {getattr(patient, 'last_name', '')}",
                    migration_batch_id=batch_id
                )
                failure_status.stage_statuses["extract"] = MigrationStageStatus.FAILED
                failure_status.current_quality_score = 0.0
                patient_results[patient.patient_id] = failure_status
        
        # Calculate batch metrics
        batch_duration = (datetime.now() - batch_start_time).total_seconds()
        batch_results = self._calculate_batch_results(
            batch_id, patients, patient_results, batch_alerts, batch_duration
        )
        
        # Update overall metrics
        self._update_migration_metrics(batch_results)
        
        # Update real-time dashboard
        self._update_dashboard_data()
        
        logger.info(f"Completed batch migration {batch_id} in {batch_duration:.2f} seconds")
        
        return batch_results
    
    def _calculate_batch_results(self, batch_id: str, patients: List['PatientRecord'],
                                patient_results: Dict[str, PatientMigrationStatus],
                                alerts: List[QualityAlert], duration: float) -> Dict[str, Any]:
        """Calculate comprehensive batch migration results"""
        
        total_patients = len(patients)
        successful_patients = sum(
            1 for status in patient_results.values()
            if status.current_quality_score >= 0.7 and status.critical_data_intact
        )
        
        # Quality metrics
        quality_scores = [status.current_quality_score for status in patient_results.values()]
        average_quality = statistics.mean(quality_scores) if quality_scores else 0.0
        
        # Alert metrics
        critical_alerts = [alert for alert in alerts if alert.severity == AlertSeverity.CRITICAL]
        high_alerts = [alert for alert in alerts if alert.severity == AlertSeverity.HIGH]
        
        # HIPAA compliance metrics
        hipaa_scores = [
            tracker.compliance_score 
            for tracker in self.hipaa_trackers.values()
            if tracker.patient_id in patient_results
        ]
        average_hipaa_compliance = statistics.mean(hipaa_scores) if hipaa_scores else 1.0
        
        # Stage performance metrics
        stage_performance = {}
        for stage in MIGRATION_STAGES:
            stage_durations = [
                status.stage_durations.get(stage, 0)
                for status in patient_results.values()
                if stage in status.stage_durations
            ]
            stage_errors = [
                status.stage_error_counts.get(stage, 0)
                for status in patient_results.values()
            ]
            
            stage_performance[stage] = {
                "average_duration": statistics.mean(stage_durations) if stage_durations else 0.0,
                "success_rate": 1 - (sum(stage_errors) / total_patients) if total_patients > 0 else 0.0,
                "total_errors": sum(stage_errors)
            }
        
        return {
            "batch_id": batch_id,
            "timestamp": datetime.now(),
            "duration": duration,
            "summary": {
                "total_patients": total_patients,
                "successful_patients": successful_patients,
                "success_rate": successful_patients / total_patients if total_patients > 0 else 0.0,
                "average_quality_score": average_quality,
                "average_hipaa_compliance": average_hipaa_compliance
            },
            "quality_metrics": {
                "quality_score_distribution": self._calculate_quality_distribution(quality_scores),
                "dimension_averages": self._calculate_dimension_averages(patient_results),
                "quality_degradation_events": sum(
                    len(status.quality_degradation_events) for status in patient_results.values()
                )
            },
            "alert_metrics": {
                "total_alerts": len(alerts),
                "critical_alerts": len(critical_alerts),
                "high_alerts": len(high_alerts),
                "alerts_requiring_intervention": sum(
                    1 for alert in alerts if alert.requires_intervention
                )
            },
            "hipaa_compliance": {
                "average_compliance_score": average_hipaa_compliance,
                "phi_exposure_incidents": sum(
                    len([v for v in tracker.violations if v["violation_type"] == "phi_exposure"])
                    for tracker in self.hipaa_trackers.values()
                    if tracker.patient_id in patient_results
                ),
                "total_violations": sum(
                    len(tracker.violations) for tracker in self.hipaa_trackers.values()
                    if tracker.patient_id in patient_results
                )
            },
            "stage_performance": stage_performance,
            "patient_details": {
                patient_id: {
                    "quality_score": status.current_quality_score,
                    "critical_data_intact": status.critical_data_intact,
                    "total_errors": sum(status.stage_error_counts.values()),
                    "hipaa_compliance": self.hipaa_trackers.get(patient_id, {}).compliance_score
                }
                for patient_id, status in patient_results.items()
            }
        }
    
    def _calculate_quality_distribution(self, quality_scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of quality scores"""
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        
        for score in quality_scores:
            if score >= 0.9:
                distribution["excellent"] += 1
            elif score >= 0.8:
                distribution["good"] += 1
            elif score >= 0.7:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1
        
        return distribution
    
    def _calculate_dimension_averages(self, patient_results: Dict[str, PatientMigrationStatus]) -> Dict[str, float]:
        """Calculate average scores by quality dimension"""
        dimension_sums = defaultdict(float)
        dimension_counts = defaultdict(int)
        
        for status in patient_results.values():
            for dimension, score in status.quality_by_dimension.items():
                dimension_sums[dimension] += score
                dimension_counts[dimension] += 1
        
        return {
            dimension: dimension_sums[dimension] / dimension_counts[dimension]
            for dimension in dimension_sums
            if dimension_counts[dimension] > 0
        }
    
    def _update_migration_metrics(self, batch_results: Dict[str, Any]) -> None:
        """Update overall migration metrics"""
        with self._lock:
            summary = batch_results["summary"]
            quality = batch_results["quality_metrics"]
            alerts = batch_results["alert_metrics"]
            hipaa = batch_results["hipaa_compliance"]
            
            # Update basic metrics
            self.metrics.total_patients += summary["total_patients"]
            self.metrics.total_batches += 1
            self.metrics.successful_migrations += summary["successful_patients"]
            self.metrics.failed_migrations += (summary["total_patients"] - summary["successful_patients"])
            
            # Update quality metrics
            current_avg = self.metrics.average_quality_score
            total_batches = self.metrics.total_batches
            self.metrics.average_quality_score = (
                (current_avg * (total_batches - 1) + summary["average_quality_score"]) / total_batches
            )
            
            # Update alert metrics
            self.metrics.total_alerts += alerts["total_alerts"]
            self.metrics.critical_alerts += alerts["critical_alerts"]
            self.metrics.unresolved_alerts += alerts["alerts_requiring_intervention"]
            
            # Update HIPAA metrics
            self.metrics.hipaa_compliance_rate = (
                (self.metrics.hipaa_compliance_rate * (total_batches - 1) + hipaa["average_compliance_score"]) / total_batches
            )
            self.metrics.phi_exposure_incidents += hipaa["phi_exposure_incidents"]
            
            # Update trend data
            now = datetime.now()
            self.metrics.quality_trend_data.append((now, summary["average_quality_score"]))
            self.metrics.alert_trend_data.append((now, alerts["total_alerts"]))
            
            # Keep only recent trend data (last 100 points)
            if len(self.metrics.quality_trend_data) > 100:
                self.metrics.quality_trend_data = self.metrics.quality_trend_data[-100:]
            if len(self.metrics.alert_trend_data) > 100:
                self.metrics.alert_trend_data = self.metrics.alert_trend_data[-100:]
    
    def _update_dashboard_data(self) -> None:
        """Update real-time dashboard data"""
        with self._lock:
            self.real_time_dashboard_data = {
                "timestamp": datetime.now(),
                "migration_summary": {
                    "total_patients": self.metrics.total_patients,
                    "total_batches": self.metrics.total_batches,
                    "success_rate": (
                        self.metrics.successful_migrations / self.metrics.total_patients 
                        if self.metrics.total_patients > 0 else 0.0
                    ),
                    "average_quality": self.metrics.average_quality_score
                },
                "quality_status": self.quality_monitor.get_quality_dashboard_data(),
                "hipaa_compliance": {
                    "compliance_rate": self.metrics.hipaa_compliance_rate,
                    "phi_incidents": self.metrics.phi_exposure_incidents,
                    "status": "COMPLIANT" if self.metrics.hipaa_compliance_rate >= 0.95 else "NON_COMPLIANT"
                },
                "active_alerts": {
                    "critical": len(self.quality_monitor.get_active_alerts(AlertSeverity.CRITICAL)),
                    "high": len(self.quality_monitor.get_active_alerts(AlertSeverity.HIGH)),
                    "medium": len(self.quality_monitor.get_active_alerts(AlertSeverity.MEDIUM)),
                    "low": len(self.quality_monitor.get_active_alerts(AlertSeverity.LOW))
                },
                "trends": {
                    "quality_trend": self.metrics.quality_trend_data[-10:],  # Last 10 points
                    "alert_trend": self.metrics.alert_trend_data[-10:]
                }
            }
    
    def get_patient_migration_status(self, patient_id: str) -> Optional[PatientMigrationStatus]:
        """Get detailed migration status for a specific patient"""
        return self.patient_statuses.get(patient_id)
    
    def get_hipaa_compliance_status(self, patient_id: str) -> Optional[HIPAAComplianceTracker]:
        """Get HIPAA compliance status for a specific patient"""
        return self.hipaa_trackers.get(patient_id)
    
    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get current real-time dashboard data"""
        with self._lock:
            return self.real_time_dashboard_data.copy()
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report"""
        with self._lock:
            return {
                "report_timestamp": datetime.now(),
                "migration_metrics": self.metrics,
                "active_alerts": self.quality_monitor.get_active_alerts(),
                "quality_dashboard": self.quality_monitor.get_quality_dashboard_data(),
                "patient_summary": {
                    "total_tracked": len(self.patient_statuses),
                    "quality_distribution": self._get_overall_quality_distribution(),
                    "critical_data_issues": self._get_critical_data_issues()
                },
                "hipaa_summary": {
                    "total_tracked": len(self.hipaa_trackers),
                    "compliance_distribution": self._get_hipaa_compliance_distribution(),
                    "violation_summary": self._get_violation_summary()
                },
                "recommendations": self._generate_recommendations()
            }
    
    def _get_overall_quality_distribution(self) -> Dict[str, int]:
        """Get overall quality score distribution"""
        scores = [status.current_quality_score for status in self.patient_statuses.values()]
        return self._calculate_quality_distribution(scores)
    
    def _get_critical_data_issues(self) -> List[Dict[str, Any]]:
        """Get summary of critical data integrity issues"""
        issues = []
        
        for patient_id, status in self.patient_statuses.items():
            if not status.critical_data_intact or status.clinical_validation_errors:
                issues.append({
                    "patient_id": patient_id,
                    "mrn": status.mrn,
                    "quality_score": status.current_quality_score,
                    "critical_data_intact": status.critical_data_intact,
                    "validation_errors": status.clinical_validation_errors,
                    "degradation_events": len(status.quality_degradation_events)
                })
        
        return sorted(issues, key=lambda x: x["quality_score"])
    
    def _get_hipaa_compliance_distribution(self) -> Dict[str, int]:
        """Get HIPAA compliance score distribution"""
        scores = [tracker.compliance_score for tracker in self.hipaa_trackers.values()]
        distribution = {"compliant": 0, "minor_issues": 0, "major_issues": 0, "non_compliant": 0}
        
        for score in scores:
            if score >= 0.95:
                distribution["compliant"] += 1
            elif score >= 0.85:
                distribution["minor_issues"] += 1
            elif score >= 0.70:
                distribution["major_issues"] += 1
            else:
                distribution["non_compliant"] += 1
        
        return distribution
    
    def _get_violation_summary(self) -> Dict[str, int]:
        """Get summary of HIPAA violations"""
        violation_types = defaultdict(int)
        
        for tracker in self.hipaa_trackers.values():
            for violation in tracker.violations:
                violation_types[violation["violation_type"]] += 1
        
        return dict(violation_types)
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on migration results"""
        recommendations = []
        
        # Quality-based recommendations
        if self.metrics.average_quality_score < 0.8:
            recommendations.append(
                "Consider implementing additional data validation checkpoints to improve overall quality scores"
            )
        
        if self.metrics.critical_alerts > self.metrics.total_batches * 2:
            recommendations.append(
                "High number of critical alerts detected - review migration process for systemic issues"
            )
        
        # HIPAA compliance recommendations
        if self.metrics.hipaa_compliance_rate < 0.95:
            recommendations.append(
                "HIPAA compliance rate below acceptable threshold - strengthen PHI protection measures"
            )
        
        if self.metrics.phi_exposure_incidents > 0:
            recommendations.append(
                "PHI exposure incidents detected - immediate review of security protocols required"
            )
        
        # Performance recommendations
        critical_issues = len(self._get_critical_data_issues())
        if critical_issues > 0:
            recommendations.append(
                f"{critical_issues} patients have critical data integrity issues - prioritize manual review"
            )
        
        return recommendations

# Export the enhanced simulator
__all__ = ['EnhancedMigrationSimulator', 'HIPAAComplianceTracker', 'EnhancedMigrationMetrics']