# Implementation Plan for Refocusing Synthetic Data Simulator

## Current Focus & Gaps
* The public-facing documentation, demos, and tests emphasize migration tooling (VistA → Oracle Health) instead of a pure synthetic data simulator, including the README, configuration defaults, demos, docs, and analytics/tests.

* Core modules such as `synthetic_patient_generator` and `multi_format_healthcare_generator` embed migration simulators, success-rate tuning, and migration metrics rather than focusing solely on patient lifecycle generation and standards-compliant exports.

* Terminology catalogs for conditions, medications, and related concepts are manually curated and relatively small, conflicting with the goal of large, comprehensive code sets across ICD-10, SNOMED, LOINC, RxNorm, etc.

* Supporting tooling (e.g., dashboard summary scripts) also centers on migration quality reports, reinforcing the current migration-first posture.

## Implementation Plan

1. **Branch Strategy & Repository Realignment**
   * Create a long-lived `migration` branch to preserve current migration engines, demos, analytics, and documentation for reference or future use. Move migration-specific packages (`src/core/enhanced_migration_simulator.py`, `src/analytics`, migration demos/tests/docs, tooling) into that branch and delete them from `main` once the branch exists.
   * Update CI/configuration on `main` to drop migration tests and replace them with generation-focused checks after the branch split.

2. **Core Domain Redesign (Patient Lifecycle-Centric)**
   * Refactor `src/core/synthetic_patient_generator.py` into a modular clinical lifecycle engine with distinct submodules for intake, longitudinal encounters, diagnostics, therapies, and follow-up, decoupled from migration metadata.
   * Introduce new domain models (e.g., `Patient`, `Encounter`, `ClinicalEvent`, `CarePlan`) using dataclasses or Pydantic models aligned with FHIR resource structures, capturing intake → history → assessments → interventions → outcomes.
   * Implement scenario templates (primary care, oncology, chronic disease management, behavioral health, pediatric, maternity, etc.) to orchestrate condition progression, comorbidities, and interventions over time.

3. **Terminology & Reference Data Expansion**
   * Replace the hand-written catalogs with large curated datasets for conditions, meds, labs, immunizations, allergies, and procedures. Use authoritative sources (ICD-10-CM, SNOMED CT reference sets, RxNorm, LOINC, CVX, CPT) stored under `data/terminology/` in normalized CSV/Parquet form, supporting thousands of entries.
   * Build loaders and sampling utilities that can filter by specialty, demographic prevalence, severity, or guideline-based cohorts.
   * Add optional integration hooks for official FHIR terminology packages or publicly distributable subsets, and expose caching so large code sets don’t need to load on every run.

4. **Standards-Aligned Generation Pipeline**
   * Architect a pipeline that produces FHIR R4, R5, and provisional R6/Draft resources while maintaining backward compatibility with DSTU2/STU3 mappings where possible, encapsulated in a new `src/standards/fhir` package.
   * Implement SNOMED, LOINC, RxNorm, ICD-10 coding helpers that map generated clinical events to appropriate codings based on scenario and event type.
   * Maintain CSV/Parquet exports via dedicated exporters that flatten FHIR bundles into analytics-friendly tables, reusing schema definitions but divorced from migration code paths.
   * Provide optional HL7 v2 message generation for completeness but treat it as a format export step rather than migration simulation.

5. **Clinical Process Modeling Enhancements**
   * Model clinical workflows (e.g., referral chains, lab ordering/result cycles, medication titration, care-plan adherence) with probabilistic state machines or rule-based engines fed by the expanded terminology sets.
   * Incorporate temporal realism: appointment scheduling, follow-up intervals, test result turnaround times, care plan adjustments, and condition progression/regression.
   * Implement SDOH influences on utilization and outcomes (e.g., missed appointments, medication adherence) using the existing demographic distributions as inputs but expanding coverage beyond current small set.

6. **Configuration & Scenario Management**
   * Replace the migration-centric configuration fields with scenario-focused YAML/JSON definitions describing patient cohorts, prevalence, chronic disease panels, and output targets.
   * Support layered configuration (global defaults, scenario overrides, CLI flags) and load validation to ensure completeness.
   * Provide CLI commands to list available scenarios, preview distributions, and run targeted generation batches.

7. **Validation & Quality Assurance**
   * Rework `src/validation` to focus on clinical and standards compliance: schema validation using `fhir.resources` or `hl7-fhir` packages, terminology validation against the new catalogs, and clinical consistency checks (e.g., lab value ranges, contraindications).
   * Introduce data quality metrics relevant to synthetic generation (coverage of code systems, event counts, demographic distribution adherence) replacing migration success metrics.
   * Develop regression fixtures to ensure reproducibility with fixed seeds.

8. **Testing Overhaul**
   * Write unit/integration tests covering the new lifecycle pipeline, exporter outputs, and terminology samplers; remove migration simulator tests from `main`.
   * Add snapshot tests for representative FHIR bundles and CSV/Parquet outputs to guard format stability.
   * Include performance tests for large-scale generation to ensure scalability without migration logic.

9. **Documentation, Demos, and Tooling**
   * Rewrite the README and docs to describe the state-of-the-art synthetic simulator focus, scenario usage, supported standards, and large terminology coverage, while referencing the `migration` branch for legacy workflows.
   * Create new demos illustrating patient journey generation, standards exports, analytics-ready datasets, and configuration-driven scenarios.
   * Retool utilities (e.g., replace `generate_dashboard_summary.py`) to summarize clinical/SDOH metrics rather than migration reports.
   * Update requirements to include any new dependencies (e.g., `fhir.resources`, `pydantic`, `networkx` for workflow graphs) and set up linting/formatting for the reorganized codebase.

10. **Deployment & Release Readiness**
    * Provide versioned release notes clarifying the migration of legacy functionality to the dedicated branch and the new simulator capabilities.
    * Set up CI workflows focused on generator validation, export schema checks, and style/linting appropriate for the new architecture.

