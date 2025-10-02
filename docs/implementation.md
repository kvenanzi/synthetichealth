# Implementation Plan Overview

This document captures the current state and near-term priorities for the simulator pivot. It consolidates the active roadmap items so future sessions can resume work quickly—treat this as the source of truth for continuing implementation.

## Current Status Snapshot
- **Lifecycle engine (Phase 1)**: completed; generator uses lifecycle modules, orchestrator, and scenario configs.
- **Terminology platform (Phase 2)**: LOINC, ICD-10, SNOMED, RxNorm, VSAC, and UMLS importers are automated; loaders prefer normalized CSVs or the DuckDB warehouse while lightweight seeds remain for CI.
- **Exports**: FHIR/HL7/VistA/CSV/Parquet remain in sync; FHIR now emits Observation resources with VSAC value set references and appends UMLS concept extensions (alongside NCBI links) when terminology metadata is available.

## Phase Roadmap

### Phase 0 – Migration Branch Finalization
- ✅ Run `python tools/prepare_migration_branch.py migration_snapshot` to stage migration modules.
- ✅ Create and push the long-lived `migration` branch containing the staged files and legacy docs.
- ✅ Remove migration flags/messages from `main` after downstream transition.

### Phase 1 – Lifecycle Engine Enhancements
- ✅ Refactor remaining generator helpers (`generate_*`) into lifecycle-focused components under `src/core/lifecycle/`.
- ✅ Expand unit coverage for lifecycle pipelines as helper functions migrate out of the legacy generator.
- ✅ Introduce scenario configuration loaders, CLI selection, and lifecycle orchestrator wiring.
- ✅ Add smoke/unit tests for scenario loading and lifecycle orchestration to guard regressions.

### Phase 2 – Terminology Platform
- ✅ Replace bespoke catalogs with normalized datasets under `data/terminology/`.
- ✅ Implement terminology loaders with filtering/caching support and connect them to scenario templates.
- ✅ Normalize official ICD-10, SNOMED CT, and RxNorm releases once source archives are available (importers now covered by unit tests for canonical samples).
- ✅ Populate terminology datasets with comprehensive NLM/NCBI extracts (automated via `tools/refresh_terminology.py`).
- ✅ Enrich terminology integration (e.g., map RxNorm CUIs to clinical scenarios, extend exporters) now that normalized tables exist for all vocabularies.
- ✅ Design a DuckDB terminology warehouse (schema, ingestion jobs) to ingest normalized ICD-10/LOINC/SNOMED/RxNorm tables; extend coverage to VSAC/UMLS and document usage in the pipeline.
  - ✅ `tools/build_terminology_db.py` stages VSAC value sets and UMLS concepts and documents the DuckDB rebuild cadence.
  - ✅ Author import utilities for VSAC/UMLS so normalized CSVs can be generated alongside the existing ICD-10/LOINC/SNOMED/RxNorm helpers.
- ✅ Expand FHIR/CSV exporters to consume the new terminology services (Condition, Medication, and Observation resources now emit VSAC/UMLS context).

### Phase 3 – Clinical Realism & Validation
- ✅ Introduce module-driven workflow engine (`ModuleEngine`) and initial cardiometabolic intensive management module.
- 🔄 Author additional modules using the documented schema (`docs/scenario_recipes.md`, `modules/*.yaml`), expanding beyond cardiometabolic cohorts.
  - ✅ Pediatric asthma & immunization pathway (`modules/pediatric_asthma_management.yaml`).
  - ✅ Prenatal care with gestational diabetes management (`modules/prenatal_care_management.yaml`).
  - ✅ Oncology survivorship (`modules/oncology_survivorship.yaml`).
  - ✅ CKD dialysis planning (`modules/ckd_dialysis_planning.yaml`).
  - ✅ COPD home oxygen therapy (`modules/copd_home_oxygen.yaml`).
  - ✅ Mental health integrated care (`modules/mental_health_integrated_care.yaml`).
  - ✅ Geriatric polypharmacy & fall mitigation (`modules/geriatric_polypharmacy.yaml`).
  - ✅ Sepsis survivorship recovery (`modules/sepsis_survivorship.yaml`).
  - ✅ HIV + PrEP management (`modules/hiv_prep_management.yaml`).
- 🔄 Rebuild validation to cover schema, terminology, and temporal consistency; ensure new tests run in CI.
  - ✅ Structural validator (`validate_module_definition`) now blocks invalid transitions.
  - ✅ CLI linter (`tools/module_linter.py`) enforces code bindings across modules.
  - ✅ Monte Carlo regression script (`tools/module_monte_carlo_check.py`) and composite harness (`tools/run_phase3_validation.py`) capture variance and required-code checks for representative module cohorts.
- 🔄 Add performance/snapshot tests to protect export stability and generator throughput.
  - ✅ Baseline multi-module run recorded (200 patients, oncology + CKD + mental health) ~17s into `output/perf_baseline/`.

### Phase 4 – Docs, Tooling, and Release Prep
- Rewrite README and docs to focus on the simulator; link to the migration branch for legacy usage.
- Replace migration dashboards with clinical/SDOH analytics summaries and update utility scripts.
- Update CI pipelines, dependency manifests, and release notes to reflect the new architecture.

### Supporting Tasks
- Audit remaining modules for hard-coded migration references and remove or gate them.
- Capture design decisions in this implementation journal for transparency across phases.
- Plan beta milestones or internal releases once each phase reaches testing parity.

## Phase 3B – Synthea‑Level Realism (Plan)
See `docs/phase_3b_synthea_parity_plan.md` for the full end‑to‑end plan to extend the DSL, engine, provenance, and validation to match Synthea’s module detail (attributes, conditional transitions, submodules, symptom modeling, and evidence‑backed parameters).

## Allergy & Hypersensitivity Realism (Plan)
Objective: expand allergens and reactions beyond the current seeds and drive clinically appropriate tests, procedures, and medications with authoritative codes (SNOMED CT, RxNorm, LOINC, CPT) so outputs reflect realistic clinical workflows.

Data Sources
- VSAC value sets (via `data/terminology/vsac/…` and DuckDB table `vsac_value_sets`): harvest curated sets for drug allergies, food allergies, and environmental allergens.
- RxNorm (normalized `rxnorm_full.csv` / DuckDB): map allergen substances to RxNorm CUIs and optional NDC exemplars.
- SNOMED CT (normalized `snomed_full.csv` / DuckDB): surface allergen substance concepts and reaction/clinical finding terms.
- UMLS (optional): crosswalk SNOMED ↔ RxNorm for gaps and enrich reaction terminology.

Model & Catalog Changes
- Replace the hard-coded `ALLERGENS` seed with a generator that samples from the normalized warehouse:
  - Build an `AllergenRegistry` at runtime using RxNorm ingredients and VSAC membership; persist a deterministic subset for reproducibility in tests.
  - Expand to at least 40–100 common allergens (drug, food, latex, insect venom, environmental) with RxNorm and UNII where available.
- Expand `ALLERGY_REACTIONS` using SNOMED CT reaction findings (e.g., rash, urticaria, angioedema, anaphylaxis, nausea, vomiting, wheeze, dyspnea):
  - Keep display strings but store SNOMED codes alongside for FHIR Condition/AllergyIntolerance `reaction.manifestation` and VistA narratives.
- Severity: map to SNOMED severities (mild, moderate, severe) while preserving FileMan-compatible text in VistA node `3`.

Clinical Workflow Mapping (evidence-driven)
- When an allergy is recorded, attach appropriate orders/observations and care steps:
  - Drug allergy (e.g., penicillin): CPT skin testing (95018/95076/95079), oral challenge pathway, LOINC specific IgE tests where appropriate; avoid future prescribing of related agents (therapeutic class rules via RxNorm relationships).
  - Food allergy (peanut, shellfish): LOINC specific IgE (e.g., 39517-9 Peanut IgE), oral food challenge (document as procedure), epinephrine autoinjector prescription for anaphylaxis history.
  - Latex allergy: perioperative alerts, latex-avoidance flag; no testing orders unless indicated.
  - Insect venom allergy: venom-specific IgE (LOINC), referral to desensitization (CPT immunotherapy codes) for severe reactions.
- Medications: add clinically appropriate prescriptions tied to severity and context (e.g., epinephrine 0.3 mg autoinjector for anaphylaxis, cetirizine/loratadine for urticaria, intranasal steroids for allergic rhinitis). Use RxNorm CUIs on outputs.

Exporter Consistency
- FHIR: emit AllergyIntolerance with `code` (substance), `reaction.manifestation` (SNOMED), `severity`, and `category`; propagate RxNorm/SNOMED codes.
- HL7 v2: include AL1 segments with code/coding system and severity where supported.
- VistA: continue writing `^GMR(120.8)` entries; ensure `^GMR(120.82)` allergen dictionary contains all selected substances; keep reactions in node `1` and severities in node `3`.

Implementation Steps
1. Add a warehouse-backed allergen/reaction loader:
   - Prefer VSAC sets for substance lists; fall back to RxNorm ingredient list filtered by allergen classes.
   - Pull a curated set of reaction terms from SNOMED CT; expose via loader API.
2. Replace `ALLERGENS` and `ALLERGY_REACTIONS` seeds with dynamic catalogs built at startup (configurable cap for cohort realism vs. performance).
3. Update `generate_allergies` to sample from the expanded catalogs and attach severity; add optional downstream orders (procedures, labs, meds) based on substance and severity.
4. Wire new catalogs to exporters:
   - FHIR: enrich AllergyIntolerance + associated resources (MedicationRequest, ServiceRequest/Procedure, Observation) with correct codes.
   - VistA: ensure `^PSDRUG`, `^LAB(60)`, and `^GMR(120.82)` contain pointer targets for every generated entry.
5. Validation:
   - Unit tests that verify minimum allergen count (>40), presence of coded reactions, and exporter integrity across CSV/FHIR/VistA/HL7.
   - Monte Carlo check: distribution of allergens, reactions, and severities across cohorts looks plausible.

Acceptance Criteria
- >40 distinct allergens available per run (configurable) with RxNorm/UNII (where available) and VSAC provenance.
- Reactions include at least rash, urticaria, angioedema, anaphylaxis, wheeze/dyspnea, nausea/vomiting, each mapped to SNOMED and exported.
- Appropriate downstream tests/procedures/meds are emitted for severe cases (e.g., epinephrine for anaphylaxis, IgE labs for food/drug allergies) with the correct LOINC/CPT/RxNorm codes.
- All exporters remain internally consistent (pointers in VistA, codings in FHIR/HL7, normalized CSV tables).

## Medication & Laboratory Realism (Plan)
Objective: expand drug variety, dosing patterns, therapeutic classes, and monitoring labs; increase lab panel breadth and result realism with condition‑driven ordering and LOINC coverage. Ensure end‑to‑end coding integrity (RxNorm/VA class/ATC for meds; LOINC/UCUM for labs) and precise VistA pointer mapping.

Data Sources
- RxNorm (normalized `rxnorm_full.csv` / DuckDB): ingredients, clinical drugs, brand mappings, VA class (if available) and relationships for class‑based rules (e.g., ACEi/ARB, statins, SABA/ICS/LABA).
- VSAC medication/value sets: condition‑specific inclusion lists to bias evidence‑based picks (e.g., diabetes oral agents, anticoagulants, asthma controllers).
- LOINC (normalized `loinc_full.csv` / DuckDB): test definitions, preferred units (UCUM), and common panels beyond the current catalog.
- SNOMED CT: indication codes and problem→lab associations for ordering rules.

Model & Generator Changes
- Medications
  - Replace the static `MEDICATIONS` seed with a dynamic catalog hydrated from RxNorm; track ingredient → class mapping and typical dose forms/strengths.
  - Enforce condition‑driven therapeutic choices with contraindications (extend current rules) and simple drug–drug interaction checks for high‑risk combos.
  - Emit realistic start/stop patterns (e.g., acute antibiotics 5–10 days; statins chronic; taper patterns for steroids where appropriate).
  - Tie follow‑up labs to meds (e.g., statins→LFT/lipids, ACEi→BMP/potassium, warfarin→INR) with timing windows.
- Labs
  - Expand COMPREHENSIVE_LAB_PANELS with additional panels (coagulation, iron studies, renal, hepatic viral serologies, cardiac enzymes HS, thyroid antibodies) using LOINC codes and UCUM units.
  - Calibrate value distributions: age/sex‑specific reference ranges; skewed distributions for disease cohorts (e.g., A1c in diabetes); correlated results (e.g., anemia trios: Hgb/Hct/MCV).
  - Increase order logic coverage: map conditions and meds to standing labs and episodic orders; attach to nearest visit and set FileMan timestamps.

Exporter Consistency
- VistA: ensure every emitted med has a `^PSDRUG` pointer and every lab has a `^LAB(60)` pointer; keep visit and patient cross‑refs (`"V"`, `"B"`, `"AE"`) and zero nodes internal only.
- FHIR: prefer `MedicationRequest` + contained `Medication` with RxNorm code, `Observation` with LOINC and UCUM, and `ServiceRequest/Procedure` for non‑lab orders (e.g., oral challenge, skin test).
- HL7 v2: continue ADT/ORU; consider ORM for orders when enabled.

Implementation Steps
1. Add `medications_loader` that builds a therapeutic catalog from RxNorm with class tags; add configuration to cap breadth (e.g., top N per class) for performance.
2. Replace static medication picks with catalog sampling constrained by condition class rules and contraindications; emit dose form metadata and durations where feasible.
3. Extend lab panel registry with additional LOINC tests; add age/sex‑aware reference ranges and disease‑biased distributions; wire order logic from condition/meds.
4. Update VistA registries if needed (e.g., support dose text nodes later) and verify pointer integrity for all new entries.
5. Tests: unit tests for (a) med variety per 100 pts, (b) class coverage by condition, (c) lab breadth and LOINC/unit integrity, (d) VistA pointer/xref correctness; Monte Carlo checks for plausible distributions.

Acceptance Criteria
- Medication variety: ≥25 distinct ingredients across cohorts, with class‑appropriate selection and no contraindicated picks in rule scenarios.
- Lab breadth: ≥50 distinct LOINC tests across panels with correct UCUM units and age/sex‑appropriate reference ranges.
- Orders reflect clinical logic: meds trigger monitoring labs; conditions map to guideline panels; timing windows look plausible.
- Exporters remain consistent (FileMan pointers, FHIR/HL7 coding), and regression tests pass.

## Conditions Realism (Plan)
Objective: expand condition variety and fidelity beyond the current curated set; drive prevalence by age/sex/SDOH, add severity/staging where relevant, and ensure consistent coding (ICD‑10 + SNOMED) across exporters.

Data Sources
- ICD‑10 (normalized `icd10_full.csv` / DuckDB) for diagnosis coding and chapter‑level sampling.
- SNOMED CT (normalized `snomed_full.csv` / DuckDB) for problem list concepts, staging/severity findings.
- VSAC value sets (DuckDB) to bias selection toward clinically relevant cohorts (e.g., diabetes, COPD, ischemic heart disease).

Model & Generator Changes
- Build a dynamic condition catalog: sample top conditions per age/sex from ICD‑10 chapters and map to SNOMED preferred terms.
- Add severity/staging flags for select conditions (e.g., heart failure NYHA class, asthma severity, cancer staging placeholders) using SNOMED findings.
- Refine prevalence engine: incorporate SDOH, comorbidity lift, and genetics; ensure probability caps and mutually exclusive conditions where needed.

Exporter Consistency
- FHIR Condition: include `code` (ICD‑10 + SNOMED where available), `clinicalStatus`, `verificationStatus`, `stage` or `abatementDate` when applicable.
- VistA: continue to emit `^AUPNPROB` with internal pointers and synced `"ICD"` and `"S"` xrefs.
- HL7 v2: expose problems in ORU/OBX context when included, or in summary segments where applicable.

Implementation Steps
- ✅ Add condition loader using DuckDB (ICD‑10 + SNOMED + optional VSAC filters).
- ✅ Replace/augment `CONDITION_CATALOG` with loader output under configurable breadth per cohort.
- ✅ Add optional severity/staging attributes per condition; wire to exporters.
- ✅ Tests: ensure breadth (≥40 distinct conditions across 1k pts), coding integrity, and stable exporter behavior.

Acceptance Criteria
- ≥40 distinct conditions across cohorts; age/sex/SDOH distributions look plausible.
- Severity/staging captured for supported conditions and exported.
- Exporters remain consistent (CSV/FHIR/VistA/HL7).

## Encounters Realism (Plan)
Objective: generate realistic visit types/frequencies, tie visits to active conditions and care steps, and map to clinic stops/locations consistently.

Data Sources
- Existing clinic stop mapping (`^DIC(40.7)`) and internal encounter types.
- VSAC/SNOMED for reason codes and care pathways influencing visit cadence.

Model & Generator Changes
- Frequency model: derive visit counts from condition burden, care plans, and medication monitoring windows; add bursts for acute events (ED/urgent care).
- Type mix: calibrate primary care vs specialty vs ED vs inpatient; set service category (A/E/I) appropriately.
- Scheduling: attach labs/procedures/med follow‑ups to nearest appropriate visit.

Exporter Consistency
- VistA: maintain `^AUPNVSIT` with FileMan datetimes, clinic stop pointers, and `.06` location; keep `"B"/"D"/"GUID"` xrefs.
- FHIR/HL7: maintain Encounter resources/ADT coverage; ensure reason codes present when available.

Implementation Steps
- ✅ Add encounter cadence rules driven by conditions/care plans.
- ✅ Expand mapping from internal encounter types to clinic stops.
- ✅ Tests: per‑patient visit distribution by condition burden; stop code validity; exporter pointer integrity.

Acceptance Criteria
- Visit counts correlate with condition severity and care plans.
- Stop codes and locations valid; datetimes properly formatted.

## Immunizations Realism (Plan)
Objective: add age‑appropriate immunization schedules, codes, and titers; support catch‑up and contraindications, and export to VistA where applicable.

Data Sources
- VSAC immunization value sets (CVX codes within VSAC extracts when available) and RxNorm vaccine products.
- LOINC for serology/titer tests (e.g., Hep B surface antibody), SNOMED immunization procedures.

Model & Generator Changes
- Add schedule logic (child/adult/older adult) with ACIP‑like timing heuristics; generate catch‑up doses.
- Contraindications: integrate from allergy registry (e.g., egg allergy for certain flu vaccines) and pregnancy flags when relevant.
- Add optional serology labs pre/post vaccination with LOINC + UCUM units.

Exporter Consistency
- CSV/FHIR: emit Immunization resources with CVX (via VSAC) and/or RxNorm; add Observation records for titers.
- VistA: emit `^AUPNVIMM` (V Immunization #9000010.11) entries with pointers to vaccine dictionary stubs.

Implementation Steps
- ✅ Hydrate immunization catalog from VSAC/RxNorm; define schedule templates.
- ✅ Generate doses by age and scenario; attach contraindications and titer observations.
- ✅ Tests: verify coverage across age bands; code integrity; (optional) VistA `^AUPNVIMM` pilot.

Acceptance Criteria
- Age‑appropriate series for common vaccines; valid CVX/RxNorm codings; titer LOINC where applicable.
- (If enabled) valid `^AUPNVIMM` entries with internal pointers.

## Care Plans Realism (Plan)
Objective: deepen specialty pathways with timed milestones, metrics, and team roles; reflect guideline‑based care steps and monitoring.

Data Sources
- VSAC quality/measure value sets for metric targets.
- SNOMED procedures and LOINC monitoring tests aligned to conditions.

Model & Generator Changes
- Enrich `SPECIALTY_CARE_PATHWAYS` with milestones per condition (dates, metrics, responsible role), e.g., cardiac rehab, oncology staging/restaging, COPD exacerbation prevention.
- Add automated order generation tied to milestones (procedures, labs, meds).

Exporter Consistency
- FHIR: emit CarePlan with activities linked to ServiceRequest/Procedure/Observation; track status updates.
- CSV: persist schedule and status; VistA export may remain out of scope unless a specific file is chosen.

Implementation Steps
- ✅ Expand pathway templates; add scheduling engine to project dates relative to encounters.
- ✅ Wire activities to order/obs generation; update summaries.
- ✅ Tests: presence of milestones per condition; activity linkage; schedule plausibility.

Acceptance Criteria
- Condition cohorts show structured, timed care activities with appropriate orders and metrics.

## Family History Realism (Plan)
Objective: generate realistic family history entries with relation, age at onset, and mapped codes; propagate risk to the patient’s condition probabilities.

Data Sources
- SNOMED family history concepts; UMLS cross‑refs.

Model & Generator Changes
- Build a family history catalog by condition; sample relations (mother/father/sibling), age at onset, and outcome.
- Feed risk increments into the condition assignment stage.

Exporter Consistency
- CSV/FHIR: output FamilyMemberHistory with SNOMED codes.
- VistA: out of scope unless a target file is identified; keep CSV/FHIR authoritative.

Implementation Steps
1. Add family history loader and generator; tie to patient risk adjustments.
2. Tests: include codes, relations, and plausible ages at onset; verify risk propagation.

Acceptance Criteria
- Family history present for a realistic share of patients; codes/relations accurate; risk effects observable in condition prevalence.

## Mortality/Deaths Realism (Plan)
Objective: assign underlying cause of death with ICD‑10 coding consistent with the patient’s conditions and age; output realistic time of death.

Data Sources
- ICD‑10 for cause‑of‑death coding; internal mortality risk model driven by age, conditions, and severity.

Model & Generator Changes
- Choose underlying cause from the patient’s condition set (or age‑appropriate leading causes) and assign a death date/time; flag immediate/contributing causes optionally.

Exporter Consistency
- CSV/FHIR: populate death records and Patient.deceased.[x].
- VistA: ensure demographics death fields are populated (`^DPT` death date if modeled), optional additional globals out of scope.

Implementation Steps
1. Extend death generator to map causes to ICD‑10 and pick realistic timing.
2. Tests: cause coherence with conditions; age distribution checks.

Acceptance Criteria
- Underlying cause aligns with condition burden; coding/exporters consistent.

## VistA Export – RXs, Labs, Allergies (Plan)
Objective: extend the VistA MUMPS exporter to include FileMan‑correct medication, laboratory, and allergy data alongside patients (^DPT), visits (^AUPNVSIT), and problems (^AUPNPROB).

Scope & Deliverables
- Medications: emit PCC V Medication file nodes `^AUPNVMED` (#9000010.14) with internal pointers and xrefs; create minimal `^PSDRUG` (#50) entries as pointer targets.
- Labs: emit PCC V Laboratory file nodes `^AUPNVLAB` (#9000010.09); create minimal test definitions under `^LAB(60)` (#60) as pointer targets.
- Allergies: emit Patient Allergies entries `^GMR(120.8)` (#120.8); create minimal allergen entries under `^GMR(120.82)` (#120.82) as pointer targets.
- Pointer registries: extend the existing registry to manage IEN lookup/creation for `^PSDRUG`, `^LAB(60)`, and `^GMR(120.82)` (with file headers).
- Cross‑refs and headers: add standard “B”/visit xrefs where applicable and file headers with last IEN/date for all new files.

Data Mapping (internal values only)
- Source → VistA pointers
  - MedicationOrder: map `rxnorm_code` to `^PSDRUG` IEN (fall back on display name when missing). Tie to visit IEN when an `encounter_id` is present.
  - Observation (labs): map LOINC code to `^LAB(60)` IEN. Carry result/value, unit, and effective date/time. Tie to visit when `encounter_id` present; otherwise choose nearest visit by date.
  - Allergies: map allergen substance (prefer RxNorm/UNII where present) to `^GMR(120.82)` IEN. Store patient‑level allergy with reaction/severity as available.

Minimal File Nodes (proposed)
- `^AUPNVMED(IEN,0)` = DFN^DRUG_IEN^VISIT_IEN^FM_DATE^... (use File #9000010.14 field order; all pointers and dates in internal format). Add:
  - `^AUPNVMED("B",DFN,IEN)=""`, `^AUPNVMED("V",VISIT_IEN,IEN)=""`
  - Header: `^AUPNVMED(0)="V MEDICATION^9000010.14^<lastIEN>^<FMdate>"`
- `^AUPNVLAB(IEN,0)` = DFN^TEST_IEN(^LAB(60))^VISIT_IEN^RESULT^UNITS^REF_RANGE^FM_DATETIME^... Add:
  - `^AUPNVLAB("B",DFN,IEN)=""`, `^AUPNVLAB("V",VISIT_IEN,IEN)=""`
  - Header: `^AUPNVLAB(0)="V LAB^9000010.09^<lastIEN>^<FMdate>"`
- `^GMR(120.8,IEN,0)` = DFN^ALLERGEN_IEN(^GMR(120.82))^... (observed/historical, verify flags optional). Add:
  - `^GMR(120.8,"B",DFN,IEN)=""`
  - Header: `^GMR(120.8,0)="PATIENT ALLERGIES^120.8^<lastIEN>^<FMdate>"`

Pointer Target Registries (new)
- Drugs (`^PSDRUG`, File #50): key on RxNorm and display; create minimal `^PSDRUG(IEN,0)=<NAME>^...` plus `^PSDRUG("B",NAME,IEN)` and header `^PSDRUG(0)="DRUG^50^..."`.
- Lab Tests (`^LAB(60)`, File #60): key on LOINC and test name; create `^LAB(60,IEN,0)=<NAME>^...`, `^LAB(60,"B",NAME,IEN)`, header `^LAB(60,0)="LAB TEST^60^..."`.
- Allergens (`^GMR(120.82)`, File #120.82): key on substance name/RxNorm/UNII; create `^GMR(120.82,IEN,0)=<NAME>^...`, `^GMR(120.82,"B",NAME,IEN)`, header `^GMR(120.82,0)="ALLERGEN^120.82^..."`.

Exporter Changes
- Extend `VistaFormatter.export_vista_globals(...)` to accept medications, observations, and allergies.
- Enhance `_export_fileman_internal` to:
  1) write medications after visits using `^AUPNVMED` and new drug registry,
  2) write labs using `^AUPNVLAB` and lab test registry,
  3) write allergies at patient scope using `^GMR(120.8)` and allergen registry,
  4) emit xrefs and file headers for each file.
- Preserve current conventions: FM dates, internal pointers only; quote free‑text; keep visit GUID xref under `^AUPNVSIT("GUID",IEN)`.

Validation & Tests
- Unit tests (extend `tests/test_vista_formatter.py`):
  - assert presence of `^AUPNVMED(0)`, `^AUPNVLAB(0)`, `^GMR(120.8,0)` headers.
  - verify `0` nodes contain only internal values (DFN/visit IENs, pointer IENs, FM dates), and strings are quoted.
  - verify xrefs: `("V" by visit)`, `("B" by DFN)` exist and match `0` nodes.
  - ensure pointer targets (`^PSDRUG`, `^LAB(60)`, `^GMR(120.82)`) are created with headers and “B” xrefs.
- Smoke test: generate a small cohort with at least one med, lab, and allergy; confirm node counts in the exporter summary and spot‑check a few lines in `vista_globals.mumps`.

Risks & Mitigations
- Site variance in DDs: use conservative, widely deployed PCC/VistA V‑file fields; keep to minimal required pieces and indexes.
- Lab complexity: we avoid deeper Lab Service globals (`^LR`) initially; stick to V LAB entries with `^LAB(60)` pointers.
- Drug master data: `^PSDRUG` is large in production; we generate minimal stubs for dereferencing/display and document this limitation.

Implementation Steps
1. Add registries for `^PSDRUG`, `^LAB(60)`, `^GMR(120.82)` mirroring the existing ICD/location/state registry patterns.
2. Wire medications, labs, and allergies into `VistaFormatter._export_fileman_internal` with node builders + xref writers.
3. Emit file headers and aggregate counts for all new files in the exporter summary.
4. Add unit tests for new files/xrefs and edge cases (missing codes → fallback display entries; missing visit linkage → patient‑only allergy; malformed phone/strings still quoted).
5. Update primers (`primers/vista_mumps_quickstart.md`) with examples for each new file and note internal vs. external values.
6. Update docs/README and main README about the expanded VistA coverage and any flags added.

Acceptance Criteria
- Export includes valid `^AUPNVMED`, `^AUPNVLAB`, and `^GMR(120.8)` entries with synchronized xrefs and headers.
- All pointer fields use internal IENs; all string fields are quoted; FM dates/times are used consistently.
- Minimal pointer target files are present (`^PSDRUG`, `^LAB(60)`, `^GMR(120.82)`) with headers and “B” indexes.
- Tests pass (`pytest`), and smoke output shows patients > 0, meds > 0, labs > 0, allergies > 0.

## Immediate Next Steps
1. **Allergy realism expansion** (scope above)
    - Implement warehouse-backed allergen/reaction loaders and swap in the expanded catalogs; add evidence-based orders for severe reactions.
    - Add tests ensuring minimum allergen count and exporter correctness (CSV/FHIR/VistA/HL7).
2. **Medication & laboratory realism expansion** (scope above)
   - Hydrate medication catalog from RxNorm; expand lab panels from LOINC; wire indication/monitoring rules.
   - Add tests to verify breadth, coding integrity, contraindication enforcement, and plausible distributions.
3. **Conditions & encounters realism expansion** (scopes above)
   - Replace static condition catalog with loader-based sampling and severity; add encounter cadence rules tied to care plans.
   - Tests for distribution plausibility and pointer/coding integrity.
4. **Immunizations realism expansion** (scope above)
   - Add CVX/RxNorm-backed schedules and (optional) VistA `^AUPNVIMM` pilot; include serology LOINC observations.
5. **Care plan realism expansion** (scope above)
   - Enrich pathways, activities, and metrics; wire to orders/obs.
6. **Family history & mortality realism** (scopes above)
   - Add realistic FamilyMemberHistory and ICD‑10 coded causes of death with timing.
7. **Extend module catalogue**
    - Implement remaining backlog scenarios (geriatrics, sepsis survivorship, HIV/PrEP) using the established authoring pattern.
    - Add scenario wiring plus regression tests mirroring `tests/test_module_engine.py` for every new module.
8. **Broaden validation coverage**
    - Build a module linter CLI (under `tools/`) that wraps `validate_module_definition` and checks terminology bindings.
    - Add Monte Carlo outcome assertions and exporter parity tests once multiple modules coexist.
9. **Baseline performance safeguards**
    - Capture generator runtime metrics with ≥3 modules enabled and persist results for regression comparison.

## Reminders
- Keep this document updated whenever milestones land; it is the authoritative checklist for the pivot.
- Raw vendor archives belong in `data/terminology/<system>/raw/`; normalized CSVs stay in the root of each system directory and should be ignored once exported to DuckDB.
- Run test suites with `pytest` before wrapping up to keep the signal clean.

When returning to the project, review this file and the checkpoint document above to decide which task to pick up next.
