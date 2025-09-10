#!/usr/bin/env python3
"""
Migration Simulator Demonstration

This script demonstrates the comprehensive MigrationSimulator class for VistA-to-Oracle Health
migration scenarios. It showcases realistic healthcare data migration simulation with:

- Multi-stage ETL pipeline (Extract → Transform → Validate → Load)
- Realistic failure injection and error handling
- Data quality degradation tracking
- Patient and batch-level status monitoring
- Migration analytics and reporting

Usage:
    python migration_demo.py
"""

import sys
import os
from datetime import datetime
import random
from faker import Faker

# Import our classes from the main generator
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.synthetic_patient_generator import (
    PatientRecord, 
    MigrationSimulator, 
    MigrationConfig,
    GENDERS, RACES, ETHNICITIES, MARITAL_STATUSES, LANGUAGES, INSURANCES
)

def create_sample_patients(num_patients=50):
    """Create sample patients for migration demonstration"""
    fake = Faker()
    patients = []
    
    print(f"Creating {num_patients} sample patients for migration testing...")
    
    for i in range(num_patients):
        # Generate realistic patient demographics
        birthdate = fake.date_of_birth(minimum_age=0, maximum_age=100)
        age = (datetime.now().date() - birthdate).days // 365
        
        patient = PatientRecord(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            middle_name=fake.first_name()[:1],
            gender=random.choice(GENDERS),
            birthdate=birthdate.isoformat(),
            age=age,
            race=random.choice(RACES),
            ethnicity=random.choice(ETHNICITIES),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            zip=fake.zipcode(),
            phone=fake.phone_number(),
            email=fake.email(),
            marital_status=random.choice(MARITAL_STATUSES),
            language=random.choice(LANGUAGES),
            insurance=random.choice(INSURANCES),
        )
        
        # Generate VistA and MRN identifiers
        patient.generate_vista_id()
        patient.generate_mrn()
        
        patients.append(patient)
    
    return patients

def demonstrate_basic_migration():
    """Demonstrate basic migration simulation with default settings"""
    print("\n" + "="*70)
    print("DEMONSTRATION 1: Basic Migration Simulation")
    print("="*70)
    
    # Create sample patients
    patients = create_sample_patients(20)
    
    # Initialize simulator with default configuration
    simulator = MigrationSimulator()
    
    # Run migration simulation
    print(f"\nSimulating migration for {len(patients)} patients...")
    batch_result = simulator.simulate_staged_migration(
        patients, 
        batch_id="demo_batch_01"
    )
    
    # Display results
    print(f"\nBatch Results:")
    print(f"  Batch ID: {batch_result.batch_id}")
    print(f"  Total Patients: {batch_result.batch_size}")
    print(f"  Overall Success Rate: {batch_result.overall_success_rate:.1%}")
    print(f"  Average Quality Score: {batch_result.average_quality_score:.3f}")
    print(f"  Total Errors: {batch_result.total_errors}")
    
    # Show stage-by-stage results
    print(f"\nStage Results:")
    for result in batch_result.stage_results:
        status_emoji = "✅" if result.status == "completed" else "⚠️" if result.status == "partial_failure" else "❌"
        print(f"  {status_emoji} {result.stage}.{result.substage}: {result.records_successful}/{result.records_processed} succeeded")
        if result.error_message:
            print(f"      Error: {result.error_message}")
    
    # Show some patient statuses
    print(f"\nSample Patient Statuses:")
    for i, (patient_id, status) in enumerate(list(batch_result.patient_statuses.items())[:5]):
        patient = next(p for p in patients if p.patient_id == patient_id)
        quality = patient.metadata['data_quality_score']
        print(f"  {patient.first_name} {patient.last_name} (MRN: {patient.mrn}): {status} (Quality: {quality:.3f})")
    
    return simulator

def demonstrate_custom_configuration():
    """Demonstrate migration with custom configuration for challenging scenarios"""
    print("\n" + "="*70)
    print("DEMONSTRATION 2: Custom Configuration - High Failure Scenario")
    print("="*70)
    
    # Create custom configuration with higher failure rates
    custom_config = MigrationConfig()
    
    # Simulate a challenging migration environment
    custom_config.stage_success_rates = {
        "extract": 0.85,    # Lower success rates
        "transform": 0.80,
        "validate": 0.75,
        "load": 0.70
    }
    
    custom_config.network_failure_rate = 0.15      # Higher network issues
    custom_config.system_overload_rate = 0.10      # More system problems
    custom_config.quality_degradation_per_failure = 0.25  # More quality loss
    
    patients = create_sample_patients(30)
    simulator = MigrationSimulator(custom_config)
    
    print("\nCustom Configuration:")
    print("  - Reduced success rates (70-85% per stage)")
    print("  - Increased network failure rate (15%)")
    print("  - Higher system overload rate (10%)")
    print("  - More quality degradation per failure")
    
    batch_result = simulator.simulate_staged_migration(
        patients, 
        batch_id="demo_batch_02_challenging",
        migration_strategy="staged"
    )
    
    print(f"\nResults with Challenging Configuration:")
    print(f"  Overall Success Rate: {batch_result.overall_success_rate:.1%}")
    print(f"  Average Quality Score: {batch_result.average_quality_score:.3f}")
    print(f"  Total Errors: {batch_result.total_errors}")
    
    # Show quality distribution
    quality_scores = [p.metadata['data_quality_score'] for p in patients]
    high_quality = sum(1 for q in quality_scores if q >= 0.9)
    medium_quality = sum(1 for q in quality_scores if 0.7 <= q < 0.9)
    low_quality = sum(1 for q in quality_scores if q < 0.7)
    
    print(f"\nData Quality Distribution:")
    print(f"  High Quality (≥0.9): {high_quality} patients ({high_quality/len(patients):.1%})")
    print(f"  Medium Quality (0.7-0.9): {medium_quality} patients ({medium_quality/len(patients):.1%})")
    print(f"  Low Quality (<0.7): {low_quality} patients ({low_quality/len(patients):.1%})")
    
    return simulator

def demonstrate_batch_processing():
    """Demonstrate large-scale batch processing with analytics"""
    print("\n" + "="*70)
    print("DEMONSTRATION 3: Large-Scale Batch Processing")
    print("="*70)
    
    # Create larger dataset
    total_patients = 200
    batch_size = 25
    patients = create_sample_patients(total_patients)
    
    # Production-like configuration
    prod_config = MigrationConfig()
    prod_config.stage_success_rates = {
        "extract": 0.98,
        "transform": 0.94,
        "validate": 0.91,
        "load": 0.88
    }
    
    simulator = MigrationSimulator(prod_config)
    
    print(f"Processing {total_patients} patients in batches of {batch_size}...")
    
    # Process in batches
    total_batches = (total_patients + batch_size - 1) // batch_size
    all_results = []
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_patients)
        batch_patients = patients[start_idx:end_idx]
        
        batch_id = f"prod_batch_{batch_num + 1:03d}"
        print(f"  Processing {batch_id}: {len(batch_patients)} patients...", end=" ")
        
        batch_result = simulator.simulate_staged_migration(
            batch_patients, 
            batch_id=batch_id
        )
        all_results.append(batch_result)
        
        print(f"Success: {batch_result.overall_success_rate:.1%}, Quality: {batch_result.average_quality_score:.3f}")
    
    # Generate comprehensive analytics
    print(f"\nGenerating comprehensive analytics for {len(all_results)} batches...")
    analytics = simulator.get_migration_analytics()
    
    return simulator, analytics

def demonstrate_analytics_and_reporting():
    """Demonstrate comprehensive analytics and reporting capabilities"""
    print("\n" + "="*70)
    print("DEMONSTRATION 4: Analytics and Reporting")
    print("="*70)
    
    # Run batch processing to get data
    simulator, analytics = demonstrate_batch_processing()
    
    print("\nCOMPREHENSIVE MIGRATION ANALYTICS")
    print("-" * 50)
    
    # Executive summary
    summary = analytics["summary"]
    print(f"Executive Summary:")
    print(f"  Total Batches: {summary['total_batches']}")
    print(f"  Total Patients: {summary['total_patients']}")
    print(f"  Overall Success Rate: {summary['overall_success_rate']:.2%}")
    print(f"  Average Data Quality: {summary['average_quality_score']:.4f}")
    print(f"  Total Errors: {summary['total_errors']}")
    
    # Stage performance
    if "stage_performance" in analytics:
        print(f"\nStage Performance Analysis:")
        for stage, stats in analytics["stage_performance"].items():
            print(f"  {stage.upper()}:")
            print(f"    Success Rate: {stats['success_rate']:.2%}")
            print(f"    Average Duration: {stats['average_duration']:.2f} seconds")
            print(f"    Total Executions: {stats['total_executions']}")
    
    # Failure analysis
    if "failure_analysis" in analytics:
        failure_analysis = analytics["failure_analysis"]
        if failure_analysis.get("failure_types"):
            print(f"\nFailure Type Analysis:")
            for failure_type, count in failure_analysis["failure_types"].items():
                print(f"  {failure_type}: {count} occurrences")
        
        if failure_analysis.get("most_common_failure"):
            print(f"  Most Common Failure: {failure_analysis['most_common_failure']}")
    
    # Quality trends
    if "quality_trends" in analytics:
        quality = analytics["quality_trends"]
        print(f"\nData Quality Trends:")
        print(f"  Initial Quality: {quality['initial_quality']:.4f}")
        print(f"  Final Quality: {quality['final_quality']:.4f}")
        print(f"  Quality Degradation: {quality['initial_quality'] - quality['final_quality']:.4f}")
        print(f"  Quality Range: {quality['min_quality']:.4f} - {quality['max_quality']:.4f}")
    
    # Timing analysis
    if "timing_analysis" in analytics:
        timing = analytics["timing_analysis"]
        if "average_batch_duration" in timing:
            print(f"\nTiming Analysis:")
            print(f"  Average Batch Duration: {timing['average_batch_duration']:.2f} seconds")
            print(f"  Fastest Batch: {timing['min_duration']:.2f} seconds")
            print(f"  Slowest Batch: {timing['max_duration']:.2f} seconds")
            print(f"  Total Migration Time: {timing['total_migration_time']:.2f} seconds")
    
    # Recommendations
    if "recommendations" in analytics:
        print(f"\nActionable Recommendations:")
        for i, recommendation in enumerate(analytics["recommendations"], 1):
            print(f"  {i}. {recommendation}")
    
    # Export detailed report
    report_file = "migration_demo_report.txt"
    simulator.export_migration_report(report_file)
    print(f"\nDetailed report exported to: {report_file}")
    
    return analytics

def main():
    """Main demonstration function"""
    print("🏥 VistA-to-Oracle Health Migration Simulator Demonstration")
    print("=" * 70)
    print("This demo showcases comprehensive healthcare data migration simulation")
    print("with realistic failure scenarios, data quality tracking, and analytics.")
    print()
    
    # Set random seed for reproducible results
    random.seed(42)
    Faker.seed(42)
    
    try:
        # Run all demonstrations
        demonstrate_basic_migration()
        demonstrate_custom_configuration()
        analytics = demonstrate_analytics_and_reporting()
        
        print("\n" + "="*70)
        print("DEMONSTRATION SUMMARY")
        print("="*70)
        print("✅ Basic migration simulation completed")
        print("✅ Custom configuration testing completed")
        print("✅ Large-scale batch processing completed")
        print("✅ Comprehensive analytics generated")
        print("✅ Detailed report exported")
        
        print("\nKey Features Demonstrated:")
        print("  • Multi-stage ETL pipeline (Extract → Transform → Validate → Load)")
        print("  • Realistic failure injection with healthcare-specific error types")
        print("  • Data quality degradation simulation and scoring")
        print("  • Patient and batch-level migration status tracking")
        print("  • Comprehensive analytics and actionable recommendations")
        print("  • Configurable migration parameters for different scenarios")
        print("  • Production-ready error handling and reporting")
        
        print(f"\nGenerated Files:")
        print(f"  • migration_demo_report.txt - Detailed migration report")
        
        print(f"\nThis simulation demonstrates production-ready capabilities for:")
        print(f"  • Healthcare organizations planning VistA-to-Oracle migrations")
        print(f"  • Migration testing and validation scenarios")
        print(f"  • Risk assessment and mitigation planning")
        print(f"  • Quality assurance and compliance tracking")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()