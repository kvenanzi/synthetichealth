#!/usr/bin/env python3
"""
Enhanced Healthcare Migration Simulator Demonstration

This comprehensive demo showcases the enhanced healthcare data migration capabilities including:

1. Granular patient-level tracking with clinical context
2. Healthcare-specific data quality scoring frameworks  
3. Data quality degradation simulation with clinical scenarios
4. Real-time quality monitoring and alerting systems
5. HIPAA compliance tracking and audit trails
6. Clinical data validation metrics and reporting
7. Production-ready dashboards and monitoring

The demo simulates realistic healthcare migration scenarios with enterprise-grade
quality management suitable for actual VistA-to-Oracle Health migrations.

Author: Healthcare Data Quality Engineer
Date: 2025-09-09
"""

import json
import random
import sys
import time
from datetime import datetime, timedelta
from faker import Faker
from typing import List, Dict, Any

# Import enhanced simulation components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.enhanced_migration_simulator import EnhancedMigrationSimulator, HIPAAComplianceTracker
from src.core.enhanced_migration_tracker import (
    AlertSeverity,
    DataQualityDimension,
    ClinicalDataCriticality,
    MigrationStageStatus
)

# Try to import existing patient generation, provide fallback if needed
try:
    from synthetic_patient_generator import PatientRecord, MigrationConfig
except ImportError:
    # Provide minimal fallback classes for demo
    from dataclasses import dataclass, field
    
    @dataclass
    class PatientRecord:
        patient_id: str = ""
        mrn: str = ""
        first_name: str = ""
        last_name: str = ""
        birthdate: str = ""
        phone: str = ""
        email: str = ""
        address: str = ""
        city: str = ""
        state: str = ""
        ssn: str = ""
        allergies: List[Dict] = field(default_factory=list)
        medications: List[Dict] = field(default_factory=list)
        conditions: List[Dict] = field(default_factory=list)
        observations: List[Dict] = field(default_factory=list)
        encounters: List[Dict] = field(default_factory=list)
        
        def __post_init__(self):
            if not self.patient_id:
                import uuid
                self.patient_id = str(uuid.uuid4())
    
    @dataclass  
    class MigrationConfig:
        stage_success_rates: Dict[str, float] = field(default_factory=lambda: {
            "extract": 0.98,
            "transform": 0.95,
            "validate": 0.92,
            "load": 0.90
        })
        network_failure_rate: float = 0.05
        system_overload_rate: float = 0.03
        quality_degradation_per_failure: float = 0.15

def create_realistic_test_patients(count: int = 25) -> List[PatientRecord]:
    """Create realistic test patients with comprehensive clinical data"""
    fake = Faker()
    patients = []
    
    print(f"Generating {count} realistic patients with comprehensive clinical data...")
    
    # Clinical data templates
    common_allergies = [
        {"substance": "Penicillin", "reaction": "Rash", "severity": "moderate"},
        {"substance": "Peanuts", "reaction": "Anaphylaxis", "severity": "severe"},
        {"substance": "Shellfish", "reaction": "Hives", "severity": "mild"},
        {"substance": "Latex", "reaction": "Contact dermatitis", "severity": "mild"}
    ]
    
    common_medications = [
        {"medication": "Metformin", "dosage": "500 mg", "frequency": "twice daily"},
        {"medication": "Lisinopril", "dosage": "10 mg", "frequency": "once daily"},
        {"medication": "Atorvastatin", "dosage": "20 mg", "frequency": "once daily"},
        {"medication": "Albuterol", "dosage": "90 mcg", "frequency": "as needed"}
    ]
    
    common_conditions = [
        {"condition": "Hypertension", "icd10_code": "I10", "onset_date": "2020-01-15", "status": "active"},
        {"condition": "Diabetes Type 2", "icd10_code": "E11.9", "onset_date": "2019-06-20", "status": "active"},
        {"condition": "Asthma", "icd10_code": "J45.9", "onset_date": "2018-03-10", "status": "active"}
    ]
    
    vital_signs_types = [
        {"type": "Blood Pressure", "unit": "mmHg"},
        {"type": "Heart Rate", "unit": "bpm"},
        {"type": "Temperature", "unit": "F"},
        {"type": "Weight", "unit": "lbs"},
        {"type": "Height", "unit": "inches"}
    ]
    
    for i in range(count):
        # Generate basic demographics
        first_name = fake.first_name()
        last_name = fake.last_name()
        birthdate = fake.date_of_birth(minimum_age=18, maximum_age=85).isoformat()
        
        # Generate MRN (8-digit format with check digit)
        mrn_base = fake.random_number(digits=7, fix_len=True)
        check_digit = (sum(int(d) for d in str(mrn_base)) % 10)
        mrn = f"{mrn_base}{check_digit}"
        
        # Create patient record
        patient = PatientRecord(
            first_name=first_name,
            last_name=last_name,
            birthdate=birthdate,
            phone=fake.phone_number(),
            email=fake.email(),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            mrn=mrn,
            ssn=fake.ssn()
        )
        
        # Add clinical data with realistic patterns
        
        # Allergies (70% have at least one allergy)
        if random.random() < 0.7:
            num_allergies = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
            patient.allergies = random.sample(common_allergies, min(num_allergies, len(common_allergies)))
        
        # Medications (80% have at least one medication)  
        if random.random() < 0.8:
            num_meds = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10])[0]
            patient.medications = random.sample(common_medications, min(num_meds, len(common_medications)))
        
        # Conditions (60% have at least one chronic condition)
        if random.random() < 0.6:
            num_conditions = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            patient.conditions = random.sample(common_conditions, min(num_conditions, len(common_conditions)))
        
        # Vital signs observations
        num_vitals = random.randint(2, 5)
        patient.observations = []
        for vital in random.sample(vital_signs_types, num_vitals):
            value = generate_realistic_vital_sign_value(vital["type"])
            patient.observations.append({
                "type": vital["type"],
                "value": value,
                "unit": vital["unit"],
                "date": fake.date_between(start_date='-1y', end_date='today').isoformat()
            })
        
        # Recent encounters
        num_encounters = random.randint(1, 4)
        encounter_types = ["Wellness Visit", "Emergency", "Follow-up", "Specialist"]
        patient.encounters = []
        for j in range(num_encounters):
            patient.encounters.append({
                "type": random.choice(encounter_types),
                "date": fake.date_between(start_date='-6m', end_date='today').isoformat(),
                "provider": fake.name(),
                "reason": fake.sentence(nb_words=4)
            })
        
        patients.append(patient)
    
    return patients

def generate_realistic_vital_sign_value(vital_type: str) -> str:
    """Generate realistic vital sign values"""
    if vital_type == "Blood Pressure":
        systolic = random.randint(110, 180)
        diastolic = random.randint(70, 100)
        return f"{systolic}/{diastolic}"
    elif vital_type == "Heart Rate":
        return str(random.randint(60, 100))
    elif vital_type == "Temperature":
        return f"{random.uniform(97.0, 99.5):.1f}"
    elif vital_type == "Weight":
        return str(random.randint(120, 250))
    elif vital_type == "Height":
        return str(random.randint(60, 76))
    else:
        return str(random.uniform(10.0, 200.0))

def demonstrate_enhanced_patient_tracking():
    """Demonstrate enhanced patient-level migration tracking"""
    print("\n" + "="*80)
    print("DEMONSTRATION 1: Enhanced Patient-Level Migration Tracking")
    print("="*80)
    
    # Create test patients
    patients = create_realistic_test_patients(5)
    
    # Initialize enhanced simulator
    config = MigrationConfig()
    config.stage_success_rates = {
        "extract": 0.95,
        "transform": 0.90,
        "validate": 0.85,
        "load": 0.80
    }
    
    simulator = EnhancedMigrationSimulator(config)
    
    print(f"\nSimulating migration for {len(patients)} patients with enhanced tracking...")
    
    # Process each patient individually to show detailed tracking
    for i, patient in enumerate(patients, 1):
        print(f"\n--- Processing Patient {i}: {patient.first_name} {patient.last_name} ---")
        print(f"MRN: {patient.mrn}")
        print(f"Clinical Profile: {len(patient.conditions)} conditions, {len(patient.medications)} medications, {len(patient.allergies)} allergies")
        
        # Simulate patient migration
        patient_status = simulator.simulate_patient_migration(patient, f"demo_batch_patient_tracking")
        
        # Display detailed status
        print(f"Initial Quality Score: {patient_status.initial_quality_score:.3f}")
        print(f"Final Quality Score: {patient_status.current_quality_score:.3f}")
        print(f"Quality Change: {patient_status.initial_quality_score - patient_status.current_quality_score:+.3f}")
        print(f"Critical Data Intact: {'✅' if patient_status.critical_data_intact else '❌'}")
        
        # Show stage results
        print("Stage Results:")
        for stage in ["extract", "transform", "validate", "load"]:
            status = patient_status.stage_statuses.get(stage, MigrationStageStatus.PENDING)
            duration = patient_status.stage_durations.get(stage, 0)
            errors = patient_status.stage_error_counts.get(stage, 0)
            
            status_icon = {"completed": "✅", "failed": "❌", "in_progress": "🔄", "pending": "⏳"}.get(
                status.value, "❓"
            )
            print(f"  {status_icon} {stage.capitalize()}: {status.value} ({duration:.2f}s, {errors} errors)")
        
        # Show quality dimension breakdown
        if patient_status.quality_by_dimension:
            print("Quality Dimensions:")
            for dimension, score in patient_status.quality_by_dimension.items():
                print(f"  {dimension.replace('_', ' ').title()}: {score:.3f}")
        
        # Show HIPAA compliance
        hipaa_tracker = simulator.get_hipaa_compliance_status(patient.patient_id)
        if hipaa_tracker:
            print(f"HIPAA Compliance Score: {hipaa_tracker.compliance_score:.3f}")
            if hipaa_tracker.violations:
                print(f"Compliance Violations: {len(hipaa_tracker.violations)}")
        
        print(f"Migration Events: {len(patient_status.migration_events)} logged")
        
        if patient_status.quality_degradation_events:
            print(f"Quality Degradation Events: {len(patient_status.quality_degradation_events)}")
            for event in patient_status.quality_degradation_events[:2]:  # Show first 2
                print(f"  - {event['failure_type']} in {event['stage']}.{event['substage']}: {event['quality_change']:.3f} quality loss")
    
    return simulator

def demonstrate_quality_monitoring_and_alerts():
    """Demonstrate real-time quality monitoring and alert system"""
    print("\n" + "="*80)
    print("DEMONSTRATION 2: Real-Time Quality Monitoring & Alert System")
    print("="*80)
    
    # Create challenging configuration to generate alerts
    config = MigrationConfig()
    config.stage_success_rates = {
        "extract": 0.85,    # Lower success rates to trigger issues
        "transform": 0.80,
        "validate": 0.75,
        "load": 0.70
    }
    config.quality_degradation_per_failure = 0.25  # Higher degradation
    
    simulator = EnhancedMigrationSimulator(config)
    
    # Process a batch to generate alerts
    patients = create_realistic_test_patients(15)
    print(f"Processing {len(patients)} patients with challenging configuration to demonstrate alerts...")
    
    batch_results = simulator.simulate_batch_migration(patients, "demo_batch_alerts")
    
    # Show alert summary
    print(f"\n📊 ALERT SYSTEM SUMMARY")
    print(f"Total Alerts Generated: {batch_results['alert_metrics']['total_alerts']}")
    print(f"Critical Alerts: {batch_results['alert_metrics']['critical_alerts']}")
    print(f"High Priority Alerts: {batch_results['alert_metrics']['high_alerts']}")
    print(f"Alerts Requiring Intervention: {batch_results['alert_metrics']['alerts_requiring_intervention']}")
    
    # Show active alerts by severity
    print(f"\n🚨 ACTIVE ALERTS BY SEVERITY:")
    for severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM]:
        alerts = simulator.quality_monitor.get_active_alerts(severity)
        if alerts:
            print(f"\n{severity.value.upper()} ALERTS ({len(alerts)}):")
            for alert in alerts[:3]:  # Show first 3 of each type
                print(f"  Patient {alert.mrn}: {alert.message}")
                print(f"    Dimension: {alert.dimension.value}, Stage: {alert.stage}.{alert.substage}")
                print(f"    Threshold: {alert.threshold_value:.3f}, Actual: {alert.actual_value:.3f}")
                if alert.requires_intervention:
                    print(f"    ⚠️  REQUIRES IMMEDIATE INTERVENTION")
    
    # Show quality dashboard data
    dashboard = simulator.quality_monitor.get_quality_dashboard_data()
    print(f"\n📈 QUALITY DASHBOARD STATUS:")
    print(f"System Status: {dashboard['system_status']}")
    print(f"Total Active Alerts: {dashboard['total_active_alerts']}")
    print(f"Alerts Requiring Intervention: {dashboard['alerts_requiring_intervention']}")
    
    # Show dimension breakdown
    if dashboard['dimension_breakdown']:
        print(f"\nAlerts by Quality Dimension:")
        for dimension, count in dashboard['dimension_breakdown'].items():
            print(f"  {dimension.replace('_', ' ').title()}: {count} alerts")
    
    return simulator, batch_results

def demonstrate_hipaa_compliance_tracking():
    """Demonstrate HIPAA compliance tracking and audit trails"""
    print("\n" + "="*80)
    print("DEMONSTRATION 3: HIPAA Compliance Tracking & Audit Trails")
    print("="*80)
    
    # Create configuration that may trigger HIPAA issues
    config = MigrationConfig()
    config.stage_success_rates = {
        "extract": 0.90,
        "transform": 0.85,
        "validate": 0.88,
        "load": 0.82
    }
    
    simulator = EnhancedMigrationSimulator(config)
    
    # Create patients with PHI data
    patients = create_realistic_test_patients(8)
    
    # Ensure some patients have PHI that could be exposed
    for i, patient in enumerate(patients):
        if i < 3:  # First 3 patients have unprotected PHI for demo
            patient.ssn = f"123-45-{6780 + i}"  # Realistic but fake SSN
            patient.phone = f"555-0{100 + i}"   # Unmasked phone
        else:
            patient.ssn = f"ENCRYPTED_{patient.ssn}"  # Protected
            patient.phone = f"***-***-{patient.phone[-4:]}"  # Masked
    
    print(f"Processing {len(patients)} patients with PHI protection analysis...")
    
    batch_results = simulator.simulate_batch_migration(patients, "demo_batch_hipaa")
    
    # Analyze HIPAA compliance results
    print(f"\n🔒 HIPAA COMPLIANCE ANALYSIS:")
    hipaa_summary = batch_results['hipaa_compliance']
    print(f"Average HIPAA Compliance Score: {hipaa_summary['average_compliance_score']:.3f}")
    print(f"PHI Exposure Incidents: {hipaa_summary['phi_exposure_incidents']}")
    print(f"Total HIPAA Violations: {hipaa_summary['total_violations']}")
    
    # Show individual patient compliance
    print(f"\n👤 PATIENT-LEVEL HIPAA COMPLIANCE:")
    for patient in patients[:5]:  # Show first 5 patients
        hipaa_tracker = simulator.get_hipaa_compliance_status(patient.patient_id)
        if hipaa_tracker:
            status_icon = "✅" if hipaa_tracker.compliance_score >= 0.95 else "⚠️" if hipaa_tracker.compliance_score >= 0.80 else "❌"
            print(f"  {status_icon} {patient.first_name} {patient.last_name} (MRN: {patient.mrn})")
            print(f"     Compliance Score: {hipaa_tracker.compliance_score:.3f}")
            print(f"     PHI Elements: {len(hipaa_tracker.phi_elements)}")
            print(f"     Access Log Entries: {len(hipaa_tracker.phi_access_log)}")
            
            if hipaa_tracker.violations:
                print(f"     Violations: {len(hipaa_tracker.violations)}")
                for violation in hipaa_tracker.violations:
                    print(f"       - {violation['violation_type']}: {violation['description']} ({violation['severity']})")
            
            # Show sample audit trail
            if hipaa_tracker.phi_access_log:
                print(f"     Recent PHI Access:")
                for access in hipaa_tracker.phi_access_log[-2:]:  # Last 2 accesses
                    print(f"       - {access['access_type']} {access['phi_element']} by {access['user_id']}")
    
    return simulator

def demonstrate_clinical_data_validation():
    """Demonstrate comprehensive clinical data validation metrics"""
    print("\n" + "="*80)
    print("DEMONSTRATION 4: Clinical Data Validation Metrics")
    print("="*80)
    
    simulator = EnhancedMigrationSimulator()
    
    # Create patients with various data quality issues for demonstration
    patients = create_realistic_test_patients(10)
    
    # Introduce specific clinical data issues for demo
    patients[0].allergies = []  # Missing allergy info
    patients[1].medications[0]["dosage"] = ""  # Missing dosage
    patients[2].conditions[0]["icd10_code"] = "INVALID_CODE"  # Invalid ICD code
    patients[3].observations = []  # No vital signs
    
    print(f"Processing {len(patients)} patients with clinical data validation...")
    
    batch_results = simulator.simulate_batch_migration(patients, "demo_batch_clinical")
    
    # Show clinical validation results
    print(f"\n🏥 CLINICAL DATA VALIDATION RESULTS:")
    quality_metrics = batch_results['quality_metrics']
    print(f"Quality Score Distribution: {quality_metrics['quality_score_distribution']}")
    print(f"Quality Degradation Events: {quality_metrics['quality_degradation_events']}")
    
    # Show dimension-specific results
    print(f"\nQuality by Clinical Dimension:")
    dimension_averages = quality_metrics['dimension_averages']
    for dimension, score in dimension_averages.items():
        criticality = "🔴 CRITICAL" if score < 0.7 else "🟡 NEEDS ATTENTION" if score < 0.85 else "🟢 GOOD"
        print(f"  {dimension.replace('_', ' ').title()}: {score:.3f} {criticality}")
    
    # Show patients with clinical validation issues
    print(f"\n⚕️ PATIENTS WITH CLINICAL VALIDATION ISSUES:")
    for patient in patients:
        patient_status = simulator.get_patient_migration_status(patient.patient_id)
        if patient_status and patient_status.clinical_validation_errors:
            print(f"  {patient.first_name} {patient.last_name} (MRN: {patient.mrn}):")
            print(f"    Quality Score: {patient_status.current_quality_score:.3f}")
            print(f"    Critical Data Intact: {'✅' if patient_status.critical_data_intact else '❌'}")
            print(f"    Validation Errors:")
            for error in patient_status.clinical_validation_errors:
                print(f"      - {error}")
    
    return simulator

def demonstrate_real_time_dashboard():
    """Demonstrate real-time migration dashboard capabilities"""
    print("\n" + "="*80)
    print("DEMONSTRATION 5: Real-Time Migration Dashboard")  
    print("="*80)
    
    simulator = EnhancedMigrationSimulator()
    
    # Process multiple batches to show trend data
    print("Processing multiple batches to demonstrate dashboard trends...")
    
    batch_sizes = [12, 15, 18, 10, 20]
    for i, batch_size in enumerate(batch_sizes, 1):
        patients = create_realistic_test_patients(batch_size)
        print(f"  Processing Batch {i}: {batch_size} patients...")
        
        batch_results = simulator.simulate_batch_migration(patients, f"dashboard_demo_batch_{i}")
        time.sleep(0.1)  # Small delay to show progression
    
    # Get comprehensive dashboard data
    dashboard = simulator.get_real_time_dashboard()
    
    print(f"\n📊 REAL-TIME MIGRATION DASHBOARD")
    print(f"=" * 50)
    
    # Migration summary
    migration_summary = dashboard['migration_summary']
    print(f"📈 MIGRATION SUMMARY:")
    print(f"  Total Patients Processed: {migration_summary['total_patients']}")
    print(f"  Total Batches Completed: {migration_summary['total_batches']}")
    print(f"  Overall Success Rate: {migration_summary['success_rate']:.1%}")
    print(f"  Average Quality Score: {migration_summary['average_quality']:.3f}")
    
    # Quality status
    quality_status = dashboard['quality_status']
    print(f"\n🎯 QUALITY STATUS:")
    print(f"  System Status: {quality_status['system_status']}")
    print(f"  Active Alerts: {quality_status['total_active_alerts']}")
    print(f"  Alerts Requiring Intervention: {quality_status['alerts_requiring_intervention']}")
    
    # HIPAA compliance
    hipaa_status = dashboard['hipaa_compliance']
    compliance_icon = "✅" if hipaa_status['status'] == "COMPLIANT" else "❌"
    print(f"\n🔒 HIPAA COMPLIANCE:")
    print(f"  Status: {hipaa_status['status']} {compliance_icon}")
    print(f"  Compliance Rate: {hipaa_status['compliance_rate']:.1%}")
    print(f"  PHI Incidents: {hipaa_status['phi_incidents']}")
    
    # Active alerts breakdown
    active_alerts = dashboard['active_alerts']
    print(f"\n🚨 ACTIVE ALERTS BREAKDOWN:")
    for severity, count in active_alerts.items():
        if count > 0:
            print(f"  {severity.upper()}: {count} alerts")
    
    # Show trends if available
    if dashboard['trends']['quality_trend']:
        print(f"\n📊 RECENT QUALITY TRENDS:")
        quality_trend = dashboard['trends']['quality_trend']
        for timestamp, quality in quality_trend[-5:]:  # Last 5 points
            print(f"  {timestamp.strftime('%H:%M:%S')}: {quality:.3f}")
    
    return simulator, dashboard

def generate_comprehensive_migration_report(simulator):
    """Generate and display comprehensive migration report"""
    print("\n" + "="*80)
    print("DEMONSTRATION 6: Comprehensive Migration Report")
    print("="*80)
    
    report = simulator.get_comprehensive_report()
    
    print(f"🔍 COMPREHENSIVE MIGRATION ANALYSIS REPORT")
    print(f"Generated: {report['report_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)
    
    # Migration metrics
    metrics = report['migration_metrics']
    print(f"\n📊 MIGRATION METRICS:")
    print(f"  Total Patients: {metrics.total_patients}")
    print(f"  Total Batches: {metrics.total_batches}")
    print(f"  Success Rate: {(metrics.successful_migrations / metrics.total_patients * 100) if metrics.total_patients > 0 else 0:.1f}%")
    print(f"  Average Quality Score: {metrics.average_quality_score:.3f}")
    print(f"  HIPAA Compliance Rate: {metrics.hipaa_compliance_rate:.1%}")
    
    # Patient summary
    patient_summary = report['patient_summary']
    print(f"\n👥 PATIENT SUMMARY:")
    print(f"  Total Patients Tracked: {patient_summary['total_tracked']}")
    print(f"  Quality Distribution: {patient_summary['quality_distribution']}")
    
    # Critical issues
    critical_issues = patient_summary['critical_data_issues']
    if critical_issues:
        print(f"\n⚠️ CRITICAL DATA ISSUES ({len(critical_issues)} patients):")
        for issue in critical_issues[:3]:  # Show top 3 issues
            print(f"  Patient MRN {issue['mrn']}:")
            print(f"    Quality Score: {issue['quality_score']:.3f}")
            print(f"    Critical Data Intact: {'No' if not issue['critical_data_intact'] else 'Yes'}")
            print(f"    Degradation Events: {issue['degradation_events']}")
            if issue['validation_errors']:
                print(f"    Validation Errors: {', '.join(issue['validation_errors'][:2])}")
    
    # HIPAA summary
    hipaa_summary = report['hipaa_summary']
    print(f"\n🔒 HIPAA COMPLIANCE SUMMARY:")
    print(f"  Patients Tracked: {hipaa_summary['total_tracked']}")
    print(f"  Compliance Distribution: {hipaa_summary['compliance_distribution']}")
    if hipaa_summary['violation_summary']:
        print(f"  Violation Types:")
        for violation_type, count in hipaa_summary['violation_summary'].items():
            print(f"    {violation_type.replace('_', ' ').title()}: {count}")
    
    # Recommendations
    recommendations = report['recommendations']
    if recommendations:
        print(f"\n💡 ACTIONABLE RECOMMENDATIONS:")
        for i, recommendation in enumerate(recommendations, 1):
            print(f"  {i}. {recommendation}")
    
    # Export report to file
    report_filename = f"enhanced_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert datetime objects to strings for JSON serialization
    def convert_datetime_for_json(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return {k: convert_datetime_for_json(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: convert_datetime_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_datetime_for_json(item) for item in obj]
        else:
            return obj
    
    serializable_report = convert_datetime_for_json(report)
    
    with open(report_filename, 'w') as f:
        json.dump(serializable_report, f, indent=2)
    
    print(f"\n💾 Full report exported to: {report_filename}")
    
    return report_filename

def main():
    """Main demonstration function showcasing all enhanced capabilities"""
    print("🏥 ENHANCED HEALTHCARE DATA MIGRATION SYSTEM")
    print("=" * 80)
    print("Comprehensive Demonstration of Enterprise-Grade Migration Capabilities")
    print()
    print("This demonstration showcases:")
    print("• Granular patient-level migration tracking with clinical context")
    print("• Healthcare-specific data quality scoring frameworks")
    print("• Data quality degradation simulation with clinical scenarios") 
    print("• Real-time quality monitoring and alerting systems")
    print("• HIPAA compliance tracking and audit trails")
    print("• Clinical data validation metrics and reporting")
    print("• Production-ready dashboards and comprehensive reporting")
    print()
    
    # Set seed for reproducible results
    random.seed(42)
    Faker.seed(42)
    
    try:
        start_time = datetime.now()
        
        # Run comprehensive demonstrations
        print("🚀 Starting comprehensive migration system demonstration...")
        
        # Demo 1: Enhanced patient tracking
        simulator1 = demonstrate_enhanced_patient_tracking()
        
        # Demo 2: Quality monitoring and alerts  
        simulator2, batch_results = demonstrate_quality_monitoring_and_alerts()
        
        # Demo 3: HIPAA compliance tracking
        simulator3 = demonstrate_hipaa_compliance_tracking()
        
        # Demo 4: Clinical data validation
        simulator4 = demonstrate_clinical_data_validation()
        
        # Demo 5: Real-time dashboard
        simulator5, dashboard = demonstrate_real_time_dashboard()
        
        # Demo 6: Comprehensive reporting
        report_file = generate_comprehensive_migration_report(simulator5)
        
        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        
        print(f"⏱️  Total Demonstration Time: {total_time:.2f} seconds")
        print(f"📁 Generated Files:")
        print(f"   • {report_file} - Comprehensive migration analysis report")
        print(f"   • migration_audit.log - HIPAA-compliant audit trail")
        
        print(f"\n🎯 KEY CAPABILITIES DEMONSTRATED:")
        print(f"   ✅ Granular patient-level migration tracking")
        print(f"   ✅ Healthcare-specific data quality scoring")
        print(f"   ✅ Clinical data degradation simulation")
        print(f"   ✅ Real-time quality monitoring & alerts")
        print(f"   ✅ HIPAA compliance tracking & audit trails")
        print(f"   ✅ Clinical data validation metrics")
        print(f"   ✅ Production-ready dashboards & reporting")
        
        print(f"\n🏆 ENTERPRISE-READY FEATURES:")
        print(f"   • Patient-level audit trails with HIPAA compliance")
        print(f"   • Real-time alerting for critical data quality issues")
        print(f"   • Comprehensive quality scoring with clinical context")
        print(f"   • Automated PHI protection monitoring")
        print(f"   • Clinical validation with healthcare-specific rules")
        print(f"   • Actionable recommendations for quality improvement")
        
        print(f"\n🎯 PRODUCTION USE CASES:")
        print(f"   • VistA-to-Oracle Health migration projects")
        print(f"   • Healthcare data quality assessment & monitoring")
        print(f"   • HIPAA compliance validation during migrations")
        print(f"   • Clinical data integrity verification")
        print(f"   • Migration risk assessment and mitigation planning")
        
        print(f"\n💡 This enhanced system provides healthcare organizations with")
        print(f"   enterprise-grade migration capabilities that ensure patient safety,")
        print(f"   regulatory compliance, and data quality throughout the migration process.")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()