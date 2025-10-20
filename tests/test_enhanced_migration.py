#!/usr/bin/env python3
"""
Test Suite for Enhanced Healthcare Migration System

This comprehensive test suite validates all components of the enhanced healthcare data migration system:

1. Patient-level migration tracking functionality
2. Healthcare-specific quality scoring accuracy  
3. Data degradation simulation realism
4. Quality monitoring and alerting reliability
5. HIPAA compliance tracking completeness
6. Clinical data validation effectiveness
7. Configuration management robustness
8. Integration between all components

The test suite ensures enterprise-grade reliability for production healthcare migration scenarios.

Author: Healthcare Data Quality Engineer
Date: 2025-09-09
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

# Import the enhanced migration components
try:
    from src.core.enhanced_migration_tracker import (
        PatientMigrationStatus,
        HealthcareDataQualityScorer,
        ClinicalDataDegradationSimulator,
        MigrationQualityMonitor,
        DataQualityDimension,
        AlertSeverity,
        MigrationStageStatus
    )
    from src.core.enhanced_migration_simulator import (
        EnhancedMigrationSimulator,
        HIPAAComplianceTracker
    )
    from src.config.healthcare_migration_config import (
        HealthcareMigrationConfig,
        ClinicalValidationRule,
        ClinicalDataType
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all enhanced migration modules are in the Python path")
    exit(1)

# Mock PatientRecord class for testing
from dataclasses import dataclass, field

@dataclass
class MockPatientRecord:
    """Mock patient record for testing"""
    patient_id: str = ""
    mrn: str = ""
    first_name: str = "John"
    last_name: str = "Doe"
    birthdate: str = "1980-01-01"
    phone: str = "555-1234"
    email: str = "john.doe@example.com"
    address: str = "123 Main St"
    city: str = "Anytown"
    state: str = "CA"
    ssn: str = "123-45-6789"
    allergies: List[Dict] = field(default_factory=list)
    medications: List[Dict] = field(default_factory=list)
    conditions: List[Dict] = field(default_factory=list)
    observations: List[Dict] = field(default_factory=list)
    encounters: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.patient_id:
            self.patient_id = str(uuid.uuid4())
        if not self.mrn:
            self.mrn = f"MRN{uuid.uuid4().hex[:8]}"

class TestPatientMigrationTracking(unittest.TestCase):
    """Test patient-level migration tracking capabilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.patient_status = PatientMigrationStatus(
            patient_id="test_patient_001",
            mrn="MRN12345678",
            patient_name="Test Patient",
            migration_batch_id="test_batch_001"
        )
    
    def test_patient_status_initialization(self):
        """Test patient status object initialization"""
        self.assertEqual(self.patient_status.patient_id, "test_patient_001")
        self.assertEqual(self.patient_status.mrn, "MRN12345678")
        self.assertEqual(self.patient_status.current_stage, "extract")
        self.assertEqual(self.patient_status.initial_quality_score, 1.0)
        self.assertTrue(self.patient_status.critical_data_intact)
    
    def test_event_logging(self):
        """Test migration event logging functionality"""
        initial_events = len(self.patient_status.migration_events)
        
        self.patient_status.log_event("test_event", {"detail": "test_detail"})
        
        self.assertEqual(len(self.patient_status.migration_events), initial_events + 1)
        
        event = self.patient_status.migration_events[-1]
        self.assertEqual(event["event_type"], "test_event")
        self.assertEqual(event["details"]["detail"], "test_detail")
        self.assertIsInstance(event["timestamp"], datetime)
    
    def test_stage_status_tracking(self):
        """Test migration stage status tracking"""
        self.patient_status.stage_statuses["extract"] = MigrationStageStatus.IN_PROGRESS
        self.patient_status.stage_statuses["transform"] = MigrationStageStatus.COMPLETED
        self.patient_status.stage_statuses["validate"] = MigrationStageStatus.FAILED
        
        self.assertEqual(
            self.patient_status.stage_statuses["extract"], 
            MigrationStageStatus.IN_PROGRESS
        )
        self.assertEqual(
            self.patient_status.stage_statuses["transform"], 
            MigrationStageStatus.COMPLETED
        )
        self.assertEqual(
            self.patient_status.stage_statuses["validate"], 
            MigrationStageStatus.FAILED
        )

class TestHealthcareDataQualityScorer(unittest.TestCase):
    """Test healthcare-specific data quality scoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scorer = HealthcareDataQualityScorer()
        self.sample_patient_data = {
            "patient_id": "test_001",
            "mrn": "12345678",
            "first_name": "John",
            "last_name": "Doe",
            "birthdate": "1980-01-01",
            "phone": "ENCRYPTED_555-1234",
            "email": "ENCRYPTED_john.doe@example.com",
            "allergies": [
                {"substance": "Penicillin", "reaction": "Rash", "severity": "moderate"}
            ],
            "medications": [
                {"medication": "Metformin", "dosage": "500 mg", "frequency": "twice daily"}
            ],
            "conditions": [
                {"condition": "Diabetes", "icd10_code": "E11.9", "status": "active"}
            ],
            "observations": [
                {"type": "Blood Pressure", "value": "120/80", "unit": "mmHg"}
            ]
        }
    
    def test_quality_score_calculation(self):
        """Test overall quality score calculation"""
        overall_score, dimension_scores = self.scorer.calculate_patient_quality_score(
            self.sample_patient_data
        )
        
        self.assertIsInstance(overall_score, float)
        self.assertGreaterEqual(overall_score, 0.0)
        self.assertLessEqual(overall_score, 1.0)
        self.assertIsInstance(dimension_scores, dict)
        
        # Check that all expected dimensions are present
        expected_dimensions = [dim.value for dim in DataQualityDimension]
        for dimension in expected_dimensions:
            self.assertIn(dimension, dimension_scores)
    
    def test_demographic_completeness_validation(self):
        """Test demographic data completeness validation"""
        score = self.scorer._validate_critical_demographics(self.sample_patient_data)
        self.assertEqual(score, 1.0)  # All required fields present
        
        # Test with missing data
        incomplete_data = self.sample_patient_data.copy()
        incomplete_data["first_name"] = ""
        score = self.scorer._validate_critical_demographics(incomplete_data)
        self.assertLess(score, 1.0)
    
    def test_allergy_validation(self):
        """Test allergy information validation"""
        score = self.scorer._validate_allergy_completeness(self.sample_patient_data)
        self.assertGreaterEqual(score, 0.8)  # Complete allergy record
        
        # Test with incomplete allergy data
        incomplete_allergy_data = self.sample_patient_data.copy()
        incomplete_allergy_data["allergies"] = [{"substance": "Peanuts"}]  # Missing reaction and severity
        score = self.scorer._validate_allergy_completeness(incomplete_allergy_data)
        self.assertLess(score, 1.0)
    
    def test_mrn_accuracy_validation(self):
        """Test MRN format and accuracy validation"""
        score = self.scorer._validate_mrn_accuracy(self.sample_patient_data)
        self.assertGreaterEqual(score, 0.8)
        
        # Test with invalid MRN
        invalid_mrn_data = self.sample_patient_data.copy()
        invalid_mrn_data["mrn"] = "INVALID"
        score = self.scorer._validate_mrn_accuracy(invalid_mrn_data)
        self.assertEqual(score, 0.0)
    
    def test_phi_protection_validation(self):
        """Test PHI protection status validation"""
        score = self.scorer._validate_phi_protection(self.sample_patient_data)
        self.assertGreaterEqual(score, 0.8)  # PHI is encrypted/protected
        
        # Test with exposed PHI
        exposed_phi_data = self.sample_patient_data.copy()
        exposed_phi_data["phone"] = "555-1234"  # Unprotected
        exposed_phi_data["email"] = "john.doe@example.com"  # Unprotected
        score = self.scorer._validate_phi_protection(exposed_phi_data)
        self.assertLess(score, 1.0)

class TestDataDegradationSimulator(unittest.TestCase):
    """Test clinical data degradation simulation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.degradation_simulator = ClinicalDataDegradationSimulator()
        self.sample_patient_data = {
            "patient_id": "test_001",
            "first_name": "John",
            "last_name": "Doe",
            "medications": [
                {"medication": "Metformin", "dosage": "500 mg", "frequency": "twice daily"}
            ],
            "allergies": [
                {"substance": "Penicillin", "reaction": "Rash", "severity": "moderate"}
            ],
            "observations": [
                {"type": "Blood Pressure", "value": 125.5, "unit": "mmHg"}
            ]
        }
    
    def test_degradation_scenario_initialization(self):
        """Test that degradation scenarios are properly initialized"""
        scenarios = self.degradation_simulator.degradation_scenarios
        
        self.assertIsInstance(scenarios, dict)
        self.assertGreater(len(scenarios), 0)
        
        # Check that all scenarios have required fields
        for scenario_name, scenario in scenarios.items():
            self.assertIn("description", scenario)
            self.assertIn("probability", scenario)
            self.assertIn("impact_severity", scenario)
            self.assertIn("affected_fields", scenario)
            self.assertIn("degradation_type", scenario)
    
    def test_medication_dosage_corruption(self):
        """Test medication dosage corruption scenario"""
        original_data = self.sample_patient_data.copy()
        failure_context = {
            "failure_type": "data_corruption",
            "stage": "transform",
            "severity": 0.8
        }
        
        degraded_data, events = self.degradation_simulator.simulate_degradation(
            original_data, failure_context
        )
        
        self.assertIsInstance(degraded_data, dict)
        self.assertIsInstance(events, list)
        
        # Verify data structure is preserved
        self.assertIn("medications", degraded_data)
        self.assertIsInstance(degraded_data["medications"], list)
    
    def test_allergy_information_loss(self):
        """Test allergy information loss scenario"""
        original_data = self.sample_patient_data.copy()
        failure_context = {
            "failure_type": "data_loss",
            "stage": "extract",
            "severity": 0.6
        }
        
        degraded_data, events = self.degradation_simulator.simulate_degradation(
            original_data, failure_context
        )
        
        # Verify that some degradation may have occurred
        self.assertIsInstance(degraded_data, dict)
        self.assertIn("allergies", degraded_data)
    
    def test_date_format_inconsistency(self):
        """Test date format inconsistency scenario"""
        data_with_dates = self.sample_patient_data.copy()
        data_with_dates["birthdate"] = "1980-01-01"
        
        failure_context = {
            "failure_type": "format_error",
            "stage": "transform",
            "severity": 0.5
        }
        
        degraded_data, events = self.degradation_simulator.simulate_degradation(
            data_with_dates, failure_context
        )
        
        self.assertIsInstance(degraded_data, dict)

class TestQualityMonitor(unittest.TestCase):
    """Test quality monitoring and alerting system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.quality_scorer = HealthcareDataQualityScorer()
        self.quality_monitor = MigrationQualityMonitor(self.quality_scorer)
        
        self.patient_status = PatientMigrationStatus(
            patient_id="test_patient_001",
            mrn="MRN12345678",
            patient_name="Test Patient",
            migration_batch_id="test_batch_001"
        )
        
        self.sample_patient_data = {
            "patient_id": "test_patient_001",
            "mrn": "MRN12345678",
            "first_name": "John",
            "last_name": "Doe",
            "birthdate": "1980-01-01"
        }
    
    def test_quality_monitoring(self):
        """Test patient quality monitoring functionality"""
        alerts = self.quality_monitor.monitor_patient_quality(
            self.patient_status, self.sample_patient_data
        )
        
        self.assertIsInstance(alerts, list)
        
        # Check that quality scores are updated
        self.assertIsNotNone(self.patient_status.current_quality_score)
        self.assertIsInstance(self.patient_status.quality_by_dimension, dict)
    
    def test_alert_generation(self):
        """Test alert generation for quality issues"""
        # Create data with quality issues
        poor_quality_data = {
            "patient_id": "test_patient_001",
            "mrn": "",  # Missing MRN
            "first_name": "",  # Missing name
            "last_name": "",
            "birthdate": "invalid_date"
        }
        
        alerts = self.quality_monitor.monitor_patient_quality(
            self.patient_status, poor_quality_data
        )
        
        # Should generate alerts for poor quality
        self.assertGreater(len(alerts), 0)
        
        # Check alert structure
        for alert in alerts:
            self.assertIsInstance(alert.alert_id, str)
            self.assertIsInstance(alert.severity, AlertSeverity)
            self.assertIsInstance(alert.dimension, DataQualityDimension)
            self.assertIsInstance(alert.message, str)
    
    def test_dashboard_data_generation(self):
        """Test quality dashboard data generation"""
        dashboard_data = self.quality_monitor.get_quality_dashboard_data()
        
        self.assertIsInstance(dashboard_data, dict)
        self.assertIn("timestamp", dashboard_data)
        self.assertIn("alert_summary", dashboard_data)
        self.assertIn("system_status", dashboard_data)
        
        # Check alert summary structure
        alert_summary = dashboard_data["alert_summary"]
        for severity in AlertSeverity:
            self.assertIn(severity.value, alert_summary)
    
    def test_alert_resolution(self):
        """Test alert resolution functionality"""
        # Generate an alert first
        poor_quality_data = {"patient_id": "test_001", "mrn": "", "first_name": ""}
        alerts = self.quality_monitor.monitor_patient_quality(
            self.patient_status, poor_quality_data
        )
        
        if alerts:
            alert_id = alerts[0].alert_id
            result = self.quality_monitor.resolve_alert(alert_id, "Resolved for testing")
            self.assertTrue(result)
            
            # Verify alert is marked as resolved
            resolved_alert = self.quality_monitor.active_alerts.get(alert_id)
            if resolved_alert:
                self.assertTrue(resolved_alert.resolved)

class TestHIPAAComplianceTracker(unittest.TestCase):
    """Test HIPAA compliance tracking functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.hipaa_tracker = HIPAAComplianceTracker(
            patient_id="test_patient_001",
            mrn="MRN12345678"
        )
    
    def test_phi_access_logging(self):
        """Test PHI access logging functionality"""
        initial_log_count = len(self.hipaa_tracker.phi_access_log)
        
        self.hipaa_tracker.log_phi_access(
            user_id="test_user",
            access_type="read",
            phi_element="demographics",
            justification="Migration processing"
        )
        
        self.assertEqual(
            len(self.hipaa_tracker.phi_access_log), 
            initial_log_count + 1
        )
        
        log_entry = self.hipaa_tracker.phi_access_log[-1]
        self.assertEqual(log_entry["user_id"], "test_user")
        self.assertEqual(log_entry["access_type"], "read")
        self.assertEqual(log_entry["phi_element"], "demographics")
    
    def test_violation_recording(self):
        """Test HIPAA violation recording"""
        initial_violation_count = len(self.hipaa_tracker.violations)
        initial_compliance_score = self.hipaa_tracker.compliance_score
        
        self.hipaa_tracker.record_violation(
            violation_type="phi_exposure",
            description="Test violation",
            severity="high"
        )
        
        self.assertEqual(
            len(self.hipaa_tracker.violations), 
            initial_violation_count + 1
        )
        self.assertLess(
            self.hipaa_tracker.compliance_score, 
            initial_compliance_score
        )
        
        violation = self.hipaa_tracker.violations[-1]
        self.assertEqual(violation["violation_type"], "phi_exposure")
        self.assertEqual(violation["severity"], "high")
        self.assertFalse(violation["resolved"])

class TestEnhancedMigrationSimulator(unittest.TestCase):
    """Test the enhanced migration simulator integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simulator = EnhancedMigrationSimulator()
        self.test_patient = MockPatientRecord()
        self.test_patient.allergies = [
            {"substance": "Penicillin", "reaction": "Rash", "severity": "moderate"}
        ]
        self.test_patient.medications = [
            {"medication": "Metformin", "dosage": "500 mg", "frequency": "twice daily"}
        ]
    
    def test_patient_migration_simulation(self):
        """Test individual patient migration simulation"""
        batch_id = "test_batch_001"
        
        patient_status = self.simulator.simulate_patient_migration(
            self.test_patient, batch_id
        )
        
        self.assertIsInstance(patient_status, PatientMigrationStatus)
        self.assertEqual(patient_status.patient_id, self.test_patient.patient_id)
        self.assertEqual(patient_status.migration_batch_id, batch_id)
        self.assertGreater(len(patient_status.migration_events), 0)
    
    def test_batch_migration_simulation(self):
        """Test batch migration simulation"""
        patients = [MockPatientRecord() for _ in range(5)]
        
        batch_results = self.simulator.simulate_batch_migration(patients)
        
        self.assertIsInstance(batch_results, dict)
        self.assertIn("summary", batch_results)
        self.assertIn("quality_metrics", batch_results)
        self.assertIn("alert_metrics", batch_results)
        self.assertIn("hipaa_compliance", batch_results)
        
        # Check summary data
        summary = batch_results["summary"]
        self.assertEqual(summary["total_patients"], len(patients))
        self.assertIsInstance(summary["success_rate"], float)
        self.assertIsInstance(summary["average_quality_score"], float)
    
    def test_comprehensive_report_generation(self):
        """Test comprehensive report generation"""
        # Run a small migration first
        patients = [MockPatientRecord() for _ in range(3)]
        self.simulator.simulate_batch_migration(patients)
        
        report = self.simulator.get_comprehensive_report()
        
        self.assertIsInstance(report, dict)
        self.assertIn("migration_metrics", report)
        self.assertIn("patient_summary", report)
        self.assertIn("hipaa_summary", report)
        self.assertIn("recommendations", report)
        
        # Check that recommendations are provided
        recommendations = report["recommendations"]
        self.assertIsInstance(recommendations, list)
    
    def test_real_time_dashboard(self):
        """Test real-time dashboard data"""
        dashboard = self.simulator.get_real_time_dashboard()
        
        self.assertIsInstance(dashboard, dict)
        self.assertIn("migration_summary", dashboard)
        self.assertIn("quality_status", dashboard)
        self.assertIn("hipaa_compliance", dashboard)
        self.assertIn("active_alerts", dashboard)

class TestHealthcareMigrationConfig(unittest.TestCase):
    """Test healthcare migration configuration management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = HealthcareMigrationConfig()
    
    def test_quality_threshold_retrieval(self):
        """Test quality threshold retrieval by criticality"""
        critical_completeness = self.config.get_quality_threshold("critical", "completeness")
        self.assertEqual(critical_completeness, 1.0)
        
        medium_accuracy = self.config.get_quality_threshold("medium", "accuracy")
        self.assertGreaterEqual(medium_accuracy, 0.8)
    
    def test_clinical_rules_by_type(self):
        """Test clinical validation rules by data type"""
        allergy_rules = self.config.get_clinical_rules_by_type(ClinicalDataType.ALLERGIES)
        self.assertIsInstance(allergy_rules, list)
        
        for rule in allergy_rules:
            self.assertIsInstance(rule, ClinicalValidationRule)
            self.assertEqual(rule.data_type, ClinicalDataType.ALLERGIES)
    
    def test_critical_data_types_identification(self):
        """Test identification of critical data types"""
        critical_types = self.config.get_critical_data_types()
        self.assertIsInstance(critical_types, list)
        
        # Should include allergies and medications as critical
        self.assertIn(ClinicalDataType.ALLERGIES, critical_types)
        self.assertIn(ClinicalDataType.MEDICATIONS, critical_types)
    
    def test_terminology_validation(self):
        """Test terminology code validation"""
        valid_icd10, message = self.config.validate_terminology_code("icd10_validation", "I10")
        self.assertTrue(valid_icd10)
        
        invalid_icd10, message = self.config.validate_terminology_code("icd10_validation", "INVALID")
        self.assertFalse(invalid_icd10)
    
    def test_batch_size_recommendation(self):
        """Test batch size recommendation by risk level"""
        high_risk_size = self.config.get_recommended_batch_size("high")
        medium_risk_size = self.config.get_recommended_batch_size("medium")
        low_risk_size = self.config.get_recommended_batch_size("low")
        
        self.assertLess(high_risk_size, medium_risk_size)
        self.assertLess(medium_risk_size, low_risk_size)
    
    def test_alert_trigger_determination(self):
        """Test alert trigger determination"""
        should_alert, severity = self.config.should_trigger_alert(0.6, "critical")
        self.assertTrue(should_alert)
        self.assertEqual(severity, "critical")
        
        should_alert, severity = self.config.should_trigger_alert(0.95, "low")
        self.assertFalse(should_alert)
    
    def test_config_export_import(self):
        """Test configuration export and import"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_filename = f.name
        
        try:
            # Export configuration
            self.config.export_config(temp_filename)
            self.assertTrue(os.path.exists(temp_filename))
            
            # Create new config and load from file
            new_config = HealthcareMigrationConfig()
            new_config.load_from_file(temp_filename)
            
            # Verify some key values are preserved
            self.assertEqual(
                new_config.quality_thresholds.critical_completeness,
                self.config.quality_thresholds.critical_completeness
            )
            
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

def run_comprehensive_test_suite():
    """Run the comprehensive test suite"""
    print("🧪 ENHANCED HEALTHCARE MIGRATION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("Running comprehensive validation of all enhanced migration capabilities...")
    print()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPatientMigrationTracking,
        TestHealthcareDataQualityScorer,
        TestDataDegradationSimulator,
        TestQualityMonitor,
        TestHIPAAComplianceTracker,
        TestEnhancedMigrationSimulator,
        TestHealthcareMigrationConfig
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = datetime.now()
    result = runner.run(test_suite)
    end_time = datetime.now()
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)
    
    duration = (end_time - start_time).total_seconds()
    print(f"⏱️  Total Test Duration: {duration:.2f} seconds")
    print(f"🧪 Tests Run: {result.testsRun}")
    print(f"✅ Successful: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ FAILED TESTS:")
        for test, traceback in result.failures:
            print(f"   • {test}")
    
    if result.errors:
        print(f"\n💥 ERROR TESTS:")
        for test, traceback in result.errors:
            print(f"   • {test}")
    
    # Overall result
    if result.wasSuccessful():
        print(f"\n🎉 ALL TESTS PASSED - System Ready for Production Use")
        print(f"   ✅ Patient-level migration tracking validated")
        print(f"   ✅ Healthcare quality scoring framework verified")
        print(f"   ✅ Data degradation simulation tested")
        print(f"   ✅ Quality monitoring and alerting confirmed")
        print(f"   ✅ HIPAA compliance tracking validated")
        print(f"   ✅ Configuration management verified")
        print(f"   ✅ End-to-end integration confirmed")
        
        return True
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Review Required Before Production")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test_suite()
    exit(0 if success else 1)
