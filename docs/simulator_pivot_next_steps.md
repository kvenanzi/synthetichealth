# Simulator Pivot: Remaining Work Plan

This checklist captures the outstanding tasks to complete the simulator-first refactor after the migration logic split.

## Phase 0 – Migration Branch Finalization
- ✅ Run `python tools/prepare_migration_branch.py migration_snapshot` to stage migration modules.
- ✅ Create and push the long-lived `migration` branch containing the staged files and legacy docs.
- ✅ Remove migration flags/messages from `main` after downstream transition.

## Phase 1 – Lifecycle Engine Enhancements
- ✅ Refactor remaining generator helpers (`generate_*`) into lifecycle-focused components under `src/core/lifecycle/`.
- ✅ Expand unit coverage for lifecycle pipelines as helper functions migrate out of the legacy generator.
- ✅ Introduce scenario configuration loaders, CLI selection, and lifecycle orchestrator wiring.
- ✅ Add smoke/unit tests for scenario loading and lifecycle orchestration to guard regressions.

## Phase 2 – Terminology Platform
- ✅ Replace bespoke catalogs with normalized datasets under `data/terminology/`.
- ✅ Implement terminology loaders with filtering/caching support and connect them to scenario templates.
- 🔄 Normalize official ICD-10, SNOMED CT, and RxNorm releases once source archives are available (ICD-10 importer added; SNOMED/RxNorm pending).
- 🔄 Populate terminology datasets with comprehensive NLM/NCBI extracts (pending larger import tooling).
- 🔄 Create import utilities for SNOMED CT and RxNorm mirroring `tools/import_loinc.py` and `tools/import_icd10.py`, update loaders to prefer normalized tables, and add pytest coverage for the new sources.
- 🔄 Design a DuckDB terminology warehouse (schema, ingestion jobs) to ingest normalized ICD-10/LOINC/SNOMED/RxNorm tables; update loaders to optionally read from `data/terminology/terminology.duckdb` for high-volume runs.
- Expand FHIR/CSV exporters to consume the new terminology services.

## Phase 3 – Clinical Realism & Validation
- Model workflow engines (referrals, lab cycles, care plan adherence) using probabilistic state machines.
- Rebuild validation to cover schema, terminology, and temporal consistency; ensure new tests run in CI.
- Add performance/snapshot tests to protect export stability and generator throughput.

## Phase 4 – Docs, Tooling, and Release Prep
- Rewrite README and docs to focus on the simulator; link to the migration branch for legacy usage.
- Replace migration dashboards with clinical/SDOH analytics summaries and update utility scripts.
- Update CI pipelines, dependency manifests, and release notes to reflect the new architecture.

## Supporting Tasks
- Audit remaining modules for hard-coded migration references and remove or gate them.
- Capture design decisions in the implementation journal for transparency across phases.
- Plan beta milestones or internal releases once each phase reaches testing parity.
