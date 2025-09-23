# Implementation Plan Overview

This document captures the current state and near-term priorities for the simulator pivot. It consolidates the active roadmap items so future sessions can resume work quickly—treat this as the source of truth for continuing implementation.

## Current Status Snapshot
- **Lifecycle engine (Phase 1)**: completed; generator uses lifecycle modules, orchestrator, and scenario configs.
- **Terminology platform (Phase 2)**: LOINC and ICD-10 importers exist; loaders prefer normalized tables while seeds remain for CI. SNOMED CT and RxNorm still rely on seed data until their importers are authored.
- **Exports**: FHIR/HL7/VistA/CSV/Parquet remain in sync; FHIR adds NCBI extensions when terminology metadata is available.

## Immediate Next Steps
1. **Build remaining importers**
   - Create `tools/import_snomed.py` and `tools/import_rxnorm.py` to normalize the official drops now staged under `data/terminology/<system>/raw/`.
   - Extend loaders/tests to prefer the normalized outputs, mirroring the LOINC/ICD-10 pattern.
2. **Design terminology DuckDB warehouse**
   - Define schema for ICD-10, LOINC, SNOMED, RxNorm, and future VSAC value sets.
   - Draft ingestion jobs (likely in `tools/`) that load the normalized CSVs into `data/terminology/terminology.duckdb`.
   - Update loaders to optionally query DuckDB when present, falling back to CSV seeds otherwise.
3. **Prepare for Phase 3 clinical realism**
   - Once the vocabularies are in DuckDB, outline the clinical rules that ensure realistic condition/med/lab combinations (e.g., contraindications, age-appropriate labs).

## Reminders
- The working checklist lives in `docs/simulator_pivot_next_steps.md`—update it whenever milestones land.
- Raw vendor archives belong in `data/terminology/<system>/raw/`; normalized CSVs stay in the root of each system directory and should be ignored once exported to DuckDB.
- Run test suites with `pytest` before wrapping up to keep the signal clean.

When returning to the project, review this file and the checkpoint document above to decide which task to pick up next.
