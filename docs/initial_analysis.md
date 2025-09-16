# Initial Analysis: Refocusing the Synthetic Data Simulator

## Purpose
This document captures the first-pass analysis for pivoting the codebase toward a clinically rich synthetic data generator. It clarifies why change is needed, the scope of the redesign, and the major workstreams that will guide subsequent implementation phases.

## Background Snapshot
- Recent releases, demos, and analytics materials highlight migration validation scenarios rather than longitudinal patient synthesis.
- Core modules (`synthetic_patient_generator`, `multi_format_healthcare_generator`) mix migration telemetry with generation logic, limiting reuse for pure simulation work.
- Terminology catalogs include small, hand-curated code samples, which conflicts with the objective of modeling large-scale clinical vocabularies.
- Supporting scripts and dashboards report on migration quality, reinforcing a migration-first narrative across the repository.

## Strategic Goals
- Reposition `main` as the home for a standards-focused synthetic health record generator.
- Preserve the migration toolkit without blocking reference access for anyone who still relies on it today.
- Expand clinical fidelity by layering comprehensive terminologies, temporal care pathways, and configurable population scenarios.
- Establish validation, testing, and documentation foundations that reflect the renewed simulator mission.

## High-Level Gaps
### Product Framing
- Public documentation, README content, and demos emphasize VistA to Oracle Health migration readiness.
- CLI defaults, analytics summaries, and dashboards surface migration KPIs instead of synthetic cohort properties.

### Platform Architecture
- Patient lifecycle generation is tightly coupled to migration stage tracking and quality scoring metrics.
- Scenario modeling is limited to a handful of examples and lacks specialty-specific templates.

### Reference Data
- ICD-10, SNOMED, LOINC, RxNorm, and related catalogs are narrow in scope and stored as bespoke Python structures.
- No loader utilities exist for working with official code set distributions or for filtering by demographic, severity, or specialty dimensions.

### Quality & Tooling
- Validation modules focus on migration success rates rather than clinical consistency (schema validation, coding integrity, temporal plausibility).
- Tooling such as `generate_dashboard_summary.py` reports migration outcomes instead of synthetic data coverage metrics.

## Phased Implementation Roadmap
### Phase 0 – Repository Realignment
- **Deliverables**: `migration` branch created with frozen migration assets, updated `CONTRIBUTING.md` instructions, CI configuration that skips migration test suites.
- **Key Actions**: Snapshot the current migration artifacts, script a repo reorganization that moves migration-only modules and docs, publish a transition note that points legacy users to the branch.
- **Sequencing Notes**: Execute prior to any generator refactors to avoid merge churn; lock releases during the split; budget time to update any local automation that still depends on the migration path.
- **Ownership**: Solo effort with ad-hoc checklists to track the split and clean-up tasks.

### Phase 1 – Core Domain Redesign
- **Deliverables**: Modular lifecycle package in `src/core/lifecycle/`, baseline domain model definitions, scenario template registry, updated CLI entrypoints reflecting the new module boundaries.
- **Key Actions**: Decompose existing generator functions into intake/encounter/therapy modules; define dataclasses or Pydantic schemas aligned with FHIR; create scenario configuration format and loaders; refactor CLI flags to reference scenarios rather than migration knobs.
- **Sequencing Notes**: Prototype the domain model with unit tests before wiring into the CLI; keep the migration branch synced until the refactor stabilizes; plan for iterative rollout by enabling feature flags for new scenarios.
- **Ownership**: Self-managed iteration with frequent checkpoints captured in the implementation log to document design decisions.

### Phase 2 – Terminology & Standards Platform
- Replace bespoke catalogs with large curated datasets across ICD-10-CM, SNOMED CT, RxNorm, LOINC, CVX, CPT, and related sets under `data/terminology/`.
- Build loaders and sampling utilities that filter by specialty, demographic prevalence, or severity, and cache large code sets.
- Deliver a standards-aligned export layer (`src/standards/fhir`) that emits FHIR R4/R5 resources, legacy DSTU2/STU3 mappings, CSV, Parquet, and optional HL7 v2 messages.
- Implement coding helpers that map generated events to appropriate SNOMED, LOINC, RxNorm, and ICD-10 codes.

### Phase 3 – Clinical Realism & Validation
- Model workflows such as referrals, lab ordering/results, medication titration, and care plan adherence using probabilistic state machines or rule engines.
- Capture temporal realism (scheduling, follow-up intervals, turnaround times, condition progression) and social determinants of health drivers for adherence.
- Rebuild validation pipelines to enforce schema correctness, terminology consistency, and clinical plausibility; introduce data quality metrics relevant to synthetic cohorts.
- Expand automated tests with lifecycle, exporter, terminology sampling, performance, and snapshot coverage.

### Phase 4 – Experience, Documentation, and Release Readiness
- Refresh README, docs, demos, and tooling to describe the simulator-first focus while referencing the legacy migration branch.
- Replace migration dashboards with clinical/SDOH metrics summaries and update utility scripts accordingly.
- Update dependency management, linting, and CI workflows to align with the new architecture and release cadence.
- Publish versioned release notes explaining the functional split and the roadmap for continued simulator enhancements.

## Immediate Next Steps
- Validate the branch split plan locally and document the sequence of git operations required to carve out the migration history.
- Sketch the modular lifecycle engine components and capture open questions directly in the repository journal for quick iteration.
- Inventory publicly distributable terminology sources and note any licensing blockers before ingestion.
- Finalize the success metrics (coverage, quality, performance, adoption) that will drive ongoing implementation checkpoints.

## Risks & Mitigations
- **Scope Creep**: The migration-to-simulator pivot touches nearly every module. Mitigation: time-box discovery for each phase, and enforce change control via architecture reviews before expanding scope.
- **Terminology Licensing**: Some vocabularies have redistribution limits. Mitigation: validate licensing upfront, prefer publicly distributable subsets, and provide integration hooks for proprietary datasets that remain external.
- **Operational Disruption**: Existing migration automation may face downtime. Mitigation: publish the transition plan, support automation updates during Phase 0, and maintain read-only snapshots for audit needs.
- **Validation Gaps**: Replacing migration quality checks with clinical validation introduces risk of undetected data issues. Mitigation: define acceptance criteria up front and create regression fixtures with known outputs.

## Success Metrics
- **Coverage**: Number of supported clinical scenarios, breadth of terminology entries per code system, and percentage of events with standards-aligned codings.
- **Quality**: Validation pass rates across schema, terminology, and clinical consistency checks; defect rates reported by internal consumers post-transition.
- **Performance**: Generation throughput (records per minute) for target cohort sizes, with benchmarks recorded before and after refactors.
- **Adoption**: Usage metrics of new CLI scenarios and documentation engagement (e.g., page views, tutorial completions) indicating successful repositioning.

