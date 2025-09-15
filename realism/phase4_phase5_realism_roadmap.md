# Clinical Realism Roadmap: Phases 4 & 5

## Goals
- Extend the synthetic generator to cover specialty clinical pathways, longitudinal outcomes, and equity-aware social determinants (Phase 4 scope from `realism/clinical_realism_assessment.md`).
- Replace Phase-1 seed vocabularies with terminology-backed catalogs (ICD-10-CM, SNOMED CT, RxNorm, CVX, CPT, LOINC) and propagate the codes through every export surface (CSV/Parquet, FHIR, HL7 v2, VistA, migration analytics).
- Maintain incremental delivery so downstream EHR migration simulations can adopt improvements without regression.

---

## Phase 4 – Specialized Clinical Domains & Equity Modeling

### Phase 4A: Specialty Clinical Pathways
**Objectives**
- Add condition, procedure, medication, lab, and outcome models for high-priority specialties: cardiology, oncology, behavioral health, endocrinology, pulmonology.
- Introduce longitudinal care plans (multi-encounter progression, episode-of-care bundles) and track guideline adherence metrics.

**Key Work Items**
1. **Clinical Requirements Gathering**
   - Review specialty care recommendations (ACC/AHA cardiology, NCCN oncology, ADA diabetes, GOLD COPD, APA behavioral health).
   - Translate into data requirements: condition subtypes, staging systems, interventions, monitoring cadence.
2. **Data Model Enhancements**
   - Expand `CONDITION_COMPLEXITY_MODELS` to include specialty staging (e.g., NYHA, GOLD, TNM refinements) and complication trees.
   - Extend procedure catalog (`CLINICAL_PROCEDURES`) and medication mappings with specialty-specific therapies (e.g., immunotherapy, biologics, advanced cardiac devices).
   - Add specialty lab panels (cardiac enzymes, tumor markers, psychiatric rating scales) with LOINC metadata.
3. **Generator Enhancements**
   - Implement episode-level simulation modules that sequence encounters, procedures, labs, and outcomes.
   - Tailor precision medicine logic for new biomarkers (e.g., KRAS, ALK, BNP-guided heart failure therapy).
   - Record new outputs in patient metadata for analytics (care pathways, stage transitions, specialty quality metrics).
4. **Validation**
   - Unit and integration tests for each specialty scenario.
   - Compare generated data distributions against published epidemiology/registry benchmarks.

**Deliverables**
- Updated generator code with specialty modules and QA scripts.
- Specialty-focused sample datasets and documentation.
- Clinical pathway dashboard additions for migration analytics.

### Phase 4B: Advanced SDOH & Health Equity Modeling
**Objectives**
- Move beyond current binary SDOH adjustments to incorporate geographic context, access-to-care parameters, and structural inequities.

**Key Work Items**
1. **SDOH Data Inputs**
   - Ingest or simulate census tract-level factors (Area Deprivation Index, food access, transportation scores).
   - Model insurance churn, provider network access, language proficiency, and social support indicators.
2. **Risk & Outcome Modeling**
   - Build propensity functions linking SDOH indices to disease incidence, progression, adherence, and mortality.
   - Simulate care gaps (missed screenings, delayed follow-up) and resource referrals.
3. **Output & Analytics**
   - Extend patient metadata with structured SDOH coding (SNOMED/LOINC SDOH assessment tools, Gravity Project terminology).
   - Add equity dashboards (by race, geography, income) and validation harness comparing distributions to reference data.

**Deliverables**
- Enhanced SDOH feature library and risk engine.
- Equity-aware quality measures in migration reporting.

**Success Criteria for Phase 4**
- Specialty conditions/procedures detectable in exports with realistic staging, therapy mix, and outcomes.
- SDOH metrics influence disease trajectory, care pathways, and quality indicators in a traceable manner.
- QA suite demonstrating no regression to Phase 1–3 functionality.

---

## Phase 5 – Terminology Normalization & Interoperability Expansion

### Phase 5A: Terminology Catalog Foundation
**Objectives**
- Replace placeholder lists with comprehensive, code-system-backed catalogs.

**Key Work Items**
1. Source authoritative vocabularies (ICD-10-CM, SNOMED CT, RxNorm, CVX, CPT, HCPCS, LOINC, UNII) via UMLS/VSAC or open subsets.
2. Build normalized catalog files (e.g., YAML/Parquet) capturing identifiers, preferred terms, synonyms, categories, specialty tags, and usage notes.
3. Define governance metadata (version, release date, licensing) for reproducibility.

### Phase 5B: Generator Refactor for Code Usage
**Objectives**
- Migrate generator logic to consume the terminology catalogs and emit codes everywhere.

**Key Work Items**
1. Refactor condition/medication/procedure assignment to reference catalog entries by code.
2. Update precision medicine, comorbidity, and SDOH engines to use code-based lookups and categories.
3. Ensure every data artifact (CSV columns, FHIR resources, HL7 segments, VistA globals, migration analytics) carries appropriate coding (primary + alternate systems).
4. Provide backwards-compatible naming for legacy consumers (include both `display` and code columns/fields).

### Phase 5C: Interoperability Packaging & Testing
**Objectives**
- Validate terminology usage and interoperability against external tooling.

**Key Work Items**
1. Add automated validators (FHIR terminology services, HL7 v2 schema checks, custom SQL assertions) verifying codes exist and align with value set constraints.
2. Produce sample integration packs (FHIR bundles, HL7 message sets, CSV extracts) for major specialties including code metadata.
3. Update documentation and user guides highlighting terminology support and migration strategies.

**Deliverables for Phase 5**
- Terminology catalog repository with ingest scripts and tests.
- Refactored generator with code-first data model.
- Interoperability validation reports and sample datasets.

**Success Criteria for Phase 5**
- ≥95% of generated clinical elements bear at least one standard code, with crosswalks where applicable.
- All export formats validated against external tooling (FHIR ValueSet expand, HL7 conformance, VistA loader sanity checks).
- Documentation guiding users on terminology versioning and customization.

---

## Cross-Phase Considerations
- **Data Volume & Performance:** Monitor generation time/size as catalogs expand; optimize where necessary (lazy loading, caching, vectorized operations).
- **Clinical SME Review:** Schedule checkpoints with clinical informatics SMEs for content validation.
- **Governance:** Establish release tagging, change logs, and regression test expectations for each phase.
- **Downstream Alignment:** Coordinate with migration simulation and analytics teams so new metadata is surfaced in dashboards and quality reports.

---

## Recommended Sequencing
1. Complete Phase 4A and 4B together to ensure specialty/SDOH modeling informs terminology selection.
2. Execute Phase 5A (catalog creation) in parallel with late Phase 4 tasks so the terminology foundation is ready when specialty logic needs richer vocabularies.
3. Deliver Phase 5B/5C after Phase 4 stabilization to refactor the generator with minimal moving pieces.
4. Follow each phase with dedicated validation sprints and documentation updates.

---

## Next Steps
- Approve the roadmap and identify clinical SMEs and terminology sources.
- Create detailed engineering tickets per phase/work item.
- Begin Phase 4A data-model design while drafting terminology ingestion scripts (Phase 5A).
