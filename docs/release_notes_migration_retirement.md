# Migration Feature Retirement (2025 Q4)

These notes capture the final removal of migration-only simulators, dashboards, and artifacts from the Synthetic Healthcare Data Generator. The patient-focused lifecycle engine, terminology loaders, and exporters now run without any dormant migration toggles.

## Highlights
- Deleted remaining migration artifacts from the repository (snapshot directories, audit logs, and dashboard state) so only patient-generation assets remain.
- Documented and reviewed all end-user guides and examples to ensure they reference the clinical simulator exclusively; legacy realism whitepapers were annotated as historical context only.
- Published a streamlined GitHub Actions workflow that runs the Python test suite and CLI smokes on pushes/pull requests to enforce the new baseline.
- Refreshed dependency manifests—dropped migration-only dashboard libraries (`websockets`, `matplotlib`, `seaborn`) and re-validated installation via the project virtual environment.

## Validation
- CLI smokes: ran patient generation with `config/config.yaml` and `examples/config.yaml` (cardiometabolic scenario) to confirm all exporters succeed end-to-end.
- Targeted pytest bundles:
  - `pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_lifecycle_orchestrator.py`
  - `pytest tests/test_clinical_generation.py tests/test_module_engine.py`
  - `pytest tests/test_parameters_loader.py tests/test_scenario_loader.py`
- Full regression suite: `pytest` (102 tests) using Python 3.12 in `.venv`.
- Terminology build/install check: `pip install -r requirements.txt` inside the project virtual environment.

## Communication
- `docs/migration_removal_plan.md` updated with completion notes, validation evidence, and references to these release notes.
- Stakeholder sign-off recorded via this document; future simulator updates can reference this file instead of the retired migration workflow.
