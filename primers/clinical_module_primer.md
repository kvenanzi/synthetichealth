# Clinical Module Primer

This guide explains how Phase 3 workflow modules are authored, validated, and wired into scenarios so you can extend the simulator with new clinical pathways.

## 1. Module Anatomy
- **Location**: `modules/<module_name>.yaml`
- **Top-level fields**:
  - `name` (slug) and `description`
  - `categories`: controls which data domains the module replaces (`replace`) or augments (`augment`).
  - `states`: directed graph describing encounters, delays, decisions, etc.

### Supported state types
| Type | Purpose |
|------|---------|
| `start` / `terminal` | Entry/exit anchors |
| `delay` | Advance simulated time (`duration_days`) |
| `encounter` | Add encounter rows with metadata (type, location, provider) |
| `condition_onset` | Create conditions (ICD-10/SNOMED codes) |
| `medication_start` | Start meds (RxNorm, dose text) |
| `observation` | Emit labs/vitals (LOINC, numeric ranges) |
| `procedure` | Record procedures (code + coding system) |
| `immunization` | Register vaccines (CVX, dose info) |
| `care_plan` | Persist care plan goals + activities |
| `decision` | Branch with weighted probabilities (`probability` on each transition) |

Transitions are listed under `transitions` or `branches` (for decisions) as `to: <state>|end` plus optional `probability`.

## 2. Authoring Workflow
1. **Start from a template**: copy an existing module close to your target (e.g., `modules/oncology_survivorship.yaml`).
2. **Define categories**: mark domains you fully control with `replace` (encounters, conditions, medications for most modules) vs. `augment` when you add to generator output.
3. **Model the timeline**: use `delay` states to space follow-ups; keep loops bounded (ModuleEngine caps at 200 transitions per run).
4. **Embed terminology**: every condition/medication/observation should reference the appropriate ICD-10/SNOMED/RxNorm/LOINC/CVX codes already normalized in `data/terminology/`.
5. **Document sources**: capture clinical guideline references in `docs/scenario_recipes.md` so the provenance is transparent.

## 3. Validation & Testing
- **Static linting**: `python tools/module_linter.py --all`
  - wraps `validate_module_definition` (structure) + terminology checks (codes present for each state).
- **Unit tests**: add assertions to `tests/test_module_engine.py`
  - Verify conditions/medications/procedures/immunizations appear with expected codes.
  - Use deterministic seeds for reproducibility.
- **Scenario smoke test**:
  ```bash
  python -m src.core.synthetic_patient_generator \
      --num-records 25 \
      --scenario <your_scenario> \
      --output-dir output/module_smoke \
      --seed 123
  ```
  Inspect `conditions.csv`, `medications.csv`, etc., for plausibility.

## 4. Wiring Modules into Scenarios
1. Add the module name to `modules` within your scenario block in `src/core/lifecycle/scenarios.py`.
2. Update `docs/scenario_recipes.md` with an **Implementation** bullet referencing the YAML file.
3. Mention the new module in `docs/implementation.md` (Phase 3 checklist) if it represents a roadmap milestone.
4. Expose it via CLI by ensuring `--list-modules` finds the YAML (ModuleEngine uses filenames under `modules/`).

## 5. Best Practices
- Keep transition probabilities within ±5% of 1.0 (linter flags larger drift).
- Convert list-valued outputs (e.g., care plan `activities`) to strings before CSV export—already handled centrally in the generator.
- Avoid placeholder text like “TODO” in patient-facing strings; use realistic clinical language.
- For loops, pair `delay` + decision nodes to avoid tight cycles that could exceed visit cap.
- When referencing new terminology, update the DuckDB seeds or ensure the values exist in `data/terminology/<system>/*`.

Need inspiration? Review the cardiometabolic, oncology, CKD, COPD, and mental health modules for patterns covering chronic care, survivorship, and crisis workflows.
