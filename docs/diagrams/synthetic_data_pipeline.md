# Synthetic Data Pipeline

Visual overview of the orchestration in `src/core/synthetic_patient_generator.py`, focusing on how the CLI entrypoint fans out to generate patient records and export artifacts.

```mermaid
flowchart TD
    cli[CLI: python -m src.core.synthetic_patient_generator<br/>main()] --> cfg[Parse args + load_yaml_config]
    cfg --> pool[ThreadPoolExecutor<br/>generate_patient_with_dist()]
    pool --> rec[PatientRecord dataclass<br/>base demographics & IDs]
    rec --> cond[assign_conditions<br/>SDOH + genetic adjustments]
    cond --> enc[generate_encounters]
    cond --> markers[assign_precision_markers]
    enc --> meds[generate_medications<br/>evidence-based & precision]
    enc --> proc[generate_procedures]
    enc --> obs[generate_observations<br/>determine_lab_panels]
    rec --> allergy[generate_allergies]
    rec --> imm[generate_immunizations]
    rec --> family[generate_family_history]
    rec --> death[generate_death]
    cond --> care[generate_care_plans]
    markers --> meds
    meds --> collect[Persist enrichment onto PatientRecord.metadata]
    proc --> collect
    obs --> collect
    allergy --> collect
    imm --> collect
    family --> collect
    care --> collect
    death --> collect
    collect --> outputs[Polars assembly + save()]
    outputs --> csv[patients.csv / encounters.csv / ...]
    outputs --> fhir[FHIRFormatter<br/>fhir_bundle.json]
    outputs --> hl7[HL7v2Formatter<br/>ADT & ORU messages]
    outputs --> vista[export_vista_globals<br/>vista_globals.mumps]
    csv --> dashboard[tools/generate_dashboard_summary.py<br/>dash summary]
```
