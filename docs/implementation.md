# Implementation Plan Overview

This document captures the current state and near-term priorities for the simulator pivot. It consolidates the active roadmap items so future sessions can resume work quickly—treat this as the source of truth for continuing implementation.

## Current Status Snapshot
- **Lifecycle engine (Phase 1)**: completed; generator uses lifecycle modules, orchestrator, and scenario configs.
- **Terminology platform (Phase 2)**: LOINC, ICD-10, SNOMED, and RxNorm importers exist; loaders prefer normalized CSVs (or the optional DuckDB warehouse) while seeds remain for CI.
- **Exports**: FHIR/HL7/VistA/CSV/Parquet remain in sync; FHIR now emits Observation resources with VSAC value set references and appends UMLS concept extensions (alongside NCBI links) when terminology metadata is available.

## Immediate Next Steps
1. **Extend terminology DuckDB workflows**
   - ✅ VSAC/UMLS staging added to `tools/build_terminology_db.py` alongside a `--force` rebuild guard.
   - ✅ DuckDB onboarding guidance (`TERMINOLOGY_DB_PATH`, regeneration cadence) folded into the main README and terminology docs.
   - ✅ Lifecycle scenarios surface VSAC/UMLS assets and exporters consume them for FHIR + CSV outputs.
   - 🔄 Automate normalization for VSAC/UMLS drops (dedicated import scripts or documented ETL steps) so staging isn't manual.
2. **Prepare for Phase 3 clinical realism**
   - Once the vocabularies are in DuckDB, outline the clinical rules that ensure realistic condition/med/lab combinations (e.g., contraindications, age-appropriate labs).

## Reminders
- The working checklist lives in `docs/simulator_pivot_next_steps.md`—update it whenever milestones land.
- Raw vendor archives belong in `data/terminology/<system>/raw/`; normalized CSVs stay in the root of each system directory and should be ignored once exported to DuckDB.
- Run test suites with `pytest` before wrapping up to keep the signal clean.

When returning to the project, review this file and the checkpoint document above to decide which task to pick up next.
