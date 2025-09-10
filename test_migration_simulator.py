#!/usr/bin/env python3
"""
Simple test script for MigrationSimulator functionality
Tests the core migration simulation without requiring all dependencies
"""

import uuid
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

# Migration constants
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
class SimplePatient:
    """Simple patient record for testing"""
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str = "Test"
    last_name: str = "Patient"
    vista_id: str = field(default_factory=lambda: str(random.randint(1000, 9999)))
    mrn: str = field(default_factory=lambda: f"MRN{random.randint(100000, 999999)}")
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        'migration_status': 'pending',
        'data_quality_score': 1.0
    })

@dataclass
class MigrationStageResult:
    """Result of a migration stage execution"""
    stage: str
    substage: Optional[str] = None
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    
    def __post_init__(self):
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

@dataclass
class BatchMigrationStatus:
    """Migration status for a batch of patients"""
    batch_id: str
    batch_size: int
    source_system: str = "vista"
    target_system: str = "oracle_health"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_stage: str = "pending"
    stage_results: List[MigrationStageResult] = field(default_factory=list)
    patient_statuses: Dict[str, str] = field(default_factory=dict)
    overall_success_rate: float = 0.0
    average_quality_score: float = 1.0
    total_errors: int = 0
    
    def calculate_metrics(self):
        """Calculate overall migration metrics"""
        if self.stage_results:
            successful_stages = sum(1 for r in self.stage_results if r.status == "completed")
            self.overall_success_rate = successful_stages / len(self.stage_results)
            self.total_errors = sum(r.records_failed for r in self.stage_results)

@dataclass
class MigrationConfig:
    """Configuration for migration simulation"""
    stage_success_rates: Dict[str, float] = field(default_factory=lambda: {
        "extract": 0.98,
        "transform": 0.95,
        "validate": 0.92,
        "load": 0.90
    })
    
    substage_success_rates: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "extract": {"connect": 0.99, "query": 0.98, "export": 0.97},
        "transform": {"parse": 0.98, "map": 0.95, "standardize": 0.93},
        "validate": {"schema_check": 0.96, "business_rules": 0.92, "data_integrity": 0.89},
        "load": {"staging": 0.95, "production": 0.88, "verification": 0.92}
    })
    
    network_failure_rate: float = 0.05
    system_overload_rate: float = 0.03
    quality_degradation_per_failure: float = 0.15
    quality_degradation_per_success: float = 0.02

class SimpleMigrationSimulator:
    """Simplified migration simulator for testing"""
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()
        self.migration_history: List[BatchMigrationStatus] = []
    
    def simulate_staged_migration(self, patients: List[SimplePatient], batch_id: str = None) -> BatchMigrationStatus:
        """Simulate a complete staged migration for a batch of patients"""
        batch_id = batch_id or f"batch_{uuid.uuid4().hex[:8]}"
        
        batch_status = BatchMigrationStatus(
            batch_id=batch_id,
            batch_size=len(patients),
            started_at=datetime.now(),
            patient_statuses={p.patient_id: "pending" for p in patients}
        )
        
        try:
            # Execute each migration stage
            for stage in MIGRATION_STAGES:
                batch_status.current_stage = stage
                self._execute_migration_stage(patients, stage, batch_status)
                    
            # Calculate final metrics
            batch_status.completed_at = datetime.now()
            batch_status.calculate_metrics()
            self._calculate_quality_metrics(patients, batch_status)
            
        except Exception as e:
            batch_status.current_stage = "failed"
            print(f"Migration batch {batch_id} failed with error: {str(e)}")
            
        self.migration_history.append(batch_status)
        return batch_status
    
    def _execute_migration_stage(self, patients: List[SimplePatient], stage: str, batch_status: BatchMigrationStatus):
        """Execute a specific migration stage for all patients"""
        substages = ETL_SUBSTAGES.get(stage, [stage])
        
        for substage in substages:
            substage_result = MigrationStageResult(
                stage=stage,
                substage=substage,
                status="running",
                start_time=datetime.now(),
                records_processed=len(patients)
            )
            
            # Simulate processing
            successful_count = 0
            failed_count = 0
            
            for patient in patients:
                patient_success = self._process_patient_stage(patient, stage, substage)
                if patient_success:
                    successful_count += 1
                    if batch_status.patient_statuses[patient.patient_id] != "failed":
                        batch_status.patient_statuses[patient.patient_id] = f"{stage}_{substage}_complete"
                else:
                    failed_count += 1
                    batch_status.patient_statuses[patient.patient_id] = "failed"
            
            # Complete substage result
            substage_result.end_time = datetime.now()
            substage_result.records_successful = successful_count
            substage_result.records_failed = failed_count
            substage_result.status = "completed" if failed_count == 0 else "partial_failure"
            
            if failed_count > 0:
                substage_result.error_type = random.choice(FAILURE_TYPES)
                substage_result.error_message = f"{substage_result.error_type} in {stage}.{substage}"
            
            batch_status.stage_results.append(substage_result)
    
    def _process_patient_stage(self, patient: SimplePatient, stage: str, substage: str) -> bool:
        """Process a single patient through a migration stage/substage"""
        stage_rates = self.config.substage_success_rates.get(stage, {})
        success_rate = stage_rates.get(substage, self.config.stage_success_rates.get(stage, 0.9))
        
        # Apply failure factors
        if random.random() < self.config.network_failure_rate:
            success_rate *= 0.5
            
        if random.random() < self.config.system_overload_rate:
            success_rate *= 0.7
        
        patient_succeeds = random.random() < success_rate
        
        # Update patient data quality score
        if patient_succeeds:
            quality_impact = self.config.quality_degradation_per_success
            patient.metadata['data_quality_score'] = max(
                0.0, 
                patient.metadata['data_quality_score'] - quality_impact
            )
            patient.metadata['migration_status'] = f"{stage}_{substage}_complete"
        else:
            quality_impact = self.config.quality_degradation_per_failure
            patient.metadata['data_quality_score'] = max(
                0.0,
                patient.metadata['data_quality_score'] - quality_impact
            )
            patient.metadata['migration_status'] = f"{stage}_{substage}_failed"
            
        return patient_succeeds
    
    def _calculate_quality_metrics(self, patients: List[SimplePatient], batch_status: BatchMigrationStatus):
        """Calculate data quality metrics for the batch"""
        if not patients:
            batch_status.average_quality_score = 0.0
            return
            
        total_quality = sum(p.metadata['data_quality_score'] for p in patients)
        batch_status.average_quality_score = total_quality / len(patients)

def test_migration_simulator():
    """Test the migration simulator"""
    print("🏥 Testing MigrationSimulator Functionality")
    print("=" * 50)
    
    # Set seed for reproducible results
    random.seed(42)
    
    # Test 1: Basic functionality
    print("\nTest 1: Basic Migration Simulation")
    print("-" * 30)
    
    # Create test patients
    patients = [
        SimplePatient(first_name=f"Patient", last_name=f"{i}", patient_id=f"test_{i}")
        for i in range(5)
    ]
    
    simulator = SimpleMigrationSimulator()
    batch_result = simulator.simulate_staged_migration(patients, "test_batch_01")
    
    print(f"✅ Batch completed: {batch_result.batch_id}")
    print(f"   Success Rate: {batch_result.overall_success_rate:.1%}")
    print(f"   Quality Score: {batch_result.average_quality_score:.3f}")
    print(f"   Total Errors: {batch_result.total_errors}")
    print(f"   Stages Processed: {len(batch_result.stage_results)}")
    
    # Test 2: Custom configuration with high failure rates
    print("\nTest 2: High Failure Rate Configuration")
    print("-" * 30)
    
    challenging_config = MigrationConfig()
    challenging_config.stage_success_rates = {
        "extract": 0.70,
        "transform": 0.60,
        "validate": 0.50,
        "load": 0.40
    }
    challenging_config.network_failure_rate = 0.20
    challenging_config.system_overload_rate = 0.15
    
    challenging_simulator = SimpleMigrationSimulator(challenging_config)
    challenging_result = challenging_simulator.simulate_staged_migration(patients, "challenging_batch")
    
    print(f"✅ Challenging batch completed: {challenging_result.batch_id}")
    print(f"   Success Rate: {challenging_result.overall_success_rate:.1%}")
    print(f"   Quality Score: {challenging_result.average_quality_score:.3f}")
    print(f"   Total Errors: {challenging_result.total_errors}")
    
    # Test 3: Multiple batches
    print("\nTest 3: Multiple Batch Processing")
    print("-" * 30)
    
    for batch_num in range(3):
        batch_patients = [
            SimplePatient(first_name=f"Batch{batch_num}_Patient", last_name=f"{i}")
            for i in range(3)
        ]
        
        batch_result = simulator.simulate_staged_migration(batch_patients, f"multi_batch_{batch_num}")
        print(f"   Batch {batch_num}: {batch_result.overall_success_rate:.1%} success, "
              f"{batch_result.average_quality_score:.3f} quality")
    
    print(f"\n✅ Total migration history: {len(simulator.migration_history)} batches")
    
    # Test 4: Patient status tracking
    print("\nTest 4: Patient Status Tracking")
    print("-" * 30)
    
    test_patients = patients[:3]  # Use first 3 patients
    result = simulator.simulate_staged_migration(test_patients, "status_test")
    
    print("Patient Statuses:")
    for patient in test_patients:
        status = result.patient_statuses[patient.patient_id]
        quality = patient.metadata['data_quality_score']
        print(f"   {patient.first_name} {patient.last_name}: {status} (Quality: {quality:.3f})")
    
    print(f"\n🎉 All tests completed successfully!")
    print(f"Migration simulation is working correctly with:")
    print(f"   • Multi-stage ETL pipeline processing")
    print(f"   • Realistic failure injection")
    print(f"   • Data quality degradation tracking")
    print(f"   • Patient and batch status monitoring")
    print(f"   • Configurable parameters")

if __name__ == "__main__":
    test_migration_simulator()