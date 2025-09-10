#!/usr/bin/env python3
"""
Healthcare Migration Analytics Test Suite

Comprehensive test suite for the healthcare migration analytics and reporting system.
Tests all major components including analytics engine, report generation, real-time
monitoring, interoperability validation, and dashboard functionality.

Test Categories:
- Unit tests for core analytics calculations
- Integration tests for report generation
- Performance tests for real-time monitoring
- Compliance tests for healthcare standards
- End-to-end workflow tests
- Data quality validation tests
- Security and HIPAA compliance tests

Usage:
    python test_migration_analytics.py
    python -m pytest test_migration_analytics.py -v
    python test_migration_analytics.py --benchmark

Author: Healthcare Systems Architect
Date: 2025-09-09
"""

import unittest
import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Import components to test
from migration_analytics_engine import (
    HealthcareAnalyticsEngine,
    BusinessKPI,
    ComplianceMetric,
    InteroperabilityMetric,
    AnalyticsTimeframe,
    ReportFormat,
    ComplianceFramework,
    InteroperabilityStandard
)

from migration_report_generator import HealthcareReportGenerator

from real_time_dashboard import RealTimeDashboard, DashboardMetric, AlertManager

from healthcare_interoperability_validator import (
    HealthcareInteroperabilityValidator,
    FHIRValidator,
    HL7V2Validator,
    create_sample_fhir_patient,
    create_sample_hl7_message,
    ValidationResult,
    InteroperabilityStandard as ValidatorStandard,
    ValidationSeverity,
    ComplianceLevel
)

from enhanced_migration_tracker import (
    PatientMigrationStatus,
    HealthcareDataQualityScorer,
    MigrationQualityMonitor,
    DataQualityDimension,
    ClinicalDataCriticality,
    AlertSeverity,
    QualityAlert,
    MigrationStageStatus
)

class TestHealthcareAnalyticsEngine(unittest.TestCase):
    """Test suite for HealthcareAnalyticsEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analytics_engine = HealthcareAnalyticsEngine()
        self.sample_timeframe = AnalyticsTimeframe(
            start_time=datetime.now() - timedelta(hours=24),
            end_time=datetime.now(),
            description="Test timeframe"
        )
        
        # Create sample patient data
        self._create_sample_patients()
    
    def _create_sample_patients(self):
        """Create sample patient migration data for testing"""
        sample_data = [
            {
                "patient_id": str(uuid.uuid4()),
                "mrn": "MRN12345678",
                "name": "John Doe",
                "quality_score": 0.95,
                "hipaa_score": 0.98,
                "critical_data_intact": True,
                "stage": "completed"
            },
            {
                "patient_id": str(uuid.uuid4()),
                "mrn": "MRN23456789", 
                "name": "Jane Smith",
                "quality_score": 0.85,
                "hipaa_score": 0.92,
                "critical_data_intact": True,
                "stage": "load"
            },
            {
                "patient_id": str(uuid.uuid4()),
                "mrn": "MRN34567890",
                "name": "Bob Johnson",
                "quality_score": 0.75,
                "hipaa_score": 0.88,
                "critical_data_intact": False,
                "stage": "validate"
            }
        ]
        
        for data in sample_data:
            patient_status = PatientMigrationStatus(
                patient_id=data["patient_id"],
                mrn=data["mrn"],
                patient_name=data["name"],
                migration_batch_id="TEST-BATCH-001"
            )
            
            patient_status.current_quality_score = data["quality_score"]
            patient_status.hipaa_compliance_score = data["hipaa_score"]
            patient_status.critical_data_intact = data["critical_data_intact"]
            patient_status.current_stage = data["stage"]
            
            # Add stage durations
            patient_status.stage_durations = {
                "extract": 120.0,
                "transform": 180.0,
                "validate": 90.0,
                "load": 150.0
            }
            
            # Add clinical data elements
            patient_status.clinical_data_elements = {
                "first_name": data["name"].split()[0],
                "last_name": data["name"].split()[1],
                "mrn": data["mrn"],
                "birthdate": "1980-01-01",
                "medications": [{"medication": "Test Med", "dosage": "10mg"}],
                "allergies": [{"substance": "Penicillin", "reaction": "Rash", "severity": "Mild"}]
            }
            
            self.analytics_engine.register_patient_migration(patient_status)
    
    def test_executive_kpi_calculation(self):
        """Test executive KPI calculation"""
        kpis = self.analytics_engine.calculate_executive_kpis(self.sample_timeframe)
        
        # Verify KPIs are calculated
        self.assertIn("migration_success_rate", kpis)
        self.assertIn("data_quality_score", kpis)
        self.assertIn("hipaa_compliance", kpis)
        self.assertIn("patient_safety_incidents", kpis)
        
        # Verify KPI structure
        migration_kpi = kpis["migration_success_rate"]
        self.assertIsInstance(migration_kpi, BusinessKPI)
        self.assertGreaterEqual(migration_kpi.value, 0)
        self.assertLessEqual(migration_kpi.value, 100)
        self.assertEqual(migration_kpi.unit, "%")
        
        # Verify quality score calculation
        quality_kpi = kpis["data_quality_score"]
        self.assertGreaterEqual(quality_kpi.value, 0)
        self.assertLessEqual(quality_kpi.value, 100)
    
    def test_technical_metrics_calculation(self):
        """Test technical performance metrics calculation"""
        technical_metrics = self.analytics_engine.calculate_technical_metrics(self.sample_timeframe)
        
        # Verify metrics structure
        self.assertIn("performance_by_stage", technical_metrics)
        self.assertIn("error_analysis", technical_metrics)
        self.assertIn("resource_utilization", technical_metrics)
        
        # Verify stage performance metrics
        performance = technical_metrics["performance_by_stage"]
        for stage_metrics in performance.values():
            self.assertIn("avg_duration_minutes", stage_metrics)
            self.assertIn("throughput_patients_per_hour", stage_metrics)
            self.assertGreaterEqual(stage_metrics["avg_duration_minutes"], 0)
    
    def test_clinical_integrity_calculation(self):
        """Test clinical data integrity metrics"""
        clinical_metrics = self.analytics_engine.calculate_clinical_integrity_metrics(self.sample_timeframe)
        
        # Verify clinical metrics structure
        self.assertIn("critical_data_integrity", clinical_metrics)
        self.assertIn("patient_safety_risk", clinical_metrics)
        
        # Verify critical data integrity calculation
        integrity = clinical_metrics["critical_data_integrity"]
        self.assertIn("critical_data_integrity_rate", integrity)
        self.assertIn("total_patients", integrity)
        self.assertEqual(integrity["total_patients"], 3)  # Our sample data
        
        # Verify patient safety risk assessment
        safety_risk = clinical_metrics["patient_safety_risk"]
        self.assertIn("high_risk_patients_count", safety_risk)
        self.assertIn("overall_risk_score", safety_risk)
    
    def test_compliance_metrics_calculation(self):
        """Test regulatory compliance metrics"""
        compliance_metrics = self.analytics_engine.calculate_compliance_metrics(self.sample_timeframe)
        
        # Verify compliance frameworks are assessed
        self.assertIn("hipaa", compliance_metrics)
        self.assertIn("data_integrity", compliance_metrics)
        
        # Verify compliance metric structure
        hipaa_metric = compliance_metrics["hipaa"]
        self.assertIsInstance(hipaa_metric, ComplianceMetric)
        self.assertEqual(hipaa_metric.framework, ComplianceFramework.HIPAA)
        self.assertGreaterEqual(hipaa_metric.compliance_score, 0.0)
        self.assertLessEqual(hipaa_metric.compliance_score, 1.0)
    
    def test_real_time_dashboard_data(self):
        """Test real-time dashboard data generation"""
        dashboard_data = self.analytics_engine.get_real_time_dashboard_data()
        
        # Verify dashboard data structure
        self.assertIn("timestamp", dashboard_data)
        self.assertIn("active_migrations", dashboard_data)
        self.assertIn("system_health", dashboard_data)
        self.assertIn("performance_indicators", dashboard_data)
        
        # Verify active migrations data
        active_migrations = dashboard_data["active_migrations"]
        self.assertIn("total_patients", active_migrations)
        self.assertIn("by_stage", active_migrations)

class TestHealthcareReportGenerator(unittest.TestCase):
    """Test suite for HealthcareReportGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analytics_engine = HealthcareAnalyticsEngine()
        self.report_generator = HealthcareReportGenerator(self.analytics_engine)
        self.sample_timeframe = AnalyticsTimeframe(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            description="Test report timeframe"
        )
        
        # Create temporary directory for test reports
        self.test_dir = tempfile.mkdtemp()
        self.report_generator.output_dir = Path(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_executive_report_generation(self):
        """Test executive dashboard report generation"""
        # Test JSON format
        json_report_path = self.report_generator.generate_executive_dashboard_report(
            self.sample_timeframe, ReportFormat.JSON
        )
        
        self.assertTrue(Path(json_report_path).exists())
        
        # Verify JSON content
        with open(json_report_path, 'r') as f:
            report_data = json.load(f)
            self.assertIn("report_title", report_data)
            self.assertIn("kpis", report_data)
            self.assertIn("generated_at", report_data)
    
    def test_technical_report_generation(self):
        """Test technical performance report generation"""
        report_path = self.report_generator.generate_technical_performance_report(
            self.sample_timeframe, ReportFormat.JSON
        )
        
        self.assertTrue(Path(report_path).exists())
        
        # Verify report content
        with open(report_path, 'r') as f:
            report_data = json.load(f)
            self.assertIn("report_title", report_data)
            self.assertIn("performance_metrics", report_data)
    
    def test_csv_export(self):
        """Test CSV export functionality"""
        test_data = {
            "metric1": 100,
            "metric2": 200,
            "nested": {"value": 300}
        }
        
        csv_path = self.report_generator.export_to_csv(test_data, "test_export")
        self.assertTrue(Path(csv_path).exists())
        
        # Verify CSV content
        with open(csv_path, 'r') as f:
            content = f.read()
            self.assertIn("metric1", content)
            self.assertIn("100", content)
    
    def test_report_template_creation(self):
        """Test HTML template creation"""
        # This test verifies that templates are created
        template_dir = self.report_generator.template_dir
        self.assertTrue(template_dir.exists())
        
        # Check for executive template
        executive_template = template_dir / "executive_dashboard.html"
        self.assertTrue(executive_template.exists())

class TestInteroperabilityValidator(unittest.TestCase):
    """Test suite for Healthcare Interoperability Validator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = HealthcareInteroperabilityValidator()
        self.fhir_validator = FHIRValidator("R4")
        self.hl7_validator = HL7V2Validator("2.8")
    
    def test_fhir_patient_validation(self):
        """Test FHIR Patient resource validation"""
        patient = create_sample_fhir_patient()
        result = self.fhir_validator.validate(patient)
        
        # Verify validation result structure
        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.standard, ValidatorStandard.FHIR_R4)
        self.assertGreaterEqual(result.compliance_score, 0.0)
        self.assertLessEqual(result.compliance_score, 1.0)
        
        # Valid patient should pass validation
        self.assertTrue(result.is_valid)
        self.assertGreaterEqual(result.compliance_score, 0.8)
    
    def test_fhir_invalid_patient(self):
        """Test FHIR validation with invalid patient data"""
        invalid_patient = {
            "resourceType": "Patient",
            # Missing required elements
            "gender": "invalid_gender",  # Invalid enum value
            "birthDate": "invalid-date-format"  # Invalid date format
        }
        
        result = self.fhir_validator.validate(invalid_patient)
        
        # Should have validation errors
        self.assertGreater(len(result.errors), 0)
        self.assertLess(result.compliance_score, 1.0)
    
    def test_hl7_message_validation(self):
        """Test HL7 v2.x message validation"""
        hl7_message = create_sample_hl7_message()
        result = self.hl7_validator.validate(hl7_message)
        
        # Verify validation result
        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.standard, ValidatorStandard.HL7_V2)
        
        # Valid message should pass basic validation
        self.assertTrue(result.is_valid)
        self.assertGreaterEqual(result.compliance_score, 0.8)
    
    def test_hl7_invalid_message(self):
        """Test HL7 validation with invalid message"""
        invalid_message = "INVALID|MESSAGE|FORMAT"
        
        result = self.hl7_validator.validate(invalid_message)
        
        # Should have validation errors
        self.assertGreater(len(result.errors), 0)
        self.assertLess(result.compliance_score, 0.9)
    
    def test_compliance_report_generation(self):
        """Test compliance report generation"""
        # Validate both FHIR and HL7
        fhir_result = self.validator.validate_data(
            create_sample_fhir_patient(), ValidatorStandard.FHIR_R4
        )
        hl7_result = self.validator.validate_data(
            create_sample_hl7_message(), ValidatorStandard.HL7_V2
        )
        
        results = {"fhir_r4": fhir_result, "hl7_v2": hl7_result}
        report = self.validator.generate_compliance_report(results)
        
        # Verify report structure
        self.assertIn("report_timestamp", report)
        self.assertIn("overall_compliance", report)
        self.assertIn("standard_compliance", report)
        self.assertIn("recommendations", report)
        
        # Verify overall compliance calculation
        overall = report["overall_compliance"]
        self.assertIn("score", overall)
        self.assertIn("level", overall)
        self.assertGreaterEqual(overall["score"], 0.0)
        self.assertLessEqual(overall["score"], 1.0)

class TestDataQualityScoring(unittest.TestCase):
    """Test suite for Healthcare Data Quality Scoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.quality_scorer = HealthcareDataQualityScorer()
    
    def test_patient_quality_scoring(self):
        """Test patient data quality scoring"""
        sample_patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "birthdate": "1980-01-01",
            "mrn": "12345678",
            "medications": [
                {"medication": "Metformin", "dosage": "500mg"}
            ],
            "allergies": [
                {"substance": "Penicillin", "reaction": "Rash", "severity": "Mild"}
            ],
            "no_known_allergies": False
        }
        
        overall_score, dimension_scores = self.quality_scorer.calculate_patient_quality_score(sample_patient_data)
        
        # Verify scoring results
        self.assertGreaterEqual(overall_score, 0.0)
        self.assertLessEqual(overall_score, 1.0)
        self.assertIsInstance(dimension_scores, dict)
        
        # Verify dimension scores
        for dimension, score in dimension_scores.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
    
    def test_missing_data_scoring(self):
        """Test scoring with missing critical data"""
        incomplete_patient_data = {
            "first_name": "Jane",
            # Missing last_name, birthdate, mrn
            "medications": [],
            "allergies": []
        }
        
        overall_score, dimension_scores = self.quality_scorer.calculate_patient_quality_score(incomplete_patient_data)
        
        # Should have lower scores due to missing data
        self.assertLess(overall_score, 0.9)
        self.assertLess(dimension_scores["completeness"], 0.9)

class TestRealTimeDashboard(unittest.TestCase):
    """Test suite for Real-Time Dashboard"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analytics_engine = HealthcareAnalyticsEngine()
        self.dashboard = RealTimeDashboard(self.analytics_engine)
    
    def test_dashboard_metric_creation(self):
        """Test dashboard metric creation and updates"""
        metric = DashboardMetric("Test Metric", 100.0, "units", 90.0)
        
        self.assertEqual(metric.name, "Test Metric")
        self.assertEqual(metric.value, 100.0)
        self.assertEqual(metric.unit, "units")
        self.assertEqual(metric.threshold, 90.0)
        self.assertTrue(metric.is_critical)  # 100 > 90 threshold
        
        # Test metric update
        metric.update(85.0)
        self.assertEqual(metric.value, 85.0)
        self.assertFalse(metric.is_critical)  # 85 < 90 threshold
    
    def test_alert_manager(self):
        """Test alert management functionality"""
        alert_manager = AlertManager()
        
        # Create test alert
        test_alert = QualityAlert(
            alert_id="test-alert-001",
            patient_id="patient-123",
            mrn="MRN12345",
            severity=AlertSeverity.HIGH,
            dimension=DataQualityDimension.ACCURACY,
            message="Test alert message",
            threshold_value=0.9,
            actual_value=0.8,
            timestamp=datetime.now(),
            stage="test",
            substage="test"
        )
        
        # Add alert
        alert_manager.add_alert(test_alert)
        self.assertIn("test-alert-001", alert_manager.active_alerts)
        
        # Get alerts by severity
        high_alerts = alert_manager.get_alerts_by_severity(AlertSeverity.HIGH)
        self.assertEqual(len(high_alerts), 1)
        self.assertEqual(high_alerts[0].alert_id, "test-alert-001")
        
        # Resolve alert
        alert_manager.resolve_alert("test-alert-001", "Test resolution")
        self.assertTrue(alert_manager.active_alerts["test-alert-001"].resolved)
    
    def test_migration_status_summary(self):
        """Test migration status summary generation"""
        # Add test patient
        test_patient = PatientMigrationStatus(
            patient_id="test-patient",
            mrn="TEST123",
            patient_name="Test Patient",
            migration_batch_id="TEST-BATCH"
        )
        test_patient.current_stage = "load"
        
        self.analytics_engine.register_patient_migration(test_patient)
        
        # Get migration status
        status_summary = self.dashboard.get_migration_status_summary()
        
        self.assertIn("total_patients", status_summary)
        self.assertIn("by_stage", status_summary)
        self.assertIn("completion_percentage", status_summary)
        self.assertEqual(status_summary["total_patients"], 1)
        self.assertIn("load", status_summary["by_stage"])

class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarking tests"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.analytics_engine = HealthcareAnalyticsEngine()
        self.large_patient_count = 1000
        
        # Create large dataset for performance testing
        self._create_large_patient_dataset()
    
    def _create_large_patient_dataset(self):
        """Create large patient dataset for performance testing"""
        for i in range(self.large_patient_count):
            patient_status = PatientMigrationStatus(
                patient_id=str(uuid.uuid4()),
                mrn=f"MRN{i:08d}",
                patient_name=f"Patient {i}",
                migration_batch_id=f"PERF-BATCH-{i//100}"
            )
            
            patient_status.current_quality_score = 0.9 + (random.random() * 0.1)
            patient_status.hipaa_compliance_score = 0.95 + (random.random() * 0.05)
            patient_status.current_stage = random.choice(["extract", "transform", "validate", "load", "completed"])
            
            self.analytics_engine.register_patient_migration(patient_status)
    
    def test_kpi_calculation_performance(self):
        """Test KPI calculation performance with large dataset"""
        timeframe = AnalyticsTimeframe(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            description="Performance test"
        )
        
        # Measure KPI calculation time
        start_time = time.time()
        kpis = self.analytics_engine.calculate_executive_kpis(timeframe)
        calculation_time = time.time() - start_time
        
        # Performance assertion (should complete within reasonable time)
        self.assertLess(calculation_time, 5.0, f"KPI calculation took {calculation_time:.2f}s for {self.large_patient_count} patients")
        
        # Verify results are still accurate
        self.assertGreater(len(kpis), 0)
        for kpi in kpis.values():
            self.assertIsInstance(kpi, BusinessKPI)
    
    def test_dashboard_data_performance(self):
        """Test real-time dashboard data generation performance"""
        start_time = time.time()
        dashboard_data = self.analytics_engine.get_real_time_dashboard_data()
        generation_time = time.time() - start_time
        
        # Should be fast enough for real-time updates
        self.assertLess(generation_time, 2.0, f"Dashboard data generation took {generation_time:.2f}s")
        
        # Verify data completeness
        self.assertIn("active_migrations", dashboard_data)
        self.assertIn("system_health", dashboard_data)

class TestIntegrationWorkflow(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.analytics_engine = HealthcareAnalyticsEngine()
        self.report_generator = HealthcareReportGenerator(self.analytics_engine)
        self.validator = HealthcareInteroperabilityValidator()
        
        # Create test output directory
        self.test_dir = tempfile.mkdtemp()
        self.report_generator.output_dir = Path(self.test_dir)
    
    def tearDown(self):
        """Clean up integration test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_migration_workflow(self):
        """Test complete migration analytics workflow"""
        # 1. Create patient migration data
        patient_status = PatientMigrationStatus(
            patient_id=str(uuid.uuid4()),
            mrn="WORKFLOW123",
            patient_name="Workflow Test Patient",
            migration_batch_id="INTEGRATION-TEST"
        )
        
        patient_status.current_quality_score = 0.92
        patient_status.hipaa_compliance_score = 0.96
        patient_status.critical_data_intact = True
        patient_status.current_stage = "completed"
        
        self.analytics_engine.register_patient_migration(patient_status)
        
        # 2. Calculate analytics
        timeframe = AnalyticsTimeframe(
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            description="Integration test"
        )
        
        kpis = self.analytics_engine.calculate_executive_kpis(timeframe)
        technical_metrics = self.analytics_engine.calculate_technical_metrics(timeframe)
        clinical_metrics = self.analytics_engine.calculate_clinical_integrity_metrics(timeframe)
        
        # 3. Generate reports
        exec_report = self.report_generator.generate_executive_dashboard_report(timeframe, ReportFormat.JSON)
        tech_report = self.report_generator.generate_technical_performance_report(timeframe, ReportFormat.JSON)
        
        # 4. Validate results
        self.assertTrue(Path(exec_report).exists())
        self.assertTrue(Path(tech_report).exists())
        
        # Verify report content
        with open(exec_report, 'r') as f:
            exec_data = json.load(f)
            self.assertIn("kpis", exec_data)
            self.assertIn("compliance_metrics", exec_data)
        
        # 5. Test interoperability validation
        fhir_patient = create_sample_fhir_patient()
        fhir_result = self.validator.validate_data(fhir_patient, ValidatorStandard.FHIR_R4)
        
        self.assertTrue(fhir_result.is_valid)
        self.assertGreaterEqual(fhir_result.compliance_score, 0.8)
        
        print(f"✅ Integration test completed successfully")
        print(f"   Reports generated: {len([exec_report, tech_report])}")
        print(f"   FHIR compliance: {fhir_result.compliance_score:.1%}")

def run_benchmark_tests():
    """Run performance benchmark tests"""
    print("\n🏃 Running Performance Benchmarks...")
    print("="*50)
    
    # Create test loader and suite for benchmark tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add performance test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmarks))
    
    # Run benchmark tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ All benchmark tests passed")
    else:
        print("❌ Some benchmark tests failed")
        for failure in result.failures:
            print(f"   FAIL: {failure[0]}")
        for error in result.errors:
            print(f"   ERROR: {error[0]}")

def main():
    """Main test runner"""
    import sys
    
    print("🧪 Healthcare Migration Analytics Test Suite")
    print("="*60)
    
    # Check for benchmark flag
    if "--benchmark" in sys.argv:
        run_benchmark_tests()
        return
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestHealthcareAnalyticsEngine,
        TestHealthcareReportGenerator,
        TestInteroperabilityValidator,
        TestDataQualityScoring,
        TestRealTimeDashboard,
        TestIntegrationWorkflow
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("✅ All tests passed successfully!")
        print("\n🚀 System is ready for production healthcare migrations")
    else:
        print("❌ Some tests failed")
        print("\n🔧 Review failed tests before production deployment")
        
        if result.failures:
            print("\nFailures:")
            for failure in result.failures:
                print(f"   - {failure[0]}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"   - {error[0]}")

if __name__ == "__main__":
    # Add random import for test data generation
    import random
    main()