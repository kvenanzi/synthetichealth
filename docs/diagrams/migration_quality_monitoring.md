# Migration Quality Monitoring

Depicts how the baseline `MigrationSimulator` flow in `src/core/synthetic_patient_generator.py` connects with the enhanced tracking components in `src/core/enhanced_migration_simulator.py` and `src/core/enhanced_migration_tracker.py`.

```mermaid
flowchart TB
    subgraph BaseMigration
        batch[Batch of PatientRecord] --> sim[MigrationSimulator.simulate_staged_migration]
        sim --> stage[_execute_migration_stage<br/>iterate ETL_SUBSTAGES]
        stage --> patientStage[_process_patient_stage<br/>retry + failure logging]
        stage --> result[MigrationStageResult appended<br/>to BatchMigrationStatus]
        sim --> quality[_calculate_quality_metrics<br/>sdoh + care summaries]
        quality --> batchStatus[BatchMigrationStatus<br/>analytics & patient_failures]
    end
    batchStatus --> report1[export_migration_report<br/>+ migration_quality_report.json]
    report1 --> dashboard[tools/generate_dashboard_summary<br/>synthesize SDOH + care data]
    subgraph EnhancedTracking
        batch --> enhanced[EnhancedMigrationSimulator.simulate_patient_migration]
        enhanced --> subst[_execute_migration_stage + _execute_substage<br/>log HIPAA access]
        subst --> degrade[ClinicalDataDegradationSimulator<br/>simulate_degradation]
        subst --> scorer[HealthcareDataQualityScorer<br/>calculate_patient_quality_score]
        subst --> hipaa[HIPAAComplianceTracker<br/>record_violation]
        enhanced --> final[_perform_final_quality_assessment<br/>PatientMigrationStatus]
        final --> alerts[MigrationQualityMonitor.monitor_patient_quality<br/>QualityAlert emission]
        alerts --> metrics[EnhancedMigrationMetrics<br/>real-time dashboard payload]
    end
```
