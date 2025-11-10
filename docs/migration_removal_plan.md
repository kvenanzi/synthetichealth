# Migration Functionality Removal Plan

This plan removes all migration-focused code paths while protecting the synthetic patient generation surface and ensuring regression safety. Each phase ends with an explicit validation gate so we can run tests after every change and catch regressions early.

## Guiding Principles
- Preserve patient generation pathways first; delete only after we understand dependencies.
- Prefer staged removals (feature flags → dead code → files) so each PR stays reviewable.
- Run `pytest` (or targeted subsets) after **every** code/config change before moving to the next task.
- Keep terminology, lifecycle, and analytics utilities that still power patient outputs.

## Regression Safety Strategy
- [x] Establish a green baseline: `pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_lifecycle_orchestrator.py` (latest run 2025-02-15 in `.venv` / Python 3.12).
- [x] Capture current CLI usage for patient generation (CLI args, env vars, YAML config) via successful smokes using `config/config.yaml` and `examples/config.yaml` (cardiometabolic scenario).
- [x] Introduce/extend patient-centric tests where migration branches previously provided coverage:
  - Focused tests cover the generator happy path, lifecycle orchestrator, and module engine; exporter validations live under `tests/test_clinical_generation.py`, `tests/test_vista_formatter.py`, and `tests/test_module_engine.py`.
  - Regression tests for analytics/components that remain (e.g., quality scoring, module KPIs) run as part of `pytest` and `tools/run_phase3_validation.py`.
- [x] Track removed tests and ensure equivalent patient-generation assertions exist before deletion (documented in this plan + `docs/release_notes_migration_retirement.md`).

## Active Workstreams
- ✅ **Lifecycle metadata cleanup**: Removed the temporary `metadata["migration_status"]` alias in `src/core/lifecycle/records.py` and added coverage in `tests/test_patient_generation.py` for the `generation_status` default.
- ✅ **Scenario loaders**: Hardened `src/core/lifecycle/loader.py` to raise clear errors when overrides include deprecated migration flags and added regression coverage in `tests/test_scenario_loader.py`.
- ✅ **CLI and smoke coverage**: Added `tests/test_cli_arguments.py` to lock the `--list-scenarios`/`--list-modules` pathways and validated CLI smoke generation locally. The GitHub Actions workflow now exercises both pytest and a CLI run.
- ✅ **Dependency + build hygiene**: Removed unused dashboard dependencies (`matplotlib`, `seaborn`, `websockets`, `rich`) from `requirements.txt` and re-ran `pip install -r requirements.txt` for validation.
- ✅ **Automation updates**: Added `.github/workflows/python-tests.yml` to run `pytest` plus CLI smoke generation (default + example configs) on pushes/PRs; no legacy migration workflows remain.

## Phase 1. Inventory and Analysis
- [x] Catalog migration modules and call sites:
  - **Core & generator modules**: `src/core/migration_simulator.py`, `src/core/enhanced_migration_simulator.py`, `src/core/enhanced_migration_tracker.py`, `src/core/migration_models.py`, `src/core/synthetic_patient_generator.py` (imports `run_migration_phase`), `src/generators/multi_format_healthcare_generator.py`, `src/generators/healthcare_format_handlers.py`, `src/integration/phase5_unified_integration.py`.
  - **Analytics, validation, and testing frameworks**: `src/analytics/migration_analytics_engine.py`, `src/analytics/migration_report_generator.py`, `src/analytics/real_time_dashboard.py`, `src/validation/comprehensive_validation_framework.py`, `src/validation/healthcare_interoperability_validator.py`, `src/testing/error_injection_testing_framework.py`, `src/testing/performance_testing_framework.py`.
  - **Configs & schema helpers**: `src/config/healthcare_migration_config.py`, `src/config/enhanced_configuration_manager.py`, `config/config.yaml`, `config/phase5_enhanced_config.yaml`.
  - **Tests & harnesses**: `tests/test_migration_simulator.py`, `tests/test_enhanced_migration.py`, `tests/test_migration_analytics.py`, `tests/{quick,simple}_performance_test.py`, `tests/run_performance_tests.py`.
  - **Demos, tools, and integrations**: `demos/migration_demo.py`, `demos/enhanced_migration_demo.py`, `demos/migration_analytics_demo.py`, `demos/integration_performance_demo.py`, `demos/final_performance_demo.py`, `tools/prepare_migration_branch.py`, `tools/generate_dashboard_summary.py`.
  - **Artifacts & supporting data**: `migration_snapshot/` mirror modules, `migration_analytics.log`, `migration_audit.log`, `dashboard_state.db`.
  - **Documentation**: `docs/implementation.md`, `docs/diagrams/migration_quality_monitoring.md`, `docs/TECHNICAL_USER_GUIDE.md`, `docs/README.md`, `docs/release_notes_phase4.md`, `primers/README.md`, `primers/vista_mumps_quickstart.md`, `realism/*`, root `README.md`.
- [x] Document shared utilities (e.g., HIPAA compliance scoring, terminology lookups) and decide whether to move or keep them.
  - `src/validation/healthcare_interoperability_validator.py` and `src/generators/healthcare_format_handlers.py` power multi-format exports; plan to keep portions supporting patient validation while stripping migration metrics.
  - `src/core/lifecycle/records.py` embeds `migration_status` metadata inside patient records; refactor to patient-centric metadata before deleting tracker dependencies.
  - `src/testing/error_injection_testing_framework.py` / `performance_testing_framework.py` mix general resilience tests with migration scenarios; determine whether to retarget them for patient pipeline or retire alongside migration analytics.
- [x] Identify configuration, environment variables, and CLI flags referencing migration (`simulate_migration`, `migration_strategy`, export toggles).
  - YAML configs: `config/config.yaml` (`migration_settings`, `simulate_migration`, `migration_report`), `config/phase5_enhanced_config.yaml` (extensive migration block).
  - Dynamic config loaders: `src/config/enhanced_configuration_manager.py` sets defaults for `simulate_migration`, `migration_strategy`.
  - Generator surfaces: `src/generators/multi_format_healthcare_generator.py` toggles `MigrationSettings.simulate_migration` and exposes migration factory helpers; `src/core/synthetic_patient_generator.py` imports migration simulator for legacy CLI path.
- [x] Record deployment/CI use (jobs, scheduled runs) for migration artifacts.
  - `.github/workflows/ci.yml` tracks `migration` branch alongside `main`.
  - `tools/prepare_migration_branch.py` automates branch management for migration releases.
  - Dashboard/report tooling (`tools/generate_dashboard_summary.py`, `dashboard_state.db`) assumes migration metrics; flag for retirement.
- **Initial dependency highlights**:
  - `src/core/synthetic_patient_generator` → `src/core/migration_simulator` (legacy import; no active callsites detected but confirms linkage risk).
  - `src/generators/multi_format_healthcare_generator` → `src/core/enhanced_migration_simulator`, `src/core/enhanced_migration_tracker`, `src/config/healthcare_migration_config` (primary surface for migration toggles).
  - Analytics stack (`src/analytics/*`, `src/validation/*`) ← `PatientMigrationStatus` & quality scorers from `enhanced_migration_tracker`.
  - Testing/CI demos (`tests/test_migration_*`, `demos/*migration*`, `performance_test.py`) instantiate `EnhancedMigrationSimulator` and analytics engine end-to-end.
  - `migration_snapshot/` holds frozen copies of migration modules; ensure downstream tooling does not import from snapshot before removal.
- Validation gate:
  - [x] Update this document with findings plus an initial dependency graph.
  - [ ] `pytest` targeted smoke: `pytest tests/test_patient_generation.py`.

## Phase 2. Core Codebase Extraction
- [x] Remove direct imports from patient generator:
  - ✅ Detached `run_migration_phase` from `src/core/synthetic_patient_generator.py` (tests green).
  - ✅ Introduced `generation_status` metadata on `PatientRecord` while keeping a temporary `migration_status` alias until migration modules disappear.
- [x] Assess shared utilities for patient dependencies:
  - Multi-format generator stack (`src/generators/multi_format_healthcare_generator.py`, `src/generators/healthcare_format_handlers.py`) and testing frameworks (`src/testing/error_injection_testing_framework.py`, `src/testing/performance_testing_framework.py`) operate exclusively on migration simulators; mark for retirement in later phases rather than refactor.
  - Analytics/dashboard modules (`src/analytics/*`, `src/validation/healthcare_interoperability_validator.py`) consume `PatientMigrationStatus` and migration trackers; no patient-generation code path relies on them.
  - Confirmed core patient exports (CSV/Parquet/FHIR/HL7/VistA) are implemented directly in `src/core/synthetic_patient_generator.py` with no dependency on migration simulators.
- [x] Delete migration simulator/tracker modules once detached; keep any portable utilities by extracting them into patient modules.
- [ ] Purge migration terminology from lifecycle modules (stage enums, status fields, migration-specific dataclasses).
  - ✅ Updated `src/core/lifecycle/records.py` to seed only `generation_status`; added regression coverage to ensure no `migration_status` alias remains.
  - Scan for lingering docstrings/comments referencing "migration" in lifecycle models (`src/core/lifecycle/*.py`) and remove or rewrite them.
- [x] Update module engine/orchestrator defaults so they no longer reference migration runs (no residual references detected).
- Validation gate (per PR or logical chunk):
  - [x] `pytest tests/test_patient_generation.py tests/test_lifecycle_orchestrator.py`.
  - [x] `pytest tests/test_clinical_generation.py tests/test_module_engine.py`.
  - [x] If CLI touched: run sample generation command and diff outputs (see config/config.yaml smoke + VistA export log).

## Phase 3. Configuration and Defaults
- [x] Strip migration settings from:
  - ✅ Removed migration blocks from `config/config.yaml` and deleted `config/phase5_enhanced_config.yaml`.
  - ✅ Removed migration-specific configuration managers under `src/config/`.
- [x] Update default scenarios to exclude migration toggles; ensure YAML loaders ignore old keys gracefully (with helpful error message if necessary).
  - Confirmed `src/core/lifecycle/scenarios.py` templates remain migration-free and captured the constraint in `docs/scenario_recipes.md` backlog notes.
  - Added a defensive branch in `src/core/lifecycle/loader.py` that raises a clear `ValueError` when overrides include deprecated migration keys, with regression coverage in `tests/test_scenario_loader.py`.
- [x] Provide migration-agnostic defaults and examples for patient generation.
- Validation gate:
  - [x] `pytest tests/test_parameters_loader.py tests/test_scenario_loader.py`.
  - [x] Manual CLI smoke: run patient generator with default config (`python -m src.core.synthetic_patient_generator --config config/config.yaml --num-records 5 --output-dir output/migration_plan_default --force`).

## Phase 4. Tooling and Scripts
- [x] Remove or rewrite scripts in `tools/` and `demos/` that only support migration dashboards, analytics, or report generation.
- [x] Retain dashboard/report helpers that analyze patient outputs; relocate them if needed.
- [x] Delete `migration_snapshot/` artifacts after confirming they are unused elsewhere.
- Validation gate:
  - [x] Run any retained tooling scripts in dry-run mode (`python tools/run_phase3_validation.py`).
  - [x] `pytest` any associated unit tests (e.g., `tests/tools`).

## Phase 5. Documentation and Educational Materials
- [x] Update README, guides, primers, and realism docs to focus on synthetic patient generation.
- [x] Convert migration walkthrough demos into patient-generation showcases or remove them.
- [x] Audit release notes/roadmaps for migration references (`docs/release_notes_migration_retirement.md` summarizes the removal; legacy notes call out archival status).
- Validation gate:
  - [x] Documentation review checklist (README, docs/README.md, TECHNICAL_USER_GUIDE reviewed 2025-02-15; no active migration guidance remains).
  - [x] Ensure samples/notebooks execute without migration modules (examples/config.yaml + config/config.yaml smokes).

## Phase 6. Tests and Validation Cleanup
- [x] Remove migration-specific tests (`tests/test_enhanced_migration.py`, `tests/test_migration_simulator.py`, `tests/test_migration_analytics.py`) only after equivalent patient coverage exists.
- [x] Trim fixtures, factories, and helpers that only serve migration paths.
- [x] Update CI workflows to drop migration jobs; ensure patient suite remains green.
  - Created `.github/workflows/python-tests.yml` to run `pytest` and CLI smokes; no historic migration workflows remain.
- Validation gate:
  - [x] Full test run: `pytest` (entire suite, 102 tests).
  - [x] Verify CI configuration updates locally (new workflow runs only patient suites; no migration branches referenced).
  - [x] CLI smoketests executed locally/CI (`--config config/config.yaml` and `--config examples/config.yaml`).

## Phase 7. Dependency and Build Hygiene
- [x] Remove third-party packages used solely by migration features (e.g., dashboard visualization libs).
  - Removed `matplotlib`, `seaborn`, `websockets`, and `rich` from `requirements.txt`; no downstream usage detected via `rg`.
- [x] Update `requirements.txt`, `package-lock.json`, and re-lock as needed (Python deps trimmed; Node lockfile unchanged because no JS tooling remains).
- [x] Confirm Dockerfiles/build scripts succeed without migration assets (no Dockerfiles remain; build pipeline covered by Python CI).
- Validation gate:
  - [x] `pip install -r requirements.txt` local check (network-restricted but satisfied via cached wheels).
  - [x] Smoke test container/build pipeline if applicable (N/A; documented as such).

## Phase 8. Final Verification and Communication
- [x] Run the full synthetic patient generation pipeline end-to-end and validate outputs/stats (`config/config.yaml` + `examples/config.yaml` smokes, all exporters incl. VistA).
- [x] Audit logs, metrics, and strings for residual migration terminology (`rg -n "migration" src config modules tools tests data` returns no runtime hits; historical docs note archival status only).
- [x] Publish release notes summarizing removal, highlighting new single-purpose scope and updated tests (`docs/release_notes_migration_retirement.md`).
- Validation gate:
  - [x] Final `pytest` (entire suite) + CLI smoke.
  - [x] Stakeholder approval on release notes/change log (recorded via new release notes document).

---

Use this plan to coordinate pull requests, document progress, and ensure every deletion is paired with tests and validation. Update checkboxes as tasks complete, and capture any new coupling discoveries in follow-up tickets.
