# Synthetic Healthcare Data Generator

A lifecycle-focused synthetic healthcare simulator that produces richly coded patient records for interoperability prototyping, analytics experimentation, and scenario-driven research. The generator pairs curated lifecycle logic with normalized clinical terminology datasets (ICD-10-CM, LOINC, SNOMED CT, RxNorm; optional VSAC and UMLS) and can use a DuckDB terminology warehouse for larger runs.

## Features

- **Scenario-driven lifecycle engine** – demographic distributions, SDOH configuration, and orchestrated care pathways live under `src/core/lifecycle/`, enabling nuanced longitudinal cohorts.
- **Authoritative terminology datasets** – normalized ICD-10-CM, LOINC, SNOMED CT, RxNorm, VSAC value sets, and UMLS concept snapshots power terminology-aware generation and exports.
- **DuckDB-backed lookups** – build a shared `terminology.duckdb` warehouse for fast joins and larger vocabularies while keeping CSV seeds for lightweight usage.
- **Multi-format exports** – FHIR R4 bundles (now with VSAC value set and UMLS concept extensions alongside NCBI references), HL7 v2 ADT/ORU messages, VistA MUMPS globals, CSV, and Parquet outputs are emitted from the same patient records.
- **Module-driven clinical workflows** – Scenario-specific YAML modules (e.g., `cardiometabolic_intensive`) model encounters, labs, and medications using a state-machine interpreter for high-fidelity cohorts.
- **Parallel performance** – generation uses `concurrent.futures` and Polars pipelines to scale to tens of thousands of synthetic patients.
- **Referential integrity** – patient identifiers stay consistent across every export format.

## Documentation

- Project docs live under `docs/` – start with `docs/README.md` for an index and `docs/implementation.md` for the active roadmap.

## Quick Start

### Installation

```bash
git clone https://github.com/ospfer/synthetichealth.git
cd synthetichealth
python3 -m venv .venv
source .venv/bin/activate
pip install -r data/requirements.txt  # core generator dependencies (Polars, Faker, terminology loaders)
pip install -r requirements.txt       # additional exporters, reporting, and CLI utilities
```

### Terminology setup

Lightweight CSV seeds for each code system are committed under `data/terminology/` for quick experimentation. To ingest the official releases and consolidate them into DuckDB:

```bash
# Inspect available code systems
ls data/terminology

# Normalize official tables (examples)
python3 tools/import_loinc.py --raw data/terminology/loinc/raw/LoincTable/Loinc.csv --output data/terminology/loinc/loinc_full.csv
python3 tools/import_icd10.py --raw data/terminology/icd10/raw/icd10cm-order-2026.txt --output data/terminology/icd10/icd10_full.csv
python3 tools/import_snomed.py --concept ... --description ... --output data/terminology/snomed/snomed_full.csv
python3 tools/import_rxnorm.py --rxnconso ... --output data/terminology/rxnorm/rxnorm_full.csv

# Build the consolidated DuckDB warehouse
python3 tools/build_terminology_db.py --root data/terminology --output data/terminology/terminology.duckdb

# Or run the one-stop refresh (detects staged raw files and rebuilds DuckDB)
python3 tools/refresh_terminology.py --root data/terminology --rebuild-db --force
```

Set `TERMINOLOGY_DB_PATH` (or rely on the default `data/terminology/terminology.duckdb`) so loaders can read directly from DuckDB during high-volume generation. Loaders also respect `TERMINOLOGY_ROOT` to point at an external filesystem that hosts larger vocabularies.

### Basic usage

```bash
# Generate synthetic healthcare data (CSV + Parquet by default)
python -m src.core.synthetic_patient_generator --num-records 1000 --output-dir output

# List available lifecycle scenarios and modules
python -m src.core.synthetic_patient_generator --list-scenarios
python -m src.core.synthetic_patient_generator --list-modules

# Use a specific scenario with the DuckDB-backed terminology warehouse
TERMINOLOGY_DB_PATH=data/terminology/terminology.duckdb \
python -m src.core.synthetic_patient_generator --num-records 500 --scenario chronic_conditions --output-dir output

# Run with one or more clinical workflow modules
python -m src.core.synthetic_patient_generator --num-records 200 --module copd_v2 --module hypertension_management --output-dir output

# Control output formats or skip exporters
python -m src.core.synthetic_patient_generator --num-records 250 --output-dir output --csv
python -m src.core.synthetic_patient_generator --num-records 250 --output-dir output --parquet
python -m src.core.synthetic_patient_generator --num-records 250 --output-dir output --skip-fhir --skip-hl7 --skip-vista

# Use a config file and scenario overrides
python -m src.core.synthetic_patient_generator --config config/config.yaml --scenario-file custom_scenario.yaml --output-dir output
```

## Developer onboarding checklist

1. **Create the virtual environment and install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Stage terminology data**
   - Keep lightweight seeds under `data/terminology/<system>/*.csv` for local testing.
   - Drop official archives into the matching `raw/` folders and run the import utilities in `tools/` to generate `*_full.csv` extracts (ICD-10, LOINC, SNOMED, RxNorm, plus optional VSAC and UMLS snapshots).
3. **Materialize the DuckDB warehouse**
   ```bash
   python3 tools/build_terminology_db.py \
     --root data/terminology \
     --output data/terminology/terminology.duckdb \
     --force
   ```
   Re-run this command whenever new releases are imported so the consolidated warehouse stays current.
4. **Configure environment variables**
   ```bash
   export TERMINOLOGY_DB_PATH="$(pwd)/data/terminology/terminology.duckdb"
   # Optional: persist for future shells
   echo "export TERMINOLOGY_DB_PATH=$(pwd)/data/terminology/terminology.duckdb" >> ~/.bashrc  # or your shell profile
   ```
   Loaders automatically fall back to CSV seeds when the DuckDB path is not available, but setting `TERMINOLOGY_DB_PATH` unlocks faster joins for high-volume simulation runs.
5. **Author scenario modules (optional)**
   - Compose YAML workflows under `modules/` (see `modules/cardiometabolic_intensive.yaml`).
   - Reference the module in a scenario via `modules: ["module_name"]` and run `pytest tests/test_module_engine.py` to validate execution.
6. **Run the focused realism regression suites**
   ```bash
   source .venv/bin/activate
   pytest tests/test_clinical_generation.py tests/test_med_lab_realism.py tests/test_module_engine.py
   ```
7. **Execute the phase 3 validation harness before pushing significant changes**
   ```bash
   source .venv/bin/activate
   python tools/run_phase3_validation.py
   ```
8. **Capture/refresh baseline performance metrics when investigating regressions**
   ```bash
   source .venv/bin/activate
   python tools/capture_performance_baseline.py --track-history
   ```

## Clinical terminology datasets

Phase 2 introduces normalized clinical code sets sourced from NLM / NCBI resources. Each directory contains lightweight seeds for development and `raw/` folders for staging official releases:

| Code System | Source | Local Layout |
|-------------|--------|--------------|
| **ICD-10-CM** | https://www.cdc.gov/nchs/icd/icd10cm.htm | `icd10/icd10_conditions.csv` (seed) / `icd10/raw/` (official text exports) |
| **LOINC** | https://loinc.org/downloads/loinc | `loinc/loinc_labs.csv` (seed) / `loinc/raw/` (official CSV extract) |
| **SNOMED CT** | https://www.nlm.nih.gov/healthit/snomedct/us_edition.html | `snomed/snomed_conditions.csv` (seed) / `snomed/raw/` (snapshot directories) |
| **RxNorm** | https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html | `rxnorm/rxnorm_medications.csv` (seed) / `rxnorm/raw/` (RRF release) |
| **VSAC (optional)** | https://vsac.nlm.nih.gov/ | `vsac/vsac_value_sets.csv` (optional seed) / `vsac/raw/` (value set exports staged locally) |
| **UMLS 2025AA (optional)** | https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html | `umls/umls_concepts.csv` (optional seed) / `umls/raw/` (full UMLS release for advanced mappings) |

Normalization scripts in `tools/` generate `_full.csv` tables aligned with the loader schemas. When both the seed and normalized tables exist, the loaders automatically prioritize the richer dataset. Keep licensed content outside of version control and configure environment variables to point the generator at your secure storage.

## DuckDB terminology warehouse

The `tools/build_terminology_db.py` script materializes the normalized CSVs into a single `terminology.duckdb` database (including optional VSAC value sets and UMLS concept tables when their extracts are present). Rebuild the file with `--force` whenever fresh terminology drops are imported so analytics, exporters, and runtime loaders stay aligned.

```bash
python3 tools/build_terminology_db.py \
  --root data/terminology \
  --output data/terminology/terminology.duckdb \
  --force
```

Set `TERMINOLOGY_DB_PATH` (or rely on the default `data/terminology/terminology.duckdb`) so loaders and exports can read directly from DuckDB during high-volume generation. When the environment variable is absent or the file is missing the system gracefully falls back to the committed CSV seeds.

## Configuration (YAML)

The generator accepts a config file via `--config <path>` that complements CLI flags. Keys below mirror internal options; CLI flags take precedence.

- `num_records`: integer, number of patients to generate (default 1000)
- `output_dir`: string, directory for emitted files (default `.`)
- `seed`: integer, RNG seed for reproducibility
- `output_format`: one of `csv`, `parquet`, or `both` (default `both`)
- `scenario`: string, lifecycle scenario name (see `--list-scenarios`)
- `scenario_file`: string path to a YAML that provides scenario overrides
- `modules`: string or list of module names to activate (see `--list-modules`)
- `vista_mode`: `fileman_internal` or `legacy` (affects VistA export encoding)
- Distributions (accept dictionary of label→weight; weights auto-normalize):
  - `age_dist`, `gender_dist`, `race_dist`
  - `smoking_dist`, `alcohol_dist`, `education_dist`, `employment_dist`, `housing_dist`

Example:
```yaml
num_records: 500
output_dir: output/run1
scenario: chronic_conditions
modules: [copd_v2, hypertension_management]
output_format: parquet
vista_mode: fileman_internal
age_dist: { "0-17": 0.1, "18-34": 0.2, "35-49": 0.25, "50-64": 0.25, "65-79": 0.15, "80+": 0.05 }
```

## Project structure

```
synthetichealth/
├── src/
│   └── core/
│       ├── lifecycle/                 # Lifecycle engine, scenarios, orchestrator
│       ├── terminology/               # Terminology loaders, DuckDB adapters, environment helpers
│       └── synthetic_patient_generator.py  # Main lifecycle-aware generator CLI
├── tools/                             # Import scripts, DuckDB builder, utilities
├── data/
│   └── terminology/                   # ICD-10, LOINC, SNOMED, RxNorm seeds + DuckDB output
├── modules/                           # Optional YAML-driven clinical workflow modules
├── tests/                             # Pytest suites for lifecycle, terminology, and exporters
├── config/                            # Configuration files (baseline + scenario overrides)
└── docs/                              # Additional documentation
```

## Diagram rendering

- Install Mermaid CLI once per environment: `npm install -g @mermaid-js/mermaid-cli`.
- Render all repository diagrams (both `.mmd` files and Markdown embeds) with `tools/render_mermaid.sh`. Pass explicit paths to rerender a subset, e.g. `tools/render_mermaid.sh docs/diagrams/synthetic_data_pipeline.md`.
- The helper script writes SVGs alongside the sources and ensures `docs/diagrams/puppeteer-config.json` exists so Puppeteer can launch headless Chromium without sandboxing.
- Markdown sources that include multiple Mermaid fences emit `*-2.svg`, `*-3.svg`, etc. alongside the base file; commit the generated SVGs with the documentation changes.
- Re-run the script whenever a diagram changes to keep exported SVGs synchronized with the Markdown or `.mmd` source before opening a PR.

## Generated data formats

### Healthcare interoperability standards
- **FHIR R4**: US Core compliant Patient, Condition, and Observation resources with NCBI, VSAC, and UMLS extensions when terminology metadata is available
- **HL7 v2.x**: ADT (Admit/Discharge/Transfer) and ORU (Observation Result) messages
- **VistA MUMPS**: Production-accurate VA FileMan global structures

#### VistA export modes
- Default (`--vista-mode fileman_internal`) emits FileMan-internal pointers and supporting dictionary stubs for medications, labs, allergies, CPT-coded procedures, vital measurements, health factors, immunizations, family history, and care-plan TIU notes.
- Legacy (`--vista-mode legacy`) preserves earlier text-oriented encoding (not pointer-clean). Use only to reproduce historical artifacts.

Example:
```bash
python -m src.core.synthetic_patient_generator \
  --num-records 100 \
  --output-dir output/run1 \
  --vista-mode fileman_internal
```

#### VistA Quick Tips
- Primer with parsing and date helpers: `primers/vista_mumps_quickstart.md`
- FileMan dates use YYYMMDD with YYY = year−1700; visits use `YYYMMDD.HHMMSS`.
- Globals are written as `S ^GLOBAL(...)=<value>`; strip the leading `S` and surrounding quotes when parsing.
- Care-plan notes export under the TIU title “Care Plan.” Vital measurements default to BP, pulse, respiration, temperature, SpO₂, height, weight, and BMI per patient.

### Analytics formats
- **CSV/Parquet**: Normalized relational tables for research and analytics workflows

### Core tables
All formats maintain referential integrity via `patient_id` linkage:
- `patients`: Demographics, SDOH factors, multiple identifiers
- `encounters`: Healthcare visits with realistic patterns
- `conditions`: ICD-10/SNOMED coded diagnoses with clinical status
- `medications`: RxNorm/NDC coded prescriptions linked to indications
- `allergies`: SNOMED coded substance allergies
- `procedures`: CPT coded medical procedures
- `immunizations`: CVX coded vaccination records
- `observations`: LOINC coded vitals and lab results
- `care_plans`: Guideline milestones, status, and activities (also emitted to TIU in VistA mode)
- `deaths`: Mortality data with cause mapping
- `family_history`: Genetic predisposition modeling

## Terminology loaders & helpers

- Seed vocabularies live under `data/terminology/`. Optional VSAC and UMLS normalizations enrich value set membership and crosswalks.
- Loader utilities in `src/core/terminology/` expose filtering/search helpers and respect `TERMINOLOGY_ROOT` and `TERMINOLOGY_DB_PATH`.
- `load_scenario_config` resolves curated code lists into terminology bundles for the generator and exporters.

## Development

### Running tests

```bash
# Lifecycle and terminology coverage
pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_terminology_loaders.py

# Module engine and validation helpers
pytest tests/test_module_engine.py tests/test_module_kpi_validator.py tests/test_module_linter.py

# Full suite
pytest
```
