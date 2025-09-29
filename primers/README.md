# Synthetic Data Primer Library

Use these focused guides to work with the simulator’s outputs, clinical modules, and validation workflow.

| File | Purpose |
|------|---------|
| `data_generation_workflow.md` | End-to-end checklist for running the generator, selecting scenarios/modules, and validating artifacts. |
| `clinical_module_primer.md` | YAML module authoring, validation (`tools/module_linter.py`), and scenario wiring tips. |
| `fhir_bundle_quickstart.md` | Parse and analyze the VSAC/UMLS-enriched FHIR bundle produced by Phase 3 modules. |
| `hl7_adt_quickstart.md` | Understand ADT message structure and export demographics to CSV. |
| `hl7_oru_quickstart.md` | Work with ORU lab results and observation groups. |
| `hl7_validation_playbook.md` | Layered HL7 validation (syntax → datatype → business rules). |
| `vista_mumps_quickstart.md` | Navigate the VistA MUMPS globals emitted for migration rehearsals. |

All examples assume the virtual environment (`.venv`) is active and outputs are generated under `output/` (git-ignored). The primers complement the technical references in `docs/` and the scenario backlog in `docs/scenario_recipes.md`. For probabilistic QA, see the Monte Carlo command in `data_generation_workflow.md`.
