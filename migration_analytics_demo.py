#!/usr/bin/env python3
"""
Healthcare Migration Analytics Demo

This demonstration script showcases the comprehensive migration analytics and reporting
capabilities for healthcare data migrations. It demonstrates real-world scenarios
including VistA to Oracle Health migrations with FHIR, HL7, and HIPAA compliance.

Features Demonstrated:
- Executive dashboard analytics for C-suite reporting
- Technical performance reporting for IT operations
- Clinical data integrity reporting for medical staff
- Regulatory compliance reporting for legal teams
- Real-time monitoring with live dashboards
- Post-migration analysis with recommendations
- Multi-format report generation (JSON, HTML, PDF, CSV)
- Healthcare interoperability standards validation
- Patient safety metrics and clinical quality scoring
- Industry benchmarking and performance optimization

Usage:
    python migration_analytics_demo.py [--mode {executive|technical|clinical|compliance|realtime|full}]

Author: Healthcare Systems Architect
Date: 2025-09-09
"""

import asyncio
import json
import logging
import random
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import uuid

# Import our analytics components
from migration_analytics_engine import (
    HealthcareAnalyticsEngine,
    BusinessKPI,
    AnalyticsTimeframe,
    ReportFormat,
    ComplianceFramework,
    InteroperabilityStandard
)

from migration_report_generator import HealthcareReportGenerator

from real_time_dashboard import RealTimeDashboard, DashboardHTMLGenerator

from healthcare_interoperability_validator import (
    HealthcareInteroperabilityValidator,
    create_sample_fhir_patient,
    create_sample_hl7_message,
    InteroperabilityStandard as ValidatorStandard
)

from enhanced_migration_tracker import (
    PatientMigrationStatus,
    HealthcareDataQualityScorer,
    MigrationQualityMonitor,
    DataQualityDimension,
    ClinicalDataCriticality,
    AlertSeverity,
    MigrationStageStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [DEMO] %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationAnalyticsDemo:
    """Comprehensive demonstration of healthcare migration analytics"""
    
    def __init__(self):
        # Initialize core analytics engine
        self.analytics_engine = HealthcareAnalyticsEngine()
        
        # Initialize report generator
        self.report_generator = HealthcareReportGenerator(self.analytics_engine)
        
        # Initialize real-time dashboard
        self.dashboard = RealTimeDashboard(self.analytics_engine)
        
        # Initialize interoperability validator
        self.interop_validator = HealthcareInteroperabilityValidator()
        
        # Demo configuration
        self.demo_patients_count = 50
        self.demo_timeframe_hours = 24
        
        logger.info("Healthcare Migration Analytics Demo initialized")
    
    def run_full_demo(self):
        """Run comprehensive demonstration of all analytics capabilities"""
        print("\n" + "="*80)
        print("HEALTHCARE MIGRATION ANALYTICS & REPORTING SYSTEM DEMO")
        print("="*80)
        print(f"Demonstrating enterprise-grade analytics for healthcare data migrations")
        print(f"Focus: VistA → Oracle Health with FHIR R4/HL7 v2.x compliance")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        # 1. Generate synthetic migration data
        print("🏥 PHASE 1: Generating Synthetic Healthcare Migration Data")
        self.generate_synthetic_migration_data()
        
        # 2. Executive dashboard demo
        print("\n👔 PHASE 2: Executive Dashboard Analytics (C-Suite Reporting)")
        self.demo_executive_dashboard()
        
        # 3. Technical performance demo  
        print("\n🔧 PHASE 3: Technical Performance Analytics (IT Operations)")
        self.demo_technical_performance()
        
        # 4. Clinical integrity demo
        print("\n🩺 PHASE 4: Clinical Data Integrity Analytics (Medical Staff)")
        self.demo_clinical_integrity()
        
        # 5. Regulatory compliance demo
        print("\n⚖️  PHASE 5: Regulatory Compliance Analytics (Legal/Compliance)")
        self.demo_regulatory_compliance()
        
        # 6. Real-time monitoring demo
        print("\n📊 PHASE 6: Real-Time Migration Monitoring")
        self.demo_realtime_monitoring()
        
        # 7. Post-migration analysis demo
        print("\n📈 PHASE 7: Post-Migration Analysis & Recommendations")
        self.demo_post_migration_analysis()
        
        # 8. Interoperability validation demo
        print("\n🔗 PHASE 8: Healthcare Interoperability Validation")
        self.demo_interoperability_validation()
        
        # 9. Multi-format report generation demo
        print("\n📄 PHASE 9: Multi-Format Report Generation")
        self.demo_report_generation()
        
        print("\n" + "="*80)
        print("✅ DEMO COMPLETE - All analytics capabilities demonstrated")
        print("📁 Check 'generated_reports' directory for sample reports")
        print("🌐 Real-time dashboard available at: ws://localhost:8765")
        print("="*80 + "\n")
    
    def generate_synthetic_migration_data(self):
        """Generate realistic synthetic healthcare migration data"""
        print(f"   📋 Generating {self.demo_patients_count} synthetic patient migrations...")
        
        # Sample patient data with clinical context
        sample_patients = [
            {
                "first_name": "John", "last_name": "Smith", "mrn": "MRN12345678",
                "conditions": ["Type 2 Diabetes", "Hypertension"], 
                "medications": [{"medication": "Metformin", "dosage": "500mg"}],
                "allergies": [{"substance": "Penicillin", "reaction": "Rash", "severity": "Moderate"}]
            },
            {
                "first_name": "Sarah", "last_name": "Johnson", "mrn": "MRN23456789",
                "conditions": ["Asthma", "Seasonal Allergies"],
                "medications": [{"medication": "Albuterol", "dosage": "90mcg"}],
                "allergies": []
            },
            {
                "first_name": "Michael", "last_name": "Davis", "mrn": "MRN34567890", 
                "conditions": ["Coronary Artery Disease"],
                "medications": [{"medication": "Atorvastatin", "dosage": "20mg"}],
                "allergies": [{"substance": "Latex", "reaction": "Anaphylaxis", "severity": "Severe"}]
            },
            {
                "first_name": "Emily", "last_name": "Brown", "mrn": "MRN45678901",
                "conditions": ["Chronic Kidney Disease", "Diabetes"],
                "medications": [{"medication": "Lisinopril", "dosage": "10mg"}],
                "allergies": []
            },
            {
                "first_name": "Robert", "last_name": "Wilson", "mrn": "MRN56789012",
                "conditions": ["COPD", "Depression"],
                "medications": [{"medication": "Sertraline", "dosage": "50mg"}],
                "allergies": [{"substance": "Shellfish", "reaction": "Hives", "severity": "Mild"}]
            }
        ]
        
        migration_start_time = datetime.now() - timedelta(hours=self.demo_timeframe_hours)
        
        for i in range(self.demo_patients_count):
            # Use sample data with variation
            base_patient = sample_patients[i % len(sample_patients)]
            patient_id = str(uuid.uuid4())
            
            # Create patient migration status
            patient_status = PatientMigrationStatus(
                patient_id=patient_id,
                mrn=f"{base_patient['mrn'][:-2]}{i:02d}",
                patient_name=f"{base_patient['first_name']} {base_patient['last_name']}",
                migration_batch_id=f"BATCH-{datetime.now().strftime('%Y%m%d')}-{i//10 + 1:03d}"
            )
            
            # Simulate migration progress
            self._simulate_patient_migration(patient_status, base_patient, migration_start_time)
            
            # Register with analytics engine
            self.analytics_engine.register_patient_migration(patient_status)
        
        print(f"   ✅ Generated {self.demo_patients_count} patient migration records")
        print(f"   📊 Migration timeframe: {migration_start_time.strftime('%Y-%m-%d %H:%M')} to {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def _simulate_patient_migration(self, patient_status: PatientMigrationStatus, 
                                   patient_data: Dict[str, Any], start_time: datetime):
        """Simulate realistic patient migration with stages and quality variations"""
        stages = ["extract", "transform", "validate", "load"]
        current_time = start_time + timedelta(minutes=random.randint(0, self.demo_timeframe_hours * 60))
        
        # Set initial clinical data elements
        patient_status.clinical_data_elements = {
            "conditions": patient_data.get("conditions", []),
            "medications": patient_data.get("medications", []),
            "allergies": patient_data.get("allergies", []),
            "demographics": {
                "first_name": patient_data["first_name"],
                "last_name": patient_data["last_name"],
                "mrn": patient_status.mrn,
                "birthdate": "1975-06-15",  # Sample DOB
                "gender": random.choice(["male", "female"])
            }
        }
        
        # Set PHI protection status
        patient_status.phi_elements_count = 5  # SSN, Phone, Email, Address, DOB
        patient_status.phi_protection_status = {
            "ssn": True, "phone": True, "email": True, "address": True, "dob": True
        }
        
        # Simulate progression through stages
        for stage_idx, stage in enumerate(stages):
            patient_status.current_stage = stage
            patient_status.stage_statuses[stage] = MigrationStageStatus.IN_PROGRESS
            patient_status.stage_timestamps[stage] = current_time
            
            # Simulate stage duration (2-8 minutes per stage)
            stage_duration = random.uniform(120, 480)  # seconds
            patient_status.stage_durations[stage] = stage_duration
            
            # Simulate potential issues
            success_rate = 0.95 - (stage_idx * 0.02)  # Slightly lower success rate for later stages
            
            if random.random() > success_rate:
                # Introduce errors and quality degradation
                error_count = random.randint(1, 3)
                patient_status.stage_error_counts[stage] = error_count
                
                # Quality degradation
                quality_impact = random.uniform(0.05, 0.15)
                patient_status.current_quality_score = max(0.6, patient_status.current_quality_score - quality_impact)
                
                # Add quality degradation event
                degradation_event = {
                    "timestamp": current_time,
                    "stage": stage,
                    "type": random.choice(["data_corruption", "mapping_error", "validation_failure"]),
                    "impact": quality_impact,
                    "description": f"Quality degradation in {stage} stage"
                }
                patient_status.quality_degradation_events.append(degradation_event)
                
                # Potential HIPAA impact for critical errors
                if stage == "extract" and random.random() < 0.02:  # 2% chance
                    patient_status.hipaa_compliance_score = max(0.85, patient_status.hipaa_compliance_score - 0.1)
                    violation = {
                        "timestamp": current_time,
                        "framework": "HIPAA",
                        "type": "phi_exposure_risk",
                        "severity": "medium",
                        "description": "Potential PHI exposure during extraction"
                    }
                    patient_status.compliance_violations.append(violation)
                
                # Critical data integrity issues
                if random.random() < 0.01:  # 1% chance of critical data issues
                    patient_status.critical_data_intact = False
                    patient_status.clinical_validation_errors.append(
                        f"Critical data integrity issue in {stage}: medication dosage corruption"
                    )
                
                patient_status.stage_statuses[stage] = MigrationStageStatus.PARTIALLY_COMPLETED
            else:
                patient_status.stage_statuses[stage] = MigrationStageStatus.COMPLETED
            
            # Log migration event
            patient_status.log_event(f"stage_{stage}_completed", {
                "stage": stage,
                "duration_seconds": stage_duration,
                "error_count": patient_status.stage_error_counts.get(stage, 0),
                "quality_score": patient_status.current_quality_score
            })
            
            current_time += timedelta(seconds=stage_duration)
        
        # Set final status
        if all(status == MigrationStageStatus.COMPLETED for status in patient_status.stage_statuses.values()):
            patient_status.current_stage = "completed"
        elif any(status == MigrationStageStatus.FAILED for status in patient_status.stage_statuses.values()):
            patient_status.current_stage = "failed"
        else:
            patient_status.current_stage = "partially_completed"
        
        # Calculate dimension-specific quality scores
        scorer = HealthcareDataQualityScorer()
        overall_score, dimension_scores = scorer.calculate_patient_quality_score(patient_status.clinical_data_elements)
        patient_status.quality_by_dimension = dimension_scores
        
        patient_status.last_updated = current_time
    
    def demo_executive_dashboard(self):
        """Demonstrate executive dashboard analytics"""
        print("   📈 Calculating executive KPIs for C-suite reporting...")
        
        # Create timeframe for analysis
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, f"Last {self.demo_timeframe_hours} hours")
        
        # Calculate executive KPIs
        kpis = self.analytics_engine.calculate_executive_kpis(timeframe)
        
        print("   📊 Executive Dashboard KPIs:")
        for kpi_name, kpi in kpis.items():
            trend_icon = "📈" if kpi.trend == "improving" else "📉" if kpi.trend == "degrading" else "➡️"
            target_info = f" (Target: {kpi.target_value}{kpi.unit})" if kpi.target_value else ""
            print(f"      {trend_icon} {kpi.name}: {kpi.value:.1f}{kpi.unit}{target_info}")
        
        # Generate executive report
        report_path = self.report_generator.generate_executive_dashboard_report(timeframe, ReportFormat.HTML)
        print(f"   📄 Executive dashboard report generated: {report_path}")
    
    def demo_technical_performance(self):
        """Demonstrate technical performance analytics"""
        print("   🔧 Analyzing technical performance metrics for IT operations...")
        
        # Create timeframe
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, f"Last {self.demo_timeframe_hours} hours")
        
        # Calculate technical metrics
        technical_metrics = self.analytics_engine.calculate_technical_metrics(timeframe)
        
        print("   🖥️  Technical Performance Summary:")
        
        # Performance by stage
        if "performance_by_stage" in technical_metrics:
            print("      ⏱️  Stage Performance:")
            for stage, metrics in technical_metrics["performance_by_stage"].items():
                avg_duration = metrics.get("avg_duration_minutes", 0)
                throughput = metrics.get("throughput_patients_per_hour", 0)
                print(f"         {stage}: {avg_duration:.1f} min avg, {throughput:.1f} patients/hr")
        
        # Error analysis
        if "error_analysis" in technical_metrics:
            print("      ❌ Error Analysis:")
            for stage, error_count in technical_metrics["error_analysis"].items():
                print(f"         {stage}: {error_count} errors")
        
        # Resource utilization
        if "resource_utilization" in technical_metrics:
            print("      📊 System Resources:")
            for resource, value in technical_metrics["resource_utilization"].items():
                print(f"         {resource.replace('_', ' ').title()}: {value}")
        
        # Generate technical report
        report_path = self.report_generator.generate_technical_performance_report(timeframe, ReportFormat.HTML)
        print(f"   📄 Technical performance report generated: {report_path}")
    
    def demo_clinical_integrity(self):
        """Demonstrate clinical data integrity analytics"""
        print("   🩺 Analyzing clinical data integrity for patient safety...")
        
        # Create timeframe
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, f"Last {self.demo_timeframe_hours} hours")
        
        # Calculate clinical integrity metrics
        clinical_metrics = self.analytics_engine.calculate_clinical_integrity_metrics(timeframe)
        
        print("   🛡️  Clinical Data Integrity Summary:")
        
        # Critical data integrity
        if "critical_data_integrity" in clinical_metrics:
            integrity = clinical_metrics["critical_data_integrity"]
            integrity_rate = integrity.get("critical_data_integrity_rate", 1.0)
            total_patients = integrity.get("total_patients", 0)
            print(f"      ✅ Critical Data Integrity: {integrity_rate:.1%} ({total_patients} patients)")
        
        # Clinical quality by dimension
        if "clinical_quality_by_dimension" in clinical_metrics:
            print("      📏 Quality by Dimension:")
            for dimension, metrics in clinical_metrics["clinical_quality_by_dimension"].items():
                avg_score = metrics.get("average_score", 1.0)
                status_icon = "✅" if avg_score >= 0.95 else "⚠️" if avg_score >= 0.85 else "❌"
                print(f"         {status_icon} {dimension}: {avg_score:.1%}")
        
        # Patient safety risk
        if "patient_safety_risk" in clinical_metrics:
            risk_metrics = clinical_metrics["patient_safety_risk"]
            high_risk_count = risk_metrics.get("high_risk_patients_count", 0)
            overall_risk = risk_metrics.get("overall_risk_score", 0.0)
            print(f"      🚨 Patient Safety: {high_risk_count} high-risk patients, risk score: {overall_risk:.2f}")
        
        # Generate clinical report
        report_path = self.report_generator.generate_clinical_integrity_report(timeframe, ReportFormat.HTML)
        print(f"   📄 Clinical integrity report generated: {report_path}")
    
    def demo_regulatory_compliance(self):
        """Demonstrate regulatory compliance analytics"""
        print("   ⚖️  Analyzing regulatory compliance for legal/compliance teams...")
        
        # Create timeframe
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, f"Last {self.demo_timeframe_hours} hours")
        
        # Calculate compliance metrics
        compliance_metrics = self.analytics_engine.calculate_compliance_metrics(timeframe)
        interop_metrics = self.analytics_engine.calculate_interoperability_metrics(timeframe)
        
        print("   📋 Regulatory Compliance Summary:")
        
        # Framework compliance
        for framework_name, metric in compliance_metrics.items():
            status_icon = "✅" if metric.is_compliant else "❌"
            compliance_pct = metric.compliance_percentage
            violations = metric.violations_count
            print(f"      {status_icon} {metric.framework.value.upper()}: {compliance_pct:.1f}% ({violations} violations)")
        
        print("   🔗 Interoperability Standards:")
        for standard_name, metric in interop_metrics.items():
            compliance_pct = metric.compliance_score * 100
            feature_completeness = metric.feature_completeness * 100
            status_icon = "✅" if compliance_pct >= 90 else "⚠️" if compliance_pct >= 80 else "❌"
            print(f"      {status_icon} {metric.standard.value.upper()}: {compliance_pct:.1f}% compliance, {feature_completeness:.1f}% features")
        
        # Generate compliance report
        report_path = self.report_generator.generate_regulatory_compliance_report(timeframe, ReportFormat.HTML)
        print(f"   📄 Regulatory compliance report generated: {report_path}")
    
    def demo_realtime_monitoring(self):
        """Demonstrate real-time monitoring capabilities"""
        print("   📊 Real-time monitoring dashboard capabilities...")
        
        # Get real-time dashboard data
        dashboard_data = self.analytics_engine.get_real_time_dashboard_data()
        
        print("   🔴 Live Migration Status:")
        active_migrations = dashboard_data.get("active_migrations", {})
        print(f"      👥 Active Patients: {active_migrations.get('total_patients', 0)}")
        
        by_stage = active_migrations.get("by_stage", {})
        for stage, count in by_stage.items():
            print(f"      📋 {stage}: {count} patients")
        
        # System health
        system_health = dashboard_data.get("system_health", {})
        print(f"   💚 System Status: {system_health.get('status', 'Unknown')}")
        print(f"   ⏱️  Uptime: {system_health.get('uptime_hours', 0):.1f} hours")
        
        # Quality status
        quality_status = dashboard_data.get("quality_status", {})
        total_alerts = quality_status.get("total_active_alerts", 0)
        intervention_required = quality_status.get("alerts_requiring_intervention", 0)
        print(f"   🚨 Active Alerts: {total_alerts} (intervention required: {intervention_required})")
        
        # Generate dashboard HTML
        dashboard_html = DashboardHTMLGenerator.generate_dashboard_html()
        dashboard_path = Path("generated_reports/real_time_dashboard.html")
        dashboard_path.parent.mkdir(exist_ok=True)
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)
        
        print(f"   📄 Real-time dashboard HTML generated: {dashboard_path}")
        print("   🌐 Start dashboard server: python -c \"import asyncio; from real_time_dashboard import RealTimeDashboard; from migration_analytics_engine import HealthcareAnalyticsEngine; asyncio.run(RealTimeDashboard(HealthcareAnalyticsEngine()).start_dashboard())\"")
    
    def demo_post_migration_analysis(self):
        """Demonstrate post-migration analysis and recommendations"""
        print("   📈 Generating post-migration analysis and recommendations...")
        
        # Create timeframe
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, f"Last {self.demo_timeframe_hours} hours")
        
        # Generate post-migration analysis
        analysis = self.analytics_engine.generate_post_migration_analysis(timeframe)
        
        print("   📊 Post-Migration Analysis Results:")
        
        # Migration summary
        summary = analysis.get("migration_summary", {})
        total_patients = summary.get("total_patients", 0)
        completion_rate = summary.get("completion_rate", 0)
        avg_quality_score = summary.get("average_quality_score", 0)
        print(f"      📋 Total Patients: {total_patients}")
        print(f"      ✅ Completion Rate: {completion_rate:.1%}")
        print(f"      🎯 Avg Quality Score: {avg_quality_score:.1%}")
        
        # Success metrics
        success_metrics = analysis.get("success_metrics", {})
        if "data_quality_metrics" in success_metrics:
            dq_metrics = success_metrics["data_quality_metrics"]
            patients_above_95 = dq_metrics.get("patients_above_95_percent", 0)
            print(f"      🏆 High Quality Patients (>95%): {patients_above_95}")
        
        # Top recommendations
        recommendations = analysis.get("recommendations", [])
        print("   💡 Top Recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            priority = rec.get("priority", "Medium")
            category = rec.get("category", "General")
            recommendation = rec.get("recommendation", "")
            print(f"      {i}. [{priority}] {category}: {recommendation}")
        
        # Risk assessment
        risk_assessment = analysis.get("risk_assessment", {})
        risk_level = risk_assessment.get("overall_risk_level", "Unknown")
        risk_factors = risk_assessment.get("risk_factors", [])
        print(f"   🚨 Overall Risk Level: {risk_level}")
        for risk_factor in risk_factors[:2]:  # Top 2 risk factors
            print(f"      ⚠️  {risk_factor}")
        
        # Generate post-migration report
        report_path = self.report_generator.generate_post_migration_analysis_report(timeframe, ReportFormat.HTML)
        print(f"   📄 Post-migration analysis report generated: {report_path}")
    
    def demo_interoperability_validation(self):
        """Demonstrate healthcare interoperability validation"""
        print("   🔗 Demonstrating healthcare interoperability standards validation...")
        
        # Create sample FHIR Patient resource
        fhir_patient = create_sample_fhir_patient()
        print("   👤 Validating sample FHIR R4 Patient resource...")
        
        # Validate FHIR resource
        fhir_result = self.interop_validator.validate_data(fhir_patient, ValidatorStandard.FHIR_R4)
        
        print(f"      ✅ FHIR Validation Result:")
        print(f"         Valid: {fhir_result.is_valid}")
        print(f"         Compliance Score: {fhir_result.compliance_score:.1%}")
        print(f"         Compliance Level: {fhir_result.compliance_level.value}")
        print(f"         Errors: {fhir_result.error_count}, Warnings: {fhir_result.warning_count}")
        
        # Create sample HL7 message
        hl7_message = create_sample_hl7_message()
        print("   📨 Validating sample HL7 v2.8 ADT message...")
        
        # Validate HL7 message
        hl7_result = self.interop_validator.validate_data(hl7_message, ValidatorStandard.HL7_V2)
        
        print(f"      ✅ HL7 Validation Result:")
        print(f"         Valid: {hl7_result.is_valid}")
        print(f"         Compliance Score: {hl7_result.compliance_score:.1%}")
        print(f"         Compliance Level: {hl7_result.compliance_level.value}")
        print(f"         Errors: {hl7_result.error_count}, Warnings: {hl7_result.warning_count}")
        
        # Generate compliance report
        validation_results = {
            "fhir_r4": fhir_result,
            "hl7_v2": hl7_result
        }
        
        compliance_report = self.interop_validator.generate_compliance_report(validation_results)
        overall_compliance = compliance_report.get("overall_compliance", {})
        
        print(f"   📊 Overall Interoperability Compliance:")
        print(f"      Score: {overall_compliance.get('score', 0):.1%}")
        print(f"      Level: {overall_compliance.get('level', 'Unknown')}")
        print(f"      Valid Standards: {overall_compliance.get('valid_standards_count', 0)}/{overall_compliance.get('standards_count', 0)}")
        
        # Save compliance report
        report_path = Path("generated_reports/interoperability_compliance_report.json")
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(compliance_report, f, indent=2, default=str)
        
        print(f"   📄 Interoperability compliance report saved: {report_path}")
    
    def demo_report_generation(self):
        """Demonstrate multi-format report generation"""
        print("   📄 Demonstrating multi-format report generation...")
        
        # Create timeframe
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=self.demo_timeframe_hours)
        timeframe = AnalyticsTimeframe(start_time, end_time, "Demo Migration Batch")
        
        formats = [ReportFormat.JSON, ReportFormat.HTML, ReportFormat.CSV]
        
        for report_format in formats:
            print(f"   📋 Generating executive report in {report_format.value.upper()} format...")
            
            try:
                report_path = self.report_generator.generate_executive_dashboard_report(
                    timeframe, report_format
                )
                file_size = Path(report_path).stat().st_size / 1024  # KB
                print(f"      ✅ {report_format.value.upper()} report: {report_path} ({file_size:.1f} KB)")
                
            except Exception as e:
                print(f"      ❌ Error generating {report_format.value} report: {e}")
        
        # Demonstrate Excel export
        try:
            print("   📊 Generating Excel report with multiple sheets...")
            kpis = self.analytics_engine.calculate_executive_kpis(timeframe)
            
            # Prepare data for Excel export
            excel_data = {
                "executive_kpis": {kpi_name: {
                    "value": kpi.value,
                    "unit": kpi.unit,
                    "target": kpi.target_value,
                    "trend": kpi.trend
                } for kpi_name, kpi in kpis.items()},
                "timestamp": datetime.now().isoformat()
            }
            
            excel_path = self.report_generator.export_to_excel(excel_data, "executive_dashboard")
            file_size = Path(excel_path).stat().st_size / 1024  # KB
            print(f"      ✅ Excel report: {excel_path} ({file_size:.1f} KB)")
            
        except Exception as e:
            print(f"      ⚠️  Excel export not available (missing openpyxl): {e}")
        
        print("   📁 All reports saved to 'generated_reports' directory")
    
    def run_mode_demo(self, mode: str):
        """Run demo for specific mode"""
        print(f"\n🎯 Running {mode.upper()} mode demonstration")
        print("="*60)
        
        # Always generate some data first
        self.generate_synthetic_migration_data()
        
        if mode == "executive":
            self.demo_executive_dashboard()
        elif mode == "technical":
            self.demo_technical_performance()
        elif mode == "clinical":
            self.demo_clinical_integrity()
        elif mode == "compliance":
            self.demo_regulatory_compliance()
        elif mode == "realtime":
            self.demo_realtime_monitoring()
        else:
            print(f"Unknown mode: {mode}")
            return
        
        print(f"\n✅ {mode.upper()} mode demonstration complete")

def main():
    """Main demonstration function"""
    parser = argparse.ArgumentParser(description="Healthcare Migration Analytics Demo")
    parser.add_argument(
        "--mode", 
        choices=["executive", "technical", "clinical", "compliance", "realtime", "full"],
        default="full",
        help="Demo mode to run (default: full)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path("generated_reports").mkdir(exist_ok=True)
    
    # Initialize and run demo
    demo = MigrationAnalyticsDemo()
    
    if args.mode == "full":
        demo.run_full_demo()
    else:
        demo.run_mode_demo(args.mode)

if __name__ == "__main__":
    main()