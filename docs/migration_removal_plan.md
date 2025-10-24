# Migration Functionality Removal Plan

This plan removes all migration-focused code paths while protecting the synthetic patient generation surface and ensuring regression safety. Each phase ends with an explicit validation gate so we can run tests after every change and catch regressions early.

## Guiding Principles
- Preserve patient generation pathways first; delete only after we understand dependencies.
- Prefer staged removals (feature flags → dead code → files) so each PR stays reviewable.
- Run `pytest` (or targeted subsets) after **every** code/config change before moving to the next task.
- Keep terminology, lifecycle, and analytics utilities that still power patient outputs.

## Regression Safety Strategy
- [ ] Establish a green baseline: `pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_lifecycle_orchestrator.py`.
- [ ] Capture current CLI usage for patient generation (CLI args, env vars, YAML config).
- [ ] Introduce/extend patient-centric tests where migration branches previously provided coverage:
  - Add focused tests for `src/core/synthetic_patient_generator.py` happy path and CLI parsing.
  - Add regression tests for analytics/components that remain (e.g., patient quality scoring) so we can delete migration-specific metrics confidently.
- [ ] Track removed tests and ensure equivalent patient-generation assertions exist before deletion.

## Phase 1. Inventory and Analysis
- [ ] Catalog migration modules and call sites:
  - `src/core/migration_simulator.py`, `src/core/enhanced_migration_simulator.py`, trackers, analytics (`src/analytics/migration_*`), validation, dashboards, and CLI hooks.
  - `tests/test_migration_*.py`, demo notebooks/scripts, data snapshots, `migration_*` logs.
- [ ] Document shared utilities (e.g., HIPAA compliance scoring, terminology lookups) and decide whether to move or keep them.
- [ ] Identify configuration, environment variables, and CLI flags referencing migration (`simulate_migration`, `migration_strategy`, export toggles).
- [ ] Record deployment/CI use (jobs, scheduled runs) for migration artifacts.
- Validation gate:
  - [ ] Update this document with findings plus an initial dependency graph.
  - [ ] `pytest` targeted smoke: `pytest tests/test_patient_generation.py`.

## Phase 2. Core Codebase Extraction
- [ ] Remove direct imports from patient generator:
  - Detach `run_migration_phase` from `src/core/synthetic_patient_generator.py`.
  - Replace migration metadata fields with patient-centric equivalents (audit logging, metrics).
- [ ] Delete migration simulator/tracker modules once detached; keep any portable utilities by extracting them into patient modules.
- [ ] Purge migration terminology from lifecycle modules (stage enums, status fields, migration-specific dataclasses).
- [ ] Update module engine/orchestrator defaults so they no longer reference migration runs.
- Validation gate (per PR or logical chunk):
  - [ ] `pytest tests/test_patient_generation.py tests/test_lifecycle_orchestrator.py`.
  - [ ] `pytest tests/test_clinical_generation.py tests/test_module_engine.py`.
  - [ ] If CLI touched: run sample generation command and diff outputs.

## Phase 3. Configuration and Defaults
- [ ] Strip migration settings from:
  - `config/config.yaml`, phase configs, demo configs, `.env` templates.
  - CLI arguments (argparse definitions) and environment variable docs.
- [ ] Update default scenarios to exclude migration toggles; ensure YAML loaders ignore old keys gracefully (with helpful error message if necessary).
- [ ] Provide migration-agnostic defaults and examples for patient generation.
- Validation gate:
  - [ ] `pytest tests/test_parameters_loader.py tests/test_scenario_loader.py`.
  - [ ] Manual CLI smoke: run patient generator with default config.

## Phase 4. Tooling and Scripts
- [ ] Remove or rewrite scripts in `tools/` and `demos/` that only support migration dashboards, analytics, or report generation.
- [ ] Retain dashboard/report helpers that analyze patient outputs; relocate them if needed.
- [ ] Delete `migration_snapshot/` artifacts after confirming they are unused elsewhere.
- Validation gate:
  - [ ] Run any retained tooling scripts in dry-run mode.
  - [ ] `pytest` any associated unit tests (e.g., `tests/tools`).

## Phase 5. Documentation and Educational Materials
- [ ] Update README, guides, primers, and realism docs to focus on synthetic patient generation.
- [ ] Convert migration walkthrough demos into patient-generation showcases or remove them.
- [ ] Audit release notes/roadmaps for migration references.
- Validation gate:
  - [ ] Documentation review checklist.
  - [ ] Ensure samples/notebooks execute without migration modules.

## Phase 6. Tests and Validation Cleanup
- [ ] Remove migration-specific tests (`tests/test_enhanced_migration.py`, `tests/test_migration_simulator.py`, `tests/test_migration_analytics.py`) only after equivalent patient coverage exists.
- [ ] Trim fixtures, factories, and helpers that only serve migration paths.
- [ ] Update CI workflows to drop migration jobs; ensure patient suite remains green.
- Validation gate:
  - [ ] Full test run: `pytest`.
  - [ ] Verify CI configuration updates locally (e.g., `tox`, GitHub Actions dry-run).

## Phase 7. Dependency and Build Hygiene
- [ ] Remove third-party packages used solely by migration features (e.g., dashboard visualization libs).
- [ ] Update `requirements.txt`, `package-lock.json`, and re-lock as needed.
- [ ] Confirm Dockerfiles/build scripts succeed without migration assets.
- Validation gate:
  - [ ] `pip install -r requirements.txt` local check (or equivalent lock refresh).
  - [ ] Smoke test container/build pipeline if applicable.

## Phase 8. Final Verification and Communication
- [ ] Run the full synthetic patient generation pipeline end-to-end and validate outputs/stats.
- [ ] Audit logs, metrics, and strings for residual migration terminology.
- [ ] Publish release notes summarizing removal, highlighting new single-purpose scope and updated tests.
- Validation gate:
  - [ ] Final `pytest` (entire suite) + CLI smoke.
  - [ ] Stakeholder approval on release notes/change log.

---

Use this plan to coordinate pull requests, document progress, and ensure every deletion is paired with tests and validation. Update checkboxes as tasks complete, and capture any new coupling discoveries in follow-up tickets.
