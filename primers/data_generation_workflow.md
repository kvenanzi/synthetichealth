# Data Generation Workflow Primer

## Goals
- Prepare the environment and terminology assets
- Choose scenarios and clinical modules
- Run the generator with confidence (CSV, Parquet, FHIR, HL7, VistA)
- Validate outputs and capture baselines

## 1. Environment Checklist
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional: refresh vocabularies
python tools/refresh_terminology.py --root data/terminology --rebuild-db
```
- Always run CLI commands inside `.venv` (repository default).
- Terminology lookups prefer `data/terminology/terminology.duckdb`; the generator falls back to seed CSVs when absent.

## 2. Discover Scenarios & Modules
```bash
python -m src.core.synthetic_patient_generator --list-scenarios
python -m src.core.synthetic_patient_generator --list-modules
```
- Scenarios capture demographics + SDOH baselines: see `docs/implementation.md` and `docs/scenario_recipes.md`.
- Modules inject detailed clinical pathways (Phase 3). Current catalogue includes:
  `cardiometabolic_intensive`, `pediatric_asthma_management`, `prenatal_care_management`,
  `oncology_survivorship`, `ckd_dialysis_planning`, `copd_home_oxygen`, `mental_health_integrated_care`.

## 3. Run the Generator
### Minimal smoke test
```bash
python -m src.core.synthetic_patient_generator \
    --num-records 25 \
    --scenario cardiometabolic \
    --output-dir output/smoke
```

### Multi-module cohort with fixed seed
```bash
python -m src.core.synthetic_patient_generator \
    --num-records 200 \
    --scenario oncology_survivorship \
    --module ckd_dialysis_planning \
    --module mental_health_integrated_care \
    --seed 42 \
    --output-dir output/perf_baseline
```
- Combine scenario-default modules with extra `--module` flags; duplicates are deduplicated automatically.
- Use `--output-format csv|parquet|both` (default `both`). All artifacts land under the target directory with CSV/Parquet, `fhir_bundle.json`, HL7 ADT/ORU dumps, and optional VistA globals.

## 4. Validate Before Commit
- Structural checks: `python tools/module_linter.py --all`
- Regression tests: `pytest tests/test_module_engine.py tests/test_module_linter.py`
- Scenario-specific spot checks:
  - Inspect CSV counts with Polars or DuckDB.
  - Validate FHIR bundle via the quickstart primer (`primers/fhir_bundle_quickstart.md`).
  - Use `hl7_validation_playbook.md` snippets against ADT/ORU outputs.

## 5. Capture Performance Baselines
- Record `num-records`, modules, runtime, and artifact counts (example baseline: 200 patients with oncology + CKD + mental health ~17s, saved to `output/perf_baseline/`).
- Re-run after major module or exporter changes to catch regressions early.

## 6. Troubleshooting
- Empty terminology lookups → rerun `refresh_terminology.py`, ensure `TERMINOLOGY_DB_PATH` is set.
- CSV write errors about nested data → flatten lists (care plan activities already handled in generator).
- Randomness → supply `--seed` when reproducing bugs or benchmarks.

> Tip: keep generated artifacts under `output/` (git-ignored) so reviewers can reproduce or discard them quickly.
