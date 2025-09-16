# Migration Simulation Analysis

## Observed Outcomes
- The generated report at `output/migration_report.txt` shows an overall migration success rate of **2.08%** with every stage aside from a single extract substage reporting a 0% success rate and 211 accumulated errors across four batches.
- Failure type tallies are distributed almost evenly (e.g., `security_violation` appears most often) even though no specific security checks are implemented in the batch workflow, pointing to simulated—not diagnosed—failure categories.

## Root Cause Findings
- The reported success rate is derived from the number of stage executions with zero patient failures divided by the total stage executions (`overall_success_rate` in `BatchMigrationStatus.calculate_metrics`). Any substage where even one patient fails is marked as a partial failure, so the batch only earns credit when **every** patient in the batch clears the substage (`src/core/synthetic_patient_generator.py:266`).
- During stage execution a single patient failure sets the substage status to `partial_failure`, increments the failure count, and permanently marks that patient as failed for the remainder of the batch (`src/core/synthetic_patient_generator.py:399`-`src/core/synthetic_patient_generator.py:433`). With 50 patients in a batch, and per-patient success probabilities between 0.88 and 0.99, the chance of a “perfect” substage run is vanishingly small (e.g., `0.95^50 ≈ 0.08%`). This design makes <3% overall success entirely expected even when most patients succeed individually.
- Additional failure injection (random network/system penalties) further reduces the per-patient success rate in `_process_patient_stage`, compounding the problem without any retry logic. Once a patient fails, the status remains `failed` and no remediation is attempted (`src/core/synthetic_patient_generator.py:451`-`src/core/synthetic_patient_generator.py:482`).
- Error typing does not originate from the simulated failure condition; whenever any patient fails a substage, the code simply picks a random entry from `FAILURE_TYPES` to assign to the stage result (`src/core/synthetic_patient_generator.py:435`-`src/core/synthetic_patient_generator.py:437`). The prevalence of `security_violation` in the report therefore reflects random labeling rather than a systemic security issue.
- Configuration hooks for resilience (`retry_attempts`, `retry_delay_seconds`) are defined but never used, so the simulator lacks the “additional error handling” the report recommends (`src/core/synthetic_patient_generator.py:312`-`src/core/synthetic_patient_generator.py:315`).

## Recommendations
- Redefine batch success calculations to operate on patient-level outcomes, e.g., `successful_patients / total_patients`, and report stage success rates using `records_successful / records_processed` so partial progress is reflected.
- Introduce retry and remediation handling around `_process_patient_stage` that leverages `retry_attempts` and records the actual failure type that triggered the retry/final failure.
- Track and expose the real failure cause instead of randomly assigning `FAILURE_TYPES`; this will make the failure analysis actionable (e.g., base the type on which probability adjustment fired or which validation check failed).
- If lower failure rates are desired for the simulation, consider reducing the injected penalties (`network_failure_rate`, `system_overload_rate`) or lowering batch sizes; however, adjusting the success metric should be prioritized so that the report reflects meaningful success percentages.
- Evaluate switching the CLI to the newer `EnhancedMigrationSimulator`, which already maintains per-patient quality tracking and analytics, once the above reliability fixes are incorporated.

## Suggested Next Steps
1. Update `BatchMigrationStatus.calculate_metrics` and `_analyze_stage_performance` to compute ratios from patient successes instead of all-or-nothing stage completions.
2. Implement structured retry logic in `_process_patient_stage` so momentary simulated outages can recover without dooming the entire batch.
3. Replace the random failure labeling with deterministic mappings and re-run the simulation to confirm the success rate and failure taxonomy are now representative.
