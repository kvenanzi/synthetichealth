# Implementation Plan Overview

This document captures the current state and near-term priorities for the simulator pivot. It consolidates the active roadmap items so future sessions can resume work quickly—treat this as the source of truth for continuing implementation.

## Current Status Snapshot
- **Lifecycle engine (Phase 1)**: completed; generator uses lifecycle modules, orchestrator, and scenario configs.
- **Terminology platform (Phase 2)**: LOINC, ICD-10, SNOMED, and RxNorm importers exist; loaders prefer normalized tables while seeds remain for CI.
- **Exports**: FHIR/HL7/VistA/CSV/Parquet remain in sync; FHIR adds NCBI extensions when terminology metadata is available.

## Immediate Next Steps
1. **Design terminology DuckDB warehouse**
   - Define schema for ICD-10, LOINC, SNOMED, RxNorm, and future VSAC value sets.
   - Draft ingestion jobs (likely in `tools/`) that load the normalized CSVs into `data/terminology/terminology.duckdb`.
   - Update loaders to optionally query DuckDB when present, falling back to CSV seeds otherwise.
2. **Prepare for Phase 3 clinical realism**
   - Once the vocabularies are in DuckDB, outline the clinical rules that ensure realistic condition/med/lab combinations (e.g., contraindications, age-appropriate labs).

## Reminders
- The working checklist lives in `docs/simulator_pivot_next_steps.md`—update it whenever milestones land.
- Raw vendor archives belong in `data/terminology/<system>/raw/`; normalized CSVs stay in the root of each system directory and should be ignored once exported to DuckDB.
- Run test suites with `pytest` before wrapping up to keep the signal clean.

When returning to the project, review this file and the checkpoint document above to decide which task to pick up next.
