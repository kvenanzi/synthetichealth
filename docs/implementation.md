# Implementation Plan Overview

This document captures the current state and near-term priorities for the simulator pivot. It consolidates the active roadmap items so future sessions can resume work quickly—treat this as the source of truth for continuing implementation.

## Current Status Snapshot
- **Lifecycle engine (Phase 1)**: completed; generator uses lifecycle modules, orchestrator, and scenario configs.
- **Terminology platform (Phase 2)**: LOINC, ICD-10, SNOMED, RxNorm, VSAC, and UMLS importers are automated; loaders prefer normalized CSVs or the DuckDB warehouse while lightweight seeds remain for CI.
- **Exports**: FHIR/HL7/VistA/CSV/Parquet remain in sync; FHIR now emits Observation resources with VSAC value set references and appends UMLS concept extensions (alongside NCBI links) when terminology metadata is available.

## Phase Roadmap

### Phase 0 – Migration Branch Finalization
- ✅ Run `python tools/prepare_migration_branch.py migration_snapshot` to stage migration modules.
- ✅ Create and push the long-lived `migration` branch containing the staged files and legacy docs.
- ✅ Remove migration flags/messages from `main` after downstream transition.

### Phase 1 – Lifecycle Engine Enhancements
- ✅ Refactor remaining generator helpers (`generate_*`) into lifecycle-focused components under `src/core/lifecycle/`.
- ✅ Expand unit coverage for lifecycle pipelines as helper functions migrate out of the legacy generator.
- ✅ Introduce scenario configuration loaders, CLI selection, and lifecycle orchestrator wiring.
- ✅ Add smoke/unit tests for scenario loading and lifecycle orchestration to guard regressions.

### Phase 2 – Terminology Platform
- ✅ Replace bespoke catalogs with normalized datasets under `data/terminology/`.
- ✅ Implement terminology loaders with filtering/caching support and connect them to scenario templates.
- ✅ Normalize official ICD-10, SNOMED CT, and RxNorm releases once source archives are available (importers now covered by unit tests for canonical samples).
- ✅ Populate terminology datasets with comprehensive NLM/NCBI extracts (automated via `tools/refresh_terminology.py`).
- ✅ Enrich terminology integration (e.g., map RxNorm CUIs to clinical scenarios, extend exporters) now that normalized tables exist for all vocabularies.
- ✅ Design a DuckDB terminology warehouse (schema, ingestion jobs) to ingest normalized ICD-10/LOINC/SNOMED/RxNorm tables; extend coverage to VSAC/UMLS and document usage in the pipeline.
  - ✅ `tools/build_terminology_db.py` stages VSAC value sets and UMLS concepts and documents the DuckDB rebuild cadence.
  - ✅ Author import utilities for VSAC/UMLS so normalized CSVs can be generated alongside the existing ICD-10/LOINC/SNOMED/RxNorm helpers.
- ✅ Expand FHIR/CSV exporters to consume the new terminology services (Condition, Medication, and Observation resources now emit VSAC/UMLS context).

### Phase 3 – Clinical Realism & Validation
- ✅ Introduce module-driven workflow engine (`ModuleEngine`) and initial cardiometabolic intensive management module.
- 🔄 Author additional modules using the documented schema (`docs/scenario_recipes.md`, `modules/*.yaml`), expanding beyond cardiometabolic cohorts.
  - ✅ Pediatric asthma & immunization pathway (`modules/pediatric_asthma_management.yaml`).
  - ✅ Prenatal care with gestational diabetes management (`modules/prenatal_care_management.yaml`).
  - ✅ Oncology survivorship (`modules/oncology_survivorship.yaml`).
  - ✅ CKD dialysis planning (`modules/ckd_dialysis_planning.yaml`).
  - ✅ COPD home oxygen therapy (`modules/copd_home_oxygen.yaml`).
  - ✅ Mental health integrated care (`modules/mental_health_integrated_care.yaml`).
  - ✅ Geriatric polypharmacy & fall mitigation (`modules/geriatric_polypharmacy.yaml`).
  - 🔜 Remaining backlog modules (sepsis survivorship, HIV/PrEP management).
- 🔄 Rebuild validation to cover schema, terminology, and temporal consistency; ensure new tests run in CI.
  - ✅ Structural validator (`validate_module_definition`) now blocks invalid transitions.
  - ✅ CLI linter (`tools/module_linter.py`) enforces code bindings across modules.
  - 🔜 Temporal/terminology cross-checks and Monte Carlo regression tests.
- 🔄 Add performance/snapshot tests to protect export stability and generator throughput.
  - ✅ Baseline multi-module run recorded (200 patients, oncology + CKD + mental health) ~17s into `output/perf_baseline/`.

### Phase 4 – Docs, Tooling, and Release Prep
- Rewrite README and docs to focus on the simulator; link to the migration branch for legacy usage.
- Replace migration dashboards with clinical/SDOH analytics summaries and update utility scripts.
- Update CI pipelines, dependency manifests, and release notes to reflect the new architecture.

### Supporting Tasks
- Audit remaining modules for hard-coded migration references and remove or gate them.
- Capture design decisions in this implementation journal for transparency across phases.
- Plan beta milestones or internal releases once each phase reaches testing parity.

## Immediate Next Steps
1. **Extend module catalogue**
   - Implement remaining backlog scenarios (geriatrics, sepsis survivorship, HIV/PrEP) using the established authoring pattern.
   - Add scenario wiring plus regression tests mirroring `tests/test_module_engine.py` for every new module.
2. **Broaden validation coverage**
   - Build a module linter CLI (under `tools/`) that wraps `validate_module_definition` and checks terminology bindings.
   - Add Monte Carlo outcome assertions and exporter parity tests once multiple modules coexist.
3. **Baseline performance safeguards**
   - Capture generator runtime metrics with ≥3 modules enabled and persist results for regression comparison.

## Reminders
- Keep this document updated whenever milestones land; it is the authoritative checklist for the pivot.
- Raw vendor archives belong in `data/terminology/<system>/raw/`; normalized CSVs stay in the root of each system directory and should be ignored once exported to DuckDB.
- Run test suites with `pytest` before wrapping up to keep the signal clean.

When returning to the project, review this file and the checkpoint document above to decide which task to pick up next.
