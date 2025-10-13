# Synthetic Data Pipeline

Visual overview of the orchestration in `src/core/synthetic_patient_generator.py`, focusing on how the CLI entrypoint fans out to generate patient records and export artifacts.

```mermaid
flowchart TD
    cli["CLI: python -m src.core.synthetic_patient_generator<br/>main()"] --> cfg["Parse args + load_yaml_config"]
    cfg --> scenario["load_scenario_config + build ModuleEngine"]
    scenario --> profiles["ThreadPoolExecutor map<br/>generate_patient_profile_for_index"]
    profiles --> rec["Instantiate PatientRecord<br/>generate IDs & metadata shells"]
    rec --> moduleExec["ModuleEngine.execute (optional)<br/>replacements + attributes"]
    moduleExec --> preassign["assign_conditions<br/>merge module preassignments"]
    preassign --> family["generate_family_history"]
    preassign --> enc["generate_encounters<br/>+ module encounters"]
    enc --> conditions["generate_conditions<br/>+ module conditions"]
    conditions --> meds["generate_medications<br/>merge module medications"]
    conditions --> proc["generate_procedures"]
    conditions --> obs["generate_observations<br/>+ immunization followups"]
    rec --> allergy["generate_allergies"]
    rec --> imm["generate_immunizations<br/>+ module immunizations"]
    rec --> death["generate_death"]
    meds --> care["generate_care_plans<br/>merge module plans"]
    obs --> care
    proc --> care
    imm --> obs
    care --> collect["Persist enrichment onto PatientRecord.metadata"]
    meds --> collect
    obs --> collect
    proc --> collect
    allergy --> collect
    imm --> collect
    family --> collect
    death --> collect
    moduleExec --> collect
    collect --> outputs["Polars assembly + save()"]
    outputs --> csv["patients.csv / encounters.csv / ..."]
    outputs --> fhir["FHIRFormatter<br/>save_fhir_bundle"]
    outputs --> hl7["HL7v2Formatter<br/>save_hl7_messages"]
    outputs --> vista["VistaFormatter<br/>export_vista_globals"]
    csv --> dashboard["tools/generate_dashboard_summary.py<br/>dash summary"]
```
