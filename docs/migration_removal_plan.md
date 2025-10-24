# Migration Functionality Removal Plan

This document outlines the comprehensive steps required to remove all migration-oriented functionality from the project while preserving and strengthening the synthetic patient generation capabilities.

## 1. Inventory and Analysis
- [ ] Catalog all modules, scripts, configuration files, and documentation that reference migration features (`migration_simulator`, `enhanced_migration_simulator`, trackers, dashboards, CLI tooling).
- [ ] Identify shared utilities between migration and patient generation paths to ensure they are retained or safely refactored.
- [ ] Document any external dependencies (e.g., additional libraries, CI jobs) introduced solely for migration analytics so they can be removed.

## 2. Core Codebase Changes
- [ ] Remove migration simulators and trackers (`src/core/migration_simulator.py`, `src/core/enhanced_migration_simulator.py`, related tracker modules) after confirming no patient-generation logic depends on them.
- [ ] Excise migration-specific dataclasses, configuration schemas, and helper utilities that are not needed by the patient generator.
- [ ] Update the synthetic patient generator entry point (`src/core/synthetic_patient_generator.py`) to eliminate optional migration execution paths, inputs, and metadata fields.
- [ ] Refactor any shared components to provide clear patient-generation responsibilities (e.g., move reusable analytics or logging helpers into patient-centric modules).

## 3. Configuration and Defaults
- [ ] Strip migration-related settings from configuration files (`config/config.yaml`, `config/phase5_enhanced_config.yaml`, etc.) and ensure defaults exclusively support patient generation.
- [ ] Remove toggles such as `simulate_migration`, `migration_strategy`, and report file options from command-line interfaces and environment configuration.
- [ ] Verify tooling and scripts no longer expect migration configuration keys.

## 4. Tooling and Scripts
- [ ] Delete or rewrite scripts in `tools/` that prepare migration dashboards, generate migration reports, or manage migration-only branches.
- [ ] Update any remaining utilities to operate purely on patient-generation outputs (e.g., adjust dashboard summary tools to focus on clinical quality, SDOH, and export validation without referencing migration quality metrics).
- [ ] Remove the `migration_snapshot/` artifacts if they only exist to support the deprecated capability.

## 5. Documentation and Educational Materials
- [ ] Update README, implementation guides, primers, and realism reports to remove migration positioning and focus on synthetic patient generation.
- [ ] Excise migration walkthroughs from demos (`demos/enhanced_migration_demo.py`, notebooks, or other tutorials) or repurpose them as patient-generation showcases.
- [ ] Ensure release notes and roadmap documents no longer reference migration milestones.

## 6. Tests and Validation
- [ ] Remove migration-specific unit/integration tests (e.g., `tests/test_enhanced_migration_simulator.py`) and adjust the test suite to validate patient generator correctness only.
- [ ] Confirm CI workflows no longer invoke migration demos or expect migration outputs.
- [ ] Add or expand tests that cover any refactored patient-generation APIs introduced during the cleanup.

## 7. Dependency and Build Hygiene
- [ ] Prune dependencies added solely for migration dashboards or analytics (e.g., CLI formatting libraries, visualization packages) unless still used for patient-generation reporting.
- [ ] Update packaging metadata (`requirements.txt`, `package.json`, etc.) and lockfiles.
- [ ] Validate that build and deployment scripts run without migration artifacts.

## 8. Final Verification and Communication
- [ ] Run the full patient-generation pipeline end-to-end to ensure no residual migration references remain and outputs are stable.
- [ ] Audit log messages, error strings, and metadata fields to remove migration terminology.
- [ ] Publish updated release notes summarizing the removal and clarifying the project's new single-purpose scope.

---

Use this checklist to drive implementation tasks. Track progress in the issue tracker and create follow-up tickets for any newly discovered coupling between migration and patient-generation components.
