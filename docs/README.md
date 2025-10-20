# Synthetic Healthcare Simulator Documentation

This directory captures the reference material for the Phase 2+/Phase 3 rewrite of the synthetic healthcare generator. The primary codebase now centers on lifecycle-driven clinical realism, normalized terminology services, and multi-format exports. Use these docs to navigate the simulator, extend clinical content, and validate outputs.

## Orientation
- `implementation.md` – authoritative roadmap and phase checkpoints; review this before picking up new work.
- `TECHNICAL_USER_GUIDE.md` – end-to-end usage guide covering environment setup, generation CLI, and export knobs.
- `scenario_recipes.md` – cookbook for composing lifecycle scenarios and linking module YAML.
- `module_backlog.md` – status tracker for authored vs. scaffolded clinical workflow modules.
- `phase_3b_synthea_parity_plan.md` – long-range realism plan aligned with Synthea’s DSL depth.
- `diagrams/` – architecture and dataflow diagrams for presentations and onboarding.

## Getting Started
1. Install Python 3.10+ and create a virtual environment (the generator leans on Polars, DuckDB, and Faker).
2. Install core dependencies with `pip install -r data/requirements.txt`; add extras from `requirements.txt` when running analytics or migration tooling.
3. Stage terminology seeds under `data/terminology/` or import the official releases using the scripts in `tools/` (see the quick start section in the project `README.md`).
4. Build or refresh the DuckDB warehouse with `python tools/build_terminology_db.py --root data/terminology --output data/terminology/terminology.duckdb --force` once normalized CSVs are available.
5. Generate patients via `python -m src.core.synthetic_patient_generator --num-records 1000 --output-dir output` and explore the emitted CSV, Parquet, FHIR, HL7, and VistA artifacts.

## Analytics & Validation
- Run `pytest tests/test_clinical_generation.py tests/test_med_lab_realism.py tests/test_module_engine.py` before landing changes.
- Execute `python tools/run_phase3_validation.py` for the composite Monte Carlo + exporter integrity harness.
- Capture performance baselines when investigating throughput or memory regressions with `python tools/capture_performance_baseline.py --track-history`.
- Use `tools/module_linter.py` and `tools/module_monte_carlo_check.py` while authoring or extending module YAML.

## Migration Track (Legacy Support)
Legacy migration simulators, analytics dashboards, and demos now live on the long-lived `migration` branch. Switch with `git switch migration` when rehearsing ETL pipelines or VistA-to-Oracle conversion flows. The main branch keeps lightweight migration utilities under `src/core/migration_simulator.py`, but all new work should be scoped around the clinical simulator.

## Contributing Tips
- Keep terminology-backed catalogs (conditions, medications, allergens, labs) source-controlled only for seed data; official releases should remain outside Git.
- Scenario and module edits should cite evidence in `docs/sources.yml` whenever possible.
- Update `docs/implementation.md` after completing a roadmap item so the next session has an accurate checkpoint.
- When adding new exports or terminology dependencies, update both the main `README.md` and this docs index to reflect the change.
