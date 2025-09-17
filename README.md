# Synthetic Healthcare Data Generator

A lifecycle-focused synthetic healthcare simulator that produces richly coded patient records for interoperability prototyping, analytics experimentation, and migration rehearsals. Phase 2 introduces normalized terminology datasets sourced from the U.S. National Library of Medicine (NLM) / NCBI so exports now carry authoritative ICD‑10, LOINC, SNOMED CT, and RxNorm references.

## Features

- **Scenario-driven lifecycle engine** – demographic distributions, SDOH configuration, and orchestrated care pathways now live under `src/core/lifecycle/`.
- **Terminology platform (Phase 2)** – normalized vocabularies in `data/terminology/` with direct NCBI/MeSH/PubChem links, loader utilities, and scenario-level code curation.
- **Multi-format exports** – FHIR R4 bundles (with NCBI reference extensions), HL7 v2 ADT/ORU messages, VistA MUMPS globals, CSV, and Parquet outputs.
- **Migration simulation toolkit** – staged ETVL pipeline, failure injection, analytics dashboards, and audit logging for migration rehearsals.
- **Parallel performance** – generation uses `concurrent.futures` to scale to tens of thousands of synthetic patients.
- **Referential integrity** – patient identifiers stay consistent across every export format.

## Quick Start

### Installation

```bash
git clone https://github.com/ospfer/synthetichealth.git
cd synthetichealth
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r data/requirements.txt  # minimal lifecycle dependencies
pip3 install -r requirements.txt       # full migration/analytics stack
```

### Basic Usage

```bash
# Generate synthetic healthcare data (all formats)
python3 -m src.core.synthetic_patient_generator --num-records 100 --output-dir output

# Run migration simulation demo
python3 demos/migration_demo.py

# Run performance analysis
python3 demos/final_performance_demo.py
```

## Project Structure

```
synthetichealth/
├── src/
│   ├── core/
│   │   ├── lifecycle/                 # Lifecycle engine, scenarios, orchestrator
│   │   ├── terminology/               # Terminology loaders & helpers (Phase 2)
│   │   ├── synthetic_patient_generator.py  # Main lifecycle-aware generator
│   │   ├── enhanced_migration_simulator.py # Migration simulation engine
│   │   └── enhanced_migration_tracker.py   # Migration analytics
│   ├── generators/                    # Specialized data generators
│   ├── validation/                    # Data validation modules
│   ├── analytics/                     # Migration analytics tools
│   └── integration/                   # System integration components
├── demos/                             # Demonstration scripts
│   ├── migration_demo.py             # Basic migration demonstration
│   ├── enhanced_migration_demo.py    # Advanced migration simulation
│   ├── migration_analytics_demo.py   # Analytics and reporting demo
│   └── final_performance_demo.py     # Performance testing suite
├── tests/                            # Pytest suites (lifecycle, migration, terminology)
├── data/
│   └── terminology/                  # ICD-10, LOINC, SNOMED, RxNorm CSV seeds
├── config/                           # Configuration files
│   ├── config.yaml                   # Basic configuration
│   └── phase5_enhanced_config.yaml   # Advanced migration settings
└── docs/                             # Documentation
```

## Generated Data Formats

### Healthcare Interoperability Standards
- **FHIR R4**: US Core compliant Patient and Condition resources
- **HL7 v2.x**: ADT (Admit/Discharge/Transfer) and ORU (Observation Result) messages
- **VistA MUMPS**: Production-accurate VA FileMan global structures

### Analytics Formats
- **CSV/Parquet**: Normalized relational tables for research and analytics

### Data Tables
All formats maintain referential integrity via patient_id linkage:
- `patients`: Demographics, SDOH factors, multiple identifiers
- `encounters`: Healthcare visits with realistic patterns
- `conditions`: ICD-10/SNOMED coded diagnoses with clinical status
- `medications`: RxNorm/NDC coded prescriptions linked to indications
- `allergies`: SNOMED coded substance allergies
- `procedures`: CPT coded medical procedures
- `immunizations`: CVX coded vaccination records
- `observations`: LOINC coded vitals and lab results
- `deaths`: Mortality data with cause mapping
- `family_history`: Genetic predisposition modeling

## Terminology Platform (Phase 2)

- Seed vocabularies live under `data/terminology/` with direct NCBI/MeSH/PubChem references for each ICD-10, LOINC, SNOMED CT, and RxNorm concept.
- Loader utilities in `src/core/terminology/` expose simple filtering/search helpers and respect the `TERMINOLOGY_ROOT` environment variable for pointing at larger institutional vocabularies.
- Scenario definitions declare curated code lists that `load_scenario_config` resolves into fully hydrated terminology bundles for the generator and exporters.

## Migration Simulation

The system includes advanced migration simulation capabilities for healthcare data transformation projects:

### Features
- **Staged Migration**: Extract, Transform, Validate, Load (ETVL) pipeline simulation
- **Failure Injection**: Realistic failure scenarios with configurable rates
- **Data Quality Tracking**: Monitors degradation throughout migration process
- **Performance Analytics**: Detailed timing and throughput analysis
- **Error Classification**: Categorizes and tracks different failure types

### Migration Analytics
- Success/failure rates by stage and batch
- Data quality degradation analysis
- Performance metrics and bottleneck identification
- Automated recommendations for improvement

## Configuration

### Basic Configuration (config/config.yaml)
```yaml
demographics:
  age_distribution: [0.1, 0.15, 0.2, 0.25, 0.2, 0.1]
  
output:
  directory: "./output"
  formats: ["csv", "fhir", "hl7", "vista"]
  
generation:
  seed: 42
  parallel_workers: 4
```

### Advanced Migration Configuration (config/phase5_enhanced_config.yaml)
Includes migration simulation parameters, failure rates, and analytics settings.

## Development

### Running Tests
```bash
# Lifecycle and terminology coverage
pytest tests/test_patient_generation.py tests/test_clinical_generation.py tests/test_terminology_loaders.py

# Migration simulations
pytest tests/test_migration_simulator.py tests/test_enhanced_migration.py

# Full suite
pytest
```

### Demo Scripts
```bash
# Basic migration demonstration
python3 demos/migration_demo.py

# Enhanced migration with analytics
python3 demos/enhanced_migration_demo.py

# Performance benchmarking
python3 demos/final_performance_demo.py

# Migration analytics and reporting
python3 demos/migration_analytics_demo.py
```

## Technical Specifications

### Dependencies
- **polars**: High-performance DataFrame operations
- **faker**: Realistic demographic data generation
- **PyYAML**: Configuration file management
- **concurrent.futures**: Parallel processing support
- **pytest**: Primary automated test runner

### Performance
- Optimized for large-scale data generation (10k+ records)
- Parallel processing with configurable worker pools
- Memory-efficient data structures using Polars
- Streaming output for large datasets

### Standards Compliance
- **FHIR R4**: US Core compliance with proper terminology
- **HL7 v2.x**: Message validation and format compliance
- **VistA**: Production-accurate FileMan global structures
- **Medical Coding**: ICD-10, CPT, LOINC, NDC, CVX, SNOMED

## Implementation Status

### Roadmap Snapshot
- **Phase 0** – Migration branch split and repository realignment (complete)
- **Phase 1** – Lifecycle engine foundation, scenario orchestration, unit coverage (complete)
- **Phase 2** – Terminology platform with NCBI-linked vocabularies (in progress)
- **Phase 3** – Clinical realism & validation enhancements (up next)
- **Phase 4** – Documentation, tooling, and release readiness

### Current Capabilities
- Scenario-driven lifecycle generation with SDOH enrichment
- Normalized terminology loaders and NCBI-referenced exports
- Multi-format healthcare data generation (FHIR/HL7/VistA/CSV/Parquet)
- Migration simulation with analytics and performance benchmarking
- Pytest-based automation for lifecycle, terminology, and migration flows

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues, questions, or contributions, please use the GitHub issue tracker.
