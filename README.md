# Synthetic Healthcare Data Generator

A comprehensive synthetic healthcare data generator designed for healthcare migration simulations, EHR system testing, and interoperability research. This system generates realistic, Synthea-like healthcare data with multi-format export capabilities.

## Features

- **Multi-Format Export**: Generate data in FHIR R4, HL7 v2.x, VistA MUMPS, CSV, and Parquet formats
- **Clinical Realism**: Realistic medical relationships, proper coding (ICD-10, CPT, LOINC, NDC, CVX), and epidemiological accuracy
- **Migration Simulation**: Advanced healthcare data migration testing with failure simulation and analytics
- **Performance Optimized**: Parallel processing with concurrent.futures for high-performance generation
- **Referential Integrity**: Maintains data consistency across all export formats

## Quick Start

### Installation

```bash
git clone https://github.com/ospfer/synthetichealth.git
cd synthetichealth
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate synthetic healthcare data (all formats)
python3 -m src.core.synthetic_patient_generator --num-records 100

# Run migration simulation demo
python3 demos/migration_demo.py

# Run performance analysis
python3 demos/final_performance_demo.py
```

## Project Structure

```
synthetichealth/
├── src/
│   ├── core/                          # Core data generation modules
│   │   ├── synthetic_patient_generator.py  # Main data generator
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
├── tests/                            # Test suites
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
- `conditions`: ICD-10 coded diagnoses with clinical status
- `medications`: NDC coded prescriptions linked to conditions
- `allergies`: SNOMED coded substance allergies
- `procedures`: CPT coded medical procedures
- `immunizations`: CVX coded vaccination records
- `observations`: LOINC coded vitals and lab results
- `deaths`: Mortality data with cause mapping
- `family_history`: Genetic predisposition modeling

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
# Basic performance test
python3 tests/simple_performance_test.py

# Migration simulation tests
python3 tests/test_migration_simulator.py

# Full test suite
python3 tests/run_performance_tests.py
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

### Completed Phases
- **Phase 1**: Core Extensions - Enhanced PatientRecord class with multi-format IDs
- **Phase 2**: HL7 v2 Support - Message creation and validation
- **Phase 3**: VistA MUMPS Format - Global structure and field mappings
- **Phase 4**: Migration Simulation - Staged migration with failure injection
- **Phase 5**: Integration & Testing - Unified architecture and performance optimization

### Current Capabilities
- Multi-format healthcare data generation
- Advanced migration simulation with analytics
- Performance testing and optimization
- Comprehensive validation and error handling

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