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
  - ✅ Sepsis survivorship recovery (`modules/sepsis_survivorship.yaml`).
  - ✅ HIV + PrEP management (`modules/hiv_prep_management.yaml`).
- 🔄 Rebuild validation to cover schema, terminology, and temporal consistency; ensure new tests run in CI.
  - ✅ Structural validator (`validate_module_definition`) now blocks invalid transitions.
  - ✅ CLI linter (`tools/module_linter.py`) enforces code bindings across modules.
  - ✅ Monte Carlo regression script (`tools/module_monte_carlo_check.py`) and composite harness (`tools/run_phase3_validation.py`) capture variance and required-code checks for representative module cohorts.
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

## Phase 3B – Synthea‑Level Realism (Plan)
See `docs/phase_3b_synthea_parity_plan.md` for the full end‑to‑end plan to extend the DSL, engine, provenance, and validation to match Synthea’s module detail (attributes, conditional transitions, submodules, symptom modeling, and evidence‑backed parameters).

## VistA Export – RXs, Labs, Allergies (Plan)
Objective: extend the VistA MUMPS exporter to include FileMan‑correct medication, laboratory, and allergy data alongside patients (^DPT), visits (^AUPNVSIT), and problems (^AUPNPROB).

Scope & Deliverables
- Medications: emit PCC V Medication file nodes `^AUPNVMED` (#9000010.14) with internal pointers and xrefs; create minimal `^PSDRUG` (#50) entries as pointer targets.
- Labs: emit PCC V Laboratory file nodes `^AUPNVLAB` (#9000010.09); create minimal test definitions under `^LAB(60)` (#60) as pointer targets.
- Allergies: emit Patient Allergies entries `^GMR(120.8)` (#120.8); create minimal allergen entries under `^GMR(120.82)` (#120.82) as pointer targets.
- Pointer registries: extend the existing registry to manage IEN lookup/creation for `^PSDRUG`, `^LAB(60)`, and `^GMR(120.82)` (with file headers).
- Cross‑refs and headers: add standard “B”/visit xrefs where applicable and file headers with last IEN/date for all new files.

Data Mapping (internal values only)
- Source → VistA pointers
  - MedicationOrder: map `rxnorm_code` to `^PSDRUG` IEN (fall back on display name when missing). Tie to visit IEN when an `encounter_id` is present.
  - Observation (labs): map LOINC code to `^LAB(60)` IEN. Carry result/value, unit, and effective date/time. Tie to visit when `encounter_id` present; otherwise choose nearest visit by date.
  - Allergies: map allergen substance (prefer RxNorm/UNII where present) to `^GMR(120.82)` IEN. Store patient‑level allergy with reaction/severity as available.

Minimal File Nodes (proposed)
- `^AUPNVMED(IEN,0)` = DFN^DRUG_IEN^VISIT_IEN^FM_DATE^... (use File #9000010.14 field order; all pointers and dates in internal format). Add:
  - `^AUPNVMED("B",DFN,IEN)=""`, `^AUPNVMED("V",VISIT_IEN,IEN)=""`
  - Header: `^AUPNVMED(0)="V MEDICATION^9000010.14^<lastIEN>^<FMdate>"`
- `^AUPNVLAB(IEN,0)` = DFN^TEST_IEN(^LAB(60))^VISIT_IEN^RESULT^UNITS^REF_RANGE^FM_DATETIME^... Add:
  - `^AUPNVLAB("B",DFN,IEN)=""`, `^AUPNVLAB("V",VISIT_IEN,IEN)=""`
  - Header: `^AUPNVLAB(0)="V LAB^9000010.09^<lastIEN>^<FMdate>"`
- `^GMR(120.8,IEN,0)` = DFN^ALLERGEN_IEN(^GMR(120.82))^... (observed/historical, verify flags optional). Add:
  - `^GMR(120.8,"B",DFN,IEN)=""`
  - Header: `^GMR(120.8,0)="PATIENT ALLERGIES^120.8^<lastIEN>^<FMdate>"`

Pointer Target Registries (new)
- Drugs (`^PSDRUG`, File #50): key on RxNorm and display; create minimal `^PSDRUG(IEN,0)=<NAME>^...` plus `^PSDRUG("B",NAME,IEN)` and header `^PSDRUG(0)="DRUG^50^..."`.
- Lab Tests (`^LAB(60)`, File #60): key on LOINC and test name; create `^LAB(60,IEN,0)=<NAME>^...`, `^LAB(60,"B",NAME,IEN)`, header `^LAB(60,0)="LAB TEST^60^..."`.
- Allergens (`^GMR(120.82)`, File #120.82): key on substance name/RxNorm/UNII; create `^GMR(120.82,IEN,0)=<NAME>^...`, `^GMR(120.82,"B",NAME,IEN)`, header `^GMR(120.82,0)="ALLERGEN^120.82^..."`.

Exporter Changes
- Extend `VistaFormatter.export_vista_globals(...)` to accept medications, observations, and allergies.
- Enhance `_export_fileman_internal` to:
  1) write medications after visits using `^AUPNVMED` and new drug registry,
  2) write labs using `^AUPNVLAB` and lab test registry,
  3) write allergies at patient scope using `^GMR(120.8)` and allergen registry,
  4) emit xrefs and file headers for each file.
- Preserve current conventions: FM dates, internal pointers only; quote free‑text; keep visit GUID xref under `^AUPNVSIT("GUID",IEN)`.

Validation & Tests
- Unit tests (extend `tests/test_vista_formatter.py`):
  - assert presence of `^AUPNVMED(0)`, `^AUPNVLAB(0)`, `^GMR(120.8,0)` headers.
  - verify `0` nodes contain only internal values (DFN/visit IENs, pointer IENs, FM dates), and strings are quoted.
  - verify xrefs: `("V" by visit)`, `("B" by DFN)` exist and match `0` nodes.
  - ensure pointer targets (`^PSDRUG`, `^LAB(60)`, `^GMR(120.82)`) are created with headers and “B” xrefs.
- Smoke test: generate a small cohort with at least one med, lab, and allergy; confirm node counts in the exporter summary and spot‑check a few lines in `vista_globals.mumps`.

Risks & Mitigations
- Site variance in DDs: use conservative, widely deployed PCC/VistA V‑file fields; keep to minimal required pieces and indexes.
- Lab complexity: we avoid deeper Lab Service globals (`^LR`) initially; stick to V LAB entries with `^LAB(60)` pointers.
- Drug master data: `^PSDRUG` is large in production; we generate minimal stubs for dereferencing/display and document this limitation.

Implementation Steps
1. Add registries for `^PSDRUG`, `^LAB(60)`, `^GMR(120.82)` mirroring the existing ICD/location/state registry patterns.
2. Wire medications, labs, and allergies into `VistaFormatter._export_fileman_internal` with node builders + xref writers.
3. Emit file headers and aggregate counts for all new files in the exporter summary.
4. Add unit tests for new files/xrefs and edge cases (missing codes → fallback display entries; missing visit linkage → patient‑only allergy; malformed phone/strings still quoted).
5. Update primers (`primers/vista_mumps_quickstart.md`) with examples for each new file and note internal vs. external values.
6. Update docs/README and main README about the expanded VistA coverage and any flags added.

Acceptance Criteria
- Export includes valid `^AUPNVMED`, `^AUPNVLAB`, and `^GMR(120.8)` entries with synchronized xrefs and headers.
- All pointer fields use internal IENs; all string fields are quoted; FM dates/times are used consistently.
- Minimal pointer target files are present (`^PSDRUG`, `^LAB(60)`, `^GMR(120.82)`) with headers and “B” indexes.
- Tests pass (`pytest`), and smoke output shows patients > 0, meds > 0, labs > 0, allergies > 0.

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
