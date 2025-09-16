# Patient Attribute Enrichment

Captures how SDOH context, genetic markers, and precision medicine logic in `src/core/synthetic_patient_generator.py` evolve a base patient dictionary into rich metadata.

```mermaid
flowchart LR
    patient[Patient dict snapshot] --> sdoh[calculate_sdoh_risk<br/>+ generate_sdoh_context<br/>write sdoh_* fields]
    sdoh --> adj[apply_sdoh_adjustments<br/>condition probabilities]
    patient --> genetics[determine_genetic_risk<br/>+ genetic_markers]
    adj --> assign[assign_conditions<br/>condition_profile]
    genetics --> assign
    assign --> comorbid[apply_comorbidity_relationships<br/>comorbidity_profile]
    assign --> precision[assign_precision_markers<br/>precision targets]
    precision --> meds[generate_medications<br/>contraindication checks]
    assign --> labs[determine_lab_panels -> generate_lab_panel<br/>observation status]
    assign --> care[generate_care_plans<br/>care_plan_summary]
    meds --> record[PatientRecord.metadata updated]
    labs --> record
    care --> record
    comorbid --> record
    sdoh --> record
    genetics --> record
```
