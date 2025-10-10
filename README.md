# Synthetic Healthcare Data Generator

A lifecycle-focused synthetic healthcare simulator that produces richly coded patient records for interoperability prototyping, analytics experimentation, and scenario-driven research. Phase 2 centers on high-fidelity patient generation by pairing curated lifecycle logic with normalized clinical terminology datasets from the U.S. National Library of Medicine (NLM) and NCBI. The generator ships with lightweight seeds for local development, optional loaders for official releases, and a DuckDB terminology warehouse for high-volume runs.

## Features

- **Scenario-driven lifecycle engine** – demographic distributions, SDOH configuration, and orchestrated care pathways live under `src/core/lifecycle/`, enabling nuanced longitudinal cohorts.
- **Authoritative terminology datasets** – normalized ICD-10-CM, LOINC, SNOMED CT, RxNorm, VSAC value sets, and UMLS concept snapshots power terminology-aware generation and exports.
- **DuckDB-backed lookups** – build a shared `terminology.duckdb` warehouse for fast joins and larger vocabularies while keeping CSV seeds for lightweight usage.
- **Multi-format exports** – FHIR R4 bundles (now with VSAC value set and UMLS concept extensions alongside NCBI references), HL7 v2 ADT/ORU messages, VistA MUMPS globals, CSV, and Parquet outputs are emitted from the same patient records.
- **Module-driven clinical workflows** – Scenario-specific YAML modules (e.g., `cardiometabolic_intensive`) model encounters, labs, and medications using a state-machine interpreter for high-fidelity cohorts.
- **Parallel performance** – generation uses `concurrent.futures` and Polars pipelines to scale to tens of thousands of synthetic patients.
- **Referential integrity** – patient identifiers stay consistent across every export format.
- **Optional migration toolchain** – legacy migration simulators, analytics, and demos remain available for teams rehearsing data conversions but are no longer the primary focus of the project.

## Quick Start

### Installation

```bash
git clone https://github.com/ospfer/synthetichealth.git
cd synthetichealth
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r data/requirements.txt  # core generator dependencies (Polars, Faker, terminology loaders)
pip3 install -r requirements.txt       # optional analytics, migration, and integration extras
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

Set `TERMINOLOGY_DB_PATH` (or rely on the default `data/terminology/terminology.duckdb`) so loaders can read directly from DuckDB during high-volume generation. The loaders also respect `TERMINOLOGY_ROOT` for pointing at external filesystems that host larger vocabularies.

### Basic usage

```bash
# Generate synthetic healthcare data (CSV + Parquet by default)
python3 -m src.core.synthetic_patient_generator --num-records 1000 --output-dir output

# List available lifecycle scenarios
python3 -m src.core.synthetic_patient_generator --list-scenarios

# Use a specific scenario with the DuckDB-backed terminology warehouse
TERMINOLOGY_DB_PATH=data/terminology/terminology.duckdb \
python3 -m src.core.synthetic_patient_generator --num-records 500 --scenario chronic_conditions --output-dir output

# Produce only CSV or Parquet outputs
python3 -m src.core.synthetic_patient_generator --num-records 250 --output-dir output --csv
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
   echo "TERMINOLOGY_DB_PATH=$(pwd)/data/terminology/terminology.duckdb" >> .env
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

## Project structure

```
synthetichealth/
├── src/
│   ├── core/
│   │   ├── lifecycle/                 # Lifecycle engine, scenarios, orchestrator
│   │   ├── terminology/               # Terminology loaders, DuckDB adapters, environment helpers
│   │   ├── synthetic_patient_generator.py  # Main lifecycle-aware generator CLI
│   │   ├── analytics/                 # Generation analytics utilities
│   │   └── migration_simulator.py     # Optional migration rehearsal utilities
│   ├── generators/                    # Specialized data generators
│   ├── validation/                    # Data validation modules
│   └── integration/                   # System integration components
├── tools/                             # Import scripts, DuckDB builder, utilities
├── data/
│   └── terminology/                  # ICD-10, LOINC, SNOMED, RxNorm seeds + DuckDB output
├── demos/                             # Demonstration scripts (generation, performance, optional migration)
├── tests/                             # Pytest suites for lifecycle, terminology, analytics, migration
├── config/                            # Configuration files (baseline + scenario overrides)
└── docs/                              # Additional documentation
```

## Generated data formats

### Healthcare interoperability standards
- **FHIR R4**: US Core compliant Patient, Condition, and Observation resources with NCBI, VSAC, and UMLS extensions when terminology metadata is available
- **HL7 v2.x**: ADT (Admit/Discharge/Transfer) and ORU (Observation Result) messages
- **VistA MUMPS**: Production-accurate VA FileMan global structures

#### VistA export modes
- Default (`--vista-mode fileman_internal`) emits FileMan-internal pointers:
  - ICD diagnoses under `^ICD9(IEN,0)="<ICD-10-CM code>"` (File 80 root is `^ICD9` in stock builds)
  - Clinic Stops `^DIC(40.7,code,0)="code^<description>"`
  - Locations `^AUTTLOC(IEN,0)="<name>"`
  - Patient state pointers in `^DPT(DFN,.11)` piece 3 point to `^DIC(5)` IENs
  - Phones are quoted strings in `^DPT(DFN,.13)`
  - Medications populate `^AUPNVMED` with numeric drug/visit pointers and create matching `^PSDRUG` stubs
  - Labs populate `^AUPNVLAB` with numeric test pointers and emit `^LAB(60)` definitions with LOINC mappings
  - Allergies populate `^GMR(120.8)` with internal allergen pointers and create `^GMR(120.82)` dictionary entries
  - Visit GUIDs stored safely as `^AUPNVSIT("GUID",VisitIEN)="<uuid>"`
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
- Patient state in `^DPT(DFN,.11)` is a pointer to `^DIC(5)`; phones in `.13` are quoted strings.
- V Medication (`^AUPNVMED`), V Laboratory (`^AUPNVLAB`), and Patient Allergies (`^GMR(120.8)`) entries are emitted with FileMan dates/times and only internal IEN pointers—use the accompanying `^PSDRUG`, `^LAB(60)`, and `^GMR(120.82)` stubs when resolving display text.

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
- `deaths`: Mortality data with cause mapping
- `family_history`: Genetic predisposition modeling

## Terminology loaders & helpers

- Seed vocabularies live under `data/terminology/` with direct NCBI/MeSH/PubChem references for each ICD-10, LOINC, SNOMED CT, and RxNorm concept.
- Loader utilities in `src/core/terminology/` expose filtering/search helpers and respect the `TERMINOLOGY_ROOT` environment variable for pointing at larger institutional vocabularies.
- `load_scenario_config` resolves curated code lists into fully hydrated terminology bundles for the generator and exporters.
- DuckDB-backed lookups activate automatically when `TERMINOLOGY_DB_PATH` is supplied.

## Optional migration tooling

Legacy migration simulation capabilities remain for organizations rehearsing Extract-Transform-Validate-Load (ETVL) pipelines. Demos under `demos/migration_*.py`, analytics helpers in `src/core/analytics/`, and configuration profiles in `config/phase5_enhanced_config.yaml` illustrate how to adapt the synthetic records for migration rehearsals without changing the core generation workflow.

## Development

### Running tests

```bash
# Lifecycle and terminology coverage
pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_terminology_loaders.py

# Optional migration simulations and analytics
pytest tests/test_migration_simulator.py tests/test_enhanced_migration.py

# Full suite
pytest
```

### Demo scripts

```bash
# Generation and performance benchmarking
python3 demos/final_performance_demo.py
python3 demos/integration_performance_demo.py

# Optional migration demonstrations
python3 demos/migration_demo.py
python3 demos/enhanced_migration_demo.py
python3 demos/migration_analytics_demo.py
```
