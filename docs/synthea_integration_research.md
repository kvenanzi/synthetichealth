# Synthea Module Insights & Roadmap for High-Fidelity Scenarios

Prepared after reviewing Synthea Module Builder examples for **Allergic Rhinitis**, **Appendicitis**, and **Breast Cancer Chemotherapy**. Use this document as a reference when designing Phase 3 clinical realism enhancements.

## 1. What Synthea Modules Provide
- **State Machine Architecture**: Each module is a directed graph of states (encounter, condition, medication, delay, decision) with explicit transition logic and probabilities.
- **Guideline-Driven Parameters**: Medication regimens, encounter cadence, diagnostics, and branching logic cite clinical practice guidelines (e.g., AAAAI for allergic rhinitis, ACOG/ACS for breast oncology, CDC surgical recommendations for appendicitis).
- **Temporal Precision**: Modules encode delays (hours/days/weeks) and repeated loops (maintenance medication, follow-up imaging) to simulate longitudinal care.
- **Comorbidity Hooks**: Modules check patient attributes (age, gender, risk flags) to alter pathways.
- **Decision Points**: Probabilistic splits mimic real-world variation (e.g., appendicitis perforation vs uncomplicated recovery; chemotherapy toxicity requiring dose adjustment).

## 2. Observations by Example
### Allergic Rhinitis
- Entry via primary care encounter; evaluation includes allergy testing, differential diagnoses, and severity stratification.
- Treatment states escalate from oral antihistamines to intranasal steroids, leukotriene inhibitors, and immunotherapy referrals.
- Follow-up loops assess symptom control; failure branches escalate therapy or trigger specialist referral.

### Appendicitis
- Acute symptom onset leads to ED encounter, imaging, surgical consult, and OR decision.
- Branches for laparoscopic vs open appendectomy, perforation risk, post-op antibiotics, and readmission due to infection.
- Incorporates pediatric vs adult differences and models time-to-treatment delays.

### Breast Cancer Chemotherapy
- Staging and biomarker testing precede regimen selection (AC-T, TC, etc.).
- Cyclical chemo visits trigger labs, toxicity checks, dose holding, antiemetic support, and post-chemo surveillance.
- Includes survivorship plan (annual mammogram, endocrine therapy adherence) and recurrence monitoring.

## 3. Clinical Data Sources for Module Detail
- **Clinical Practice Guidelines**: NCCN, USPSTF, ACOG, ADA, ACC/AHA, GOLD, ASCO, CDC Pink Book.
- **Peer-Reviewed Studies**: PubMed systematic reviews for event probabilities, complication rates, adherence metrics.
- **Public Registries & Datasets**: SEER (oncology), NHANES, HCUP, National Surgical Quality Improvement Program (NSQIP).
- **Medication Databases**: RxNorm, DailyMed, WHO ATC classification for therapy sequencing.
- **Expert Consultation**: Clinical informatics SMEs validate workflows, especially for nuanced pathways (e.g., obstetrics, oncology).

## 4. Roadmap for Synthea-Level Realism in Our Simulator
### 4.1 Architecture Enhancements (Phase 3)
- Introduce a **scenario state machine DSL** (YAML/JSON) describing states, transitions, probabilities, delays, and terminology references.
- Extend `LifecycleOrchestrator` to execute modules: read configuration, mutate patient record, schedule encounters/labs/medications.
- Support guard conditions that inspect demographics, comorbidities, SDOH values, and previous module outcomes.

### 4.2 Terminology & Data Integration
- Leverage Phase 2 terminology warehouse for all code references (ICD-10, SNOMED, CPT, LOINC, RxNorm, VSAC, UMLS).
- Build validation tooling to ensure each module references codes present in `terminology.duckdb`.
- Store module provenance (guideline citations, literature references) alongside configuration to support audits.

### 4.3 Tooling & Authoring
- Provide an authoring template with sections for demographics, SDOH, clinical pathway, probabilities, and outcomes.
- Implement a module linter checking for unreachable states, probability totals, missing terminologies.
- Offer visualization (possibly with Mermaid) to mirror Synthea’s builder for internal stakeholders.

### 4.4 Validation Strategy
- Unit tests: deterministic seeds verifying expected state transitions.
- Monte Carlo analytics comparing generated outcome rates against published benchmarks (e.g., chemo toxicity prevalence, appendectomy complication rates).
- SME review: integrate `.claude/agents/clinical-informatics-sme.md` during module design to catch unsafe or unrealistic patterns.

## 5. Proposed Timeline
1. **Phase 3 Kickoff**: define module schema, interpreter prototype, and author one pilot module (Cardiometabolic Intensive Management).
2. **Phase 3 Midpoint**: migrate additional recipes from `docs/scenario_recipes.md`; add regression tests and exporter hooks for module-specific metadata (e.g., chemo cycle numbers).
3. **Phase 4**: finalize documentation, build module catalogue, and release authoring guidance.

## 6. Open Questions
- Should we ingest Synthea JSON modules directly (translation layer) or maintain a tailored YAML format optimized for our lifecycle engine?
- How granular should adverse event modeling be (e.g., CTCAE grading vs simple severity flags)?
- What level of SME sign-off is required before modules become “canonical” in the repo?
- Do we need feedback loops between modules (e.g., asthma control affecting cardiometabolic pathways)?

## 7. Action Items
- [ ] Draft module schema and circulate with clinical SME for feedback.
- [ ] Prototype module interpreter within lifecycle engine.
- [ ] Implement initial high-value module (e.g., oncology chemo) and validate outputs.
- [ ] Document authoring/linting process and integrate into developer onboarding.

