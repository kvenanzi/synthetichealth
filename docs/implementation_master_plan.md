# Unified Implementation Plan

This file consolidates the actionable items that were previously scattered across:
- `docs/implementation.md`
- `docs/module_backlog.md`
- `docs/phase_3b_synthea_parity_plan.md`
- `docs/migration_removal_plan.md`

Treat this document as the single ordering of “what’s next.” Use the linked files for deep context, evidence, and historical notes.

---

## 0. Baseline (Up To Date)
- Migration retirement work is complete and validated (`docs/migration_removal_plan.md` – all boxes checked).
- Terminology platform, exporter parity, and the initial slate of Phase 3 modules are delivered (`docs/implementation.md`).
- GitHub Actions now runs `pytest` and both CLI smokes per push/PR (`.github/workflows/python-tests.yml`).

Keep these baselines green whenever making changes.

---

## 1. Clinical Module Expansion (Phase 3 Continuation)
Goal: keep shipping high-value v2 modules so scenarios have broader coverage.

Implement the following in order (each path in `modules/` is already scaffolded):
1. **Hyperlipidemia management** (`modules/hyperlipidemia_management.yaml`)
2. **Heart failure management** (`modules/heart_failure_management.yaml`)
3. **Atrial fibrillation management** (`modules/atrial_fibrillation_management.yaml`)
4. **CAD secondary prevention** (`modules/cad_secondary_prevention.yaml`)
5. **Stroke/TIA secondary prevention** (`modules/stroke_tia_secondary_prevention.yaml`)

For each module:
- Follow the v2 DSL patterns from `type2_diabetes_management` (sources + `use:` parameters + guardrails).
- Add Monte Carlo representation if medically relevant (update `tools/run_phase3_validation.py` and/or `validation/module_kpis/`).
- Update `docs/module_backlog.md` and `docs/implementation.md` when a module graduates from “scaffolded” to “implemented.”

Reference material: `docs/scenario_recipes.md`, `data/parameters/`, `docs/sources.yml`.

---

## 2. Phase 3B DSL Enhancements
Work through the remaining items in `docs/phase_3b_synthea_parity_plan.md` in this order:
1. **Conditional expressiveness**
   - Attribute comparisons (>, ≥, ≤, <) – basic support landed; extend tests + docs.
   - Demographic predicates driven by scenario metadata (age bands, race, SDOH attributes).
   - Logical composition (`and`/`or`/`not`) with nested `conditions` arrays (already partially supported—add tests and docs).
2. **Delay semantics**
   - Enforce provenance on all non-trivial delays (already linted) and document unit conversions.
   - Support `range` delays with units beyond days (weeks/months/years) in modules + tests.
3. **Submodule ergonomics**
   - Add guardrails so `call_submodule` can limit patients via module metadata (gender/risk flags).
   - Document attribute sharing/inheritance with examples (update `docs/phase_3b_synthea_parity_plan.md` + `docs/implementation.md`).
4. **Provenance enforcement**
   - Expand `tools/module_linter.py` to flag missing `sources` on any state containing `distributed_transition` or `delay`.
   - Ensure every parameter referenced via `use:` has a `source_id` in `data/parameters/*.yaml`.
5. **Validation artifacts**
   - Capture KPI specs for new flagship modules (e.g., diabetes) under `validation/module_kpis/`.
   - Teach `tools/run_phase3_validation.py` to run the new specs.

Document progress in both `docs/implementation.md` (Phase 3B section) and `docs/phase_3b_synthea_parity_plan.md`.

---

## 3. Parameter Store Expansion
To support the module work above:
- Add parameter files for cardiovascular domains (e.g., `data/parameters/hyperlipidemia.yaml`, `.../heart_failure.yaml`) mirroring the structure used by `asthma`, `copd`, and `diabetes`.
- Insert corresponding sources into `docs/sources.yml`.
- Update the linter tests if new domains are introduced.

---

## 4. Validation & Automation Enhancements
After modules/DSL updates land:
1. **CLI Coverage**
   - Convert the CLI smoke commands into pytest tests (extend `tests/test_cli_arguments.py` or create `tests/test_cli_smoke.py`) so local runs catch regressions even without the GitHub workflow.
2. **Performance Snapshots**
   - Re-run `tools/capture_performance_baseline.py --track-history` whenever major modules are added; log results in `performance/`.
3. **Exporter Regression**
   - For any module that introduces new resource types (e.g., anticoagulation procedures), add targeted assertions in `tests/test_clinical_generation.py` or `tests/test_vista_formatter.py`.

---

## 5. Documentation Touchpoints
Keep the following synced as work progresses:
- `docs/implementation.md` – high-level roadmap ticks.
- `docs/module_backlog.md` – module status.
- `docs/phase_3b_synthea_parity_plan.md` – detailed DSL/validation notes.
- `docs/release_notes_migration_retirement.md` – add entries when large chunks of migration cleanups or new phases finish.

---

## Quick Reminders
- Always run:
  - `python -m pytest`
  - `python -m src.core.synthetic_patient_generator --config config/config.yaml --num-records 5 --output-dir output/smoke_default --force`
  - `python -m src.core.synthetic_patient_generator --config examples/config.yaml --num-records 5 --output-dir output/smoke_examples --force`
  - `python tools/run_phase3_validation.py`
- Clean up generated `output/` directories after smokes.
- Update `docs/migration_removal_plan.md` if any automation or dependency changes affect the guarantees it documents.
