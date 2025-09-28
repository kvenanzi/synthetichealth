# Technical User Guide – Synthetic Patient Simulator

## 1. Overview
The synthetic patient simulator produces clinically coherent records for analytics, interoperability testing, and migration rehearsals. It combines curated lifecycle logic with normalized terminology services so that every Patient, Condition, Medication, and Observation can be exported in FHIR R4, HL7 v2, CSV/Parquet, and VistA-friendly formats.

## 2. Environment & Prerequisites
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
All commands below assume the virtual environment is active. Raw vocabularies should be staged under `data/terminology/<system>/raw/`.

## 3. Terminology Pipeline (Mermaid: `docs/diagrams/terminology_pipeline.md`)
1. **Raw Archives** – Drop official ICD-10 order files, SNOMED snapshot TSVs, RXNCONSO.RRF, VSAC XLSX exports, and UMLS `.nlm` bundles into the corresponding `raw/` directories.
2. **Normalization Scripts** – Run individually (`python tools/import_snomed.py …`) or in bulk with `python tools/refresh_terminology.py --root data/terminology --rebuild-db --force`. Each script writes a `_full.csv` aligned with the loader schema.
3. **DuckDB Warehouse** – `tools/build_terminology_db.py` (invoked automatically by the refresh helper when `--rebuild-db` is used) consolidates all normalized tables into `data/terminology/terminology.duckdb`.
4. **Runtime Loading** – `src/core/terminology/loaders.py` prefers DuckDB, falling back to `_full.csv` or the committed seeds. `build_terminology_lookup` converts scenario-selected concepts into fast lookups for exporters.

## 4. Generation Flow (Mermaid: `docs/diagrams/synthetic_patient_generator_flow.md`)
1. **Scenario Selection** – CLI flags and optional YAML overrides pick a baseline cohort (`--scenario cardiometabolic`).
2. **load_scenario_config** – Merges overrides, resolves terminology details, and attaches filtered ICD-10/LOINC/RxNorm/VSAC/UMLS entries.
3. **LifecycleOrchestrator** – Seeds demographics, SDOH factors, and visit cadence; delegates to `generate_patient_profile_for_index` for parallel execution.
4. **Lifecycle Modules** – `generate_conditions`, `generate_encounters`, `generate_medications`, and `generate_observations` populate clinical events while embedding normalized codes.
5. **Export Stage** – `FHIRFormatter`/`HL7v2Formatter` build rich resources (MedicationStatements now include RxNorm + UMLS extensions; Observations embed VSAC references) while CSV/Parquet writers create analytic tables.

## 5. Running the Simulator
```bash
# Refresh terminology (optional but recommended when raw sources change)
python tools/refresh_terminology.py --root data/terminology --rebuild-db

# Generate 500 patients with the cardiometabolic scenario
python -m src.core.synthetic_patient_generator --num-records 500 \
    --scenario cardiometabolic --output-dir output/demo

# CSV-only run for quick analytics
python -m src.core.synthetic_patient_generator --num-records 100 --csv --output-dir output/csv_only
```
Set `TERMINOLOGY_DB_PATH=$(pwd)/data/terminology/terminology.duckdb` for high-volume runs; the generator will fall back to seeds when the database is absent.

## 6. Outputs & File Layout
- `output/<run>/patients.csv` (plus encounters, conditions, medications, observations, etc.) – normalized tables keyed by `patient_id`.
- `output/<run>/fhir_bundle.json` – Bundle containing Patient, Condition, MedicationStatement, Observation resources with VSAC/NCBI/UMLS extensions.
- `output/<run>/hl7_messages/*.hl7` – ADT and ORU messages referencing LOINC and RxNorm codes.
- `output/<run>/vista_globals.txt` – Optional VistA MUMPS globals for migration rehearsals.

## 7. Validation & Troubleshooting
- `pytest tests/tools` ensures all terminology importers still parse staged samples.
- `pytest tests/test_fhir_formatter.py tests/test_terminology_loaders.py` validates exporter metadata wiring.
- If terminology lookups return empty results, re-run `refresh_terminology.py` and confirm `TERMINOLOGY_DB_PATH` points to the regenerated DuckDB file.
- Use `--dry-run` (to be implemented) or small `--num-records` values when iterating on scenario logic to shorten feedback loops.
