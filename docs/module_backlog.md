# Clinical Module Backlog

This backlog enumerates clinical workflow modules to author in the v2 DSL (Synthea‑level parity). It tracks status and file paths so we can prioritize and measure progress.

Legend
- Implemented: functionally complete and covered by tests/validation
- Scaffolded: YAML placeholder exists (start→end); ready for expansion
- Planned: proposed; not yet scaffolded

## Implemented
- adult_primary_care_wellness — modules/adult_primary_care_wellness.yaml
- cardiometabolic_intensive — modules/cardiometabolic_intensive.yaml
- ckd_dialysis_planning — modules/ckd_dialysis_planning.yaml
- copd_home_oxygen — modules/copd_home_oxygen.yaml
- geriatric_polypharmacy — modules/geriatric_polypharmacy.yaml
- hiv_prep_management — modules/hiv_prep_management.yaml
- mental_health_integrated_care — modules/mental_health_integrated_care.yaml
- oncology_survivorship — modules/oncology_survivorship.yaml
- pediatric_asthma_management — modules/pediatric_asthma_management.yaml
- asthma_v2 — modules/asthma_v2.yaml
- copd_v2 — modules/copd_v2.yaml
- pregnancy_loss_support — modules/pregnancy_loss_support.yaml
- prenatal_care_management — modules/prenatal_care_management.yaml
- sepsis_survivorship — modules/sepsis_survivorship.yaml

## Scaffolded (ready to expand)
- hypertension_management — modules/hypertension_management.yaml
- type2_diabetes_management — modules/type2_diabetes_management.yaml
- hyperlipidemia_management — modules/hyperlipidemia_management.yaml
- heart_failure_management — modules/heart_failure_management.yaml
- atrial_fibrillation_management — modules/atrial_fibrillation_management.yaml
- cad_secondary_prevention — modules/cad_secondary_prevention.yaml
- stroke_tia_secondary_prevention — modules/stroke_tia_secondary_prevention.yaml
- ckd_progression_management — modules/ckd_progression_management.yaml
- liver_cirrhosis_management — modules/liver_cirrhosis_management.yaml
- hepatitis_c_management — modules/hepatitis_c_management.yaml
- obesity_weight_management — modules/obesity_weight_management.yaml
- hypothyroidism_management — modules/hypothyroidism_management.yaml
- osteoarthritis_management — modules/osteoarthritis_management.yaml
- rheumatoid_arthritis_management — modules/rheumatoid_arthritis_management.yaml
- osteoporosis_management — modules/osteoporosis_management.yaml
- chronic_pain_opioid_stewardship — modules/chronic_pain_opioid_stewardship.yaml
- substance_use_disorder_management — modules/substance_use_disorder_management.yaml
- major_depressive_disorder_management — modules/major_depressive_disorder_management.yaml
- generalized_anxiety_disorder_management — modules/generalized_anxiety_disorder_management.yaml
- dementia_management — modules/dementia_management.yaml
- epilepsy_management — modules/epilepsy_management.yaml
- migraine_management — modules/migraine_management.yaml
- obstructive_sleep_apnea_management — modules/obstructive_sleep_apnea_management.yaml
- psoriasis_management — modules/psoriasis_management.yaml
- crohns_disease_management — modules/crohns_disease_management.yaml
- ulcerative_colitis_management — modules/ulcerative_colitis_management.yaml
- gerd_management — modules/gerd_management.yaml
- copd_exacerbation_prevention — modules/copd_exacerbation_prevention.yaml
- community_acquired_pneumonia_episode — modules/community_acquired_pneumonia_episode.yaml
- covid19_outpatient_management — modules/covid19_outpatient_management.yaml
- tuberculosis_latent_infection — modules/tuberculosis_latent_infection.yaml
- tuberculosis_active_disease — modules/tuberculosis_active_disease.yaml
- postpartum_care_management — modules/postpartum_care_management.yaml
- contraception_family_planning — modules/contraception_family_planning.yaml
- cervical_cancer_screening — modules/cervical_cancer_screening.yaml
- breast_cancer_screening — modules/breast_cancer_screening.yaml
- prostate_cancer_screening — modules/prostate_cancer_screening.yaml
- colorectal_cancer_screening — modules/colorectal_cancer_screening.yaml
- lung_cancer_screening — modules/lung_cancer_screening.yaml
- pediatric_well_child_care — modules/pediatric_well_child_care.yaml
- pediatric_otitis_media — modules/pediatric_otitis_media.yaml
- adolescent_depression_screening — modules/adolescent_depression_screening.yaml
- adult_immunization_catchup — modules/adult_immunization_catchup.yaml
- allergy_anaphylaxis_pathway — modules/allergy_anaphylaxis_pathway.yaml
- allergy_immunotherapy_pathway — modules/allergy_immunotherapy_pathway.yaml
- end_of_life_palliative_care — modules/end_of_life_palliative_care.yaml

## Notes
- These scaffolds intentionally contain only structural start→end states to satisfy linting and allow incremental expansion.
- As we implement v2 DSL, modules will be migrated to richer flows that reference `data/parameters/*.yaml` and `docs/sources.yml`.
