# Phase 3B – Synthea‑Level Clinical Realism

Goal: Evolve our module engine, authoring DSL, and validation to match the fidelity of Synthea modules (e.g., asthma), including evidence‑based branching, attribute‑driven paths, reusable submodules, and provenance‑backed parameters.

## Success Criteria
- Engine executes an expanded DSL (attributes, conditional transitions, submodules, symptom and end states, unitized delays) with parity to key Synthea patterns.
- At least two exemplar modules (asthma, COPD) reproduce published incidence/trajectory metrics within agreed tolerances in Monte Carlo tests.
- Every nontrivial probability/delay cites a source; a linter enforces provenance and structural rules.

## Scope (What We’ll Build)
- DSL + Engine
  - Attributes: `set_attribute`, `conditional_transition` (Age/Demographic/Attribute checks, And/Or composition).
  - Decisions: `distributed_transition` (probabilities), `conditional_transition` (guards).
  - Delays with units and ranges: `delay.exact` or `delay.range` (hours/days/weeks/months/years).
  - Submodules: `call_submodule` with namespaced module paths (for med regimens, common procedures).
  - Symptom modeling: `symptom` state with name, range/frequency/severity.
  - Clinical end states: `condition_end`, `medication_end`, `care_plan_start`, `care_plan_end`, `encounter_end`.
  - Target linking: `target_encounter` (attach state outputs to a specific encounter), plus `assign_to_attribute` to reference created IDs.
  - Codes: `codes[]` with `{system, code, display}`; support SNOMED, LOINC, ICD‑10, CPT, RxNorm; value set references.
  - Metadata: `remarks[]` and `sources[]` (citations) at module and state levels; `version` & `gmf_version`.
- Provenance & Parameters
  - Curated sources per domain (examples): AAAAI, CDC NCHS FastStats, GINA/EPR‑3, USPSTF, NIH, ASCO/NCCN, GOLD, KDIGO.
  - Parameter registry (`data/parameters/*.yaml`) holding named rates/distributions with source IDs.
  - Import helpers to convert literature stats into normalized parameter files.
- Tooling & Validation
  - JSON Schema for DSL; schema‑aware linter: unreachable states, probability sums, unit validity, unknown attributes/codes, missing `sources` for nontrivial transitions.
  - Monte Carlo validator: module‑specific KPIs vs. target benchmarks with tolerances (per‑module spec).
  - Exporter parity checks (FHIR/HL7/CSV) to ensure state outputs are consistently realized.

## DSL Design (v2)
- Top‑level: `name`, `description`, `version`, `gmf_version: 2`, `categories`, `sources[]`, `remarks[]`, `states{}`.
- State types (superset): `start`, `delay`, `encounter`, `condition_onset`, `condition_end`, `medication_start`, `medication_end`, `observation`, `symptom`, `procedure`, `immunization`, `care_plan_start`, `care_plan_end`, `decision`, `set_attribute`, `encounter_end`, `terminal`, `call_submodule`.
- Transitions
  - `direct_transition: <state>`
  - `distributed_transition: [{distribution, transition}]`
  - `conditional_transition: [{condition, transition}]` with composable predicates:
    - `Attribute` (exists/equals), `Age` (operator, quantity, unit), `Demographic` (gender/race), `HasCondition`, `Random<p>`.
- Delay
  - `exact: {quantity, unit}` or `range: {low, high, unit}` with supported units.
- Example (Asthma excerpt)
  - `delay` until atopy processed; `conditional_transition` on `atopic`; `distributed_transition` for incidence; `target_encounter` for diagnosis; `care_plan_start` activities branching on smoker attribute.

## Engine Enhancements
- Parser upgrades to support v2 schema; maintain backward compatibility with v1 (current modules).
- Execution context retains attributes; expose patient demographics/SDOH for predicates.
- Submodule loader with namespacing and cycle detection; pass parent context to child.
- Time engine: unit conversions, date arithmetic precision (hours→years), guard for runaway loops.
- Output bindings: consistent assignment of IDs to attributes for later reference.

## Provenance & Data Sourcing
- Parameter store: `data/parameters/<domain>.yaml` containing named metrics (e.g., `asthma.attack_rate_semiannual = 0.265`, sources: AAAAI link IDs).
- Module authoring uses parameter references: `use: asthma.attack_rate_semiannual`.
- Source catalog: `docs/sources.yml` with `id`, `title`, `org`, `url`, `date_accessed`.
- Linter requires `sources[]` on states with `distributed_transition`/`conditional_transition` or nontrivial `delay`.

## Validation & Analytics
- Monte Carlo KPIs per module (examples)
  - Asthma: annual attack rate (~53%), ED visit rate per 100 asthma patients/year, childhood vs adult onset proportions.
  - COPD: exacerbations/year, steroid/antibiotic rescue proportion.
  - Sepsis: 30‑day readmission proxy via ED branch rate; lactate distribution.
- Tolerances: per KPI allow ±(5–10)% absolute deviation or CI bounds based on N.
- Reporter writes per‑module CSV/Parquet + HTML summary; CI fails when out of tolerance.

## Authoring Workflow & Docs
- Update `docs/TECHNICAL_USER_GUIDE.md` and `primers/clinical_module_primer.md` with v2 DSL, attribute examples, and provenance rules.
- Provide cookbook modules: high‑fidelity asthma and COPD as templates with citations.
- Diagram generation: auto‑render Mermaid state diagrams from DSL.

## Linter (v2)
- Structural: unreachable/unknown targets; probability sums ≈1; cycles without delays flagged.
- Semantics: unknown attributes, missing `sources` on stochastic branches, unit validity, `codes[]` system sanity.
- Provenance: require at least one source per probabilistic/conditional state; warn on module‑level `sources` only.

## Migration & Compatibility Strategy
- Keep v1 modules running (current Phase 3). Engine auto‑detects `gmf_version`.
- Provide translator CLI (optional) to scaffold v2 modules from v1 patterns.
- Deprecate v1 authoring after 1–2 releases; maintain execution parity.

## Milestones & Deliverables
- M1 (Engine + Schema)
  - Implement attributes, conditional/distributed transitions, unitized delays; JSON Schema + v2 parser; minimal linter.
  - Deliver: v2 schema draft; engine PR; unit tests for new state types.
- M2 (Submodules + Symptoms)
  - Add `call_submodule`, `symptom`, and end states; ensure FHIR mapping parity; expand linter checks.
  - Deliver: COPD & sepsis updates using submodules where appropriate.
- M3 (Asthma Module – High‑Fidelity)
  - Author asthma v2 mirroring Synthea: atopy gate, onset distributions, smoker plan branch, attack/ED loop.
  - Deliver: Monte Carlo KPIs passing; Mermaid diagram.
- M4 (Provenance & Parameter Store)
  - Populate parameter YAMLs; migrate v2 modules to reference parameters; enforce `sources` via linter.
  - Deliver: `docs/sources.yml`; ingestion scripts & examples.
- M5 (Validation & CI)
  - Extend Monte Carlo runner with KPI specs per module; integrate into CI; add HTML summary artifact.
  - Deliver: CI workflow and badge; primer updates.

## Acceptance Criteria
- v2 engine passes all unit/integration tests; v1 modules unaffected.
- Asthma/COPD v2 match published rates within tolerance in Monte Carlo tests.
- Linter blocks missing provenance/structure; docs demonstrate authoring with citations.

## Risks & Mitigations
- Complexity growth → Keep DSL minimal; reuse Synthea concepts selectively; strong schema + examples.
- Performance → Batch evaluation in engine; cap transition steps; profile loops; CI perf budgets.
- Data licensing → Use public/open stats; store citations only, not proprietary data.

## Effort & Timeline (indicative)
- M1: 1–2 weeks; M2: 1–2 weeks; M3: 1–2 weeks; M4: 1 week; M5: 0.5–1 week. Staggered deliverables allow early value with asthma first.

