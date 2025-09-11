# Synthetic Healthcare Data Generator - User Guide

## Overview

The Synthetic Healthcare Data Generator is a comprehensive tool for creating realistic synthetic patient data for healthcare migration simulations, EHR system testing, and interoperability research. It generates data in multiple formats including **FHIR R4**, **HL7 v2.x**, **VistA MUMPS**, **CSV**, and **Parquet** formats.

## Table of Contents

1. [Project Architecture](#project-architecture)
2. [Installation & Setup](#installation--setup)
3. [Quick Start](#quick-start)
4. [Command Line Interface](#command-line-interface)
5. [YAML Configuration](#yaml-configuration)
6. [Output Formats](#output-formats)
7. [Migration Simulation](#migration-simulation)
8. [Advanced Configuration](#advanced-configuration)
9. [Performance & Scalability](#performance--scalability)
10. [Examples](#examples)
11. [Troubleshooting](#troubleshooting)

---

## Project Architecture

The project follows a modular architecture organized into specialized directories:

### Core Modules (`src/`)
- **`src/core/`** - Core data generation and migration simulation engines
  - `synthetic_patient_generator.py` - Main modular data generator
  - `enhanced_migration_simulator.py` - Advanced migration simulation with failure injection
  - `enhanced_migration_tracker.py` - Migration analytics and performance tracking

- **`src/generators/`** - Specialized data generators for different healthcare domains
  - `multi_format_healthcare_generator.py` - Multi-format healthcare data generation
  - `healthcare_format_handlers.py` - Format-specific data handling

- **`src/validation/`** - Data validation and quality assurance modules
  - `comprehensive_validation_framework.py` - Complete validation system
  - `healthcare_interoperability_validator.py` - Healthcare-specific validation

- **`src/analytics/`** - Migration analytics and reporting tools
  - `migration_analytics_engine.py` - Analytics processing engine
  - `migration_report_generator.py` - Report generation utilities
  - `real_time_dashboard.py` - Real-time monitoring dashboard

- **`src/config/`** - Configuration management system
  - `healthcare_migration_config.py` - Healthcare migration configurations
  - `enhanced_configuration_manager.py` - Advanced configuration handling

- **`src/testing/`** - Testing frameworks and utilities
  - `performance_testing_framework.py` - Performance testing suite
  - `error_injection_testing_framework.py` - Error injection testing

- **`src/integration/`** - System integration and unified architecture
  - `phase5_unified_integration.py` - Unified integration framework

### Demo Scripts (`demos/`)
- `migration_demo.py` - Basic migration simulation
- `enhanced_migration_demo.py` - Advanced migration with analytics  
- `migration_analytics_demo.py` - Migration analytics and reporting
- `final_performance_demo.py` - Performance testing framework
- `integration_performance_demo.py` - Integration performance testing

### Test Suite (`tests/`)
- `simple_performance_test.py` - Basic performance validation
- `test_migration_simulator.py` - Migration simulation testing
- `run_performance_tests.py` - Comprehensive test suite
- `test_enhanced_migration.py` - Enhanced migration testing
- `test_migration_analytics.py` - Migration analytics testing

---

## Installation & Setup

### Prerequisites
- **Python 3.8+** with concurrent.futures support
- **Virtual environment** (recommended)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd synthetichealth
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r data/requirements.txt
   ```

### Core Dependencies
- `polars` - High-performance data processing
- `faker` - Realistic synthetic data generation
- `PyYAML` - Configuration file support
- `concurrent.futures` - Parallel processing

---

## Quick Start

### Basic Usage

Generate 1000 synthetic patient records:
```bash
python3 -m src.core.synthetic_patient_generator --num-records 1000
```

Generate with custom output directory:
```bash
python3 -m src.core.synthetic_patient_generator --num-records 500 --output-dir ./healthcare_data
```

### Using Configuration Files

Create a `config.yaml` file:
```yaml
num_records: 1000
output_dir: my_output
seed: 42
output_format: both  # csv, parquet, or both
```

Run with configuration:
```bash
python3 -m src.core.synthetic_patient_generator --config config.yaml
```

---

## Command Line Interface

### Core Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--num-records` | int | 1000 | Number of patient records to generate |
| `--output-dir` | str | "." | Directory to save output files |
| `--seed` | int | None | Random seed for reproducibility |
| `--config` | str | None | Path to YAML configuration file |
| `--report-file` | str | None | Save generation report to file |

### Output Format Options

| Argument | Description |
|----------|-------------|
| `--csv` | Output CSV files only |
| `--parquet` | Output Parquet files only |
| `--both` | Output both CSV and Parquet files (default) |

### Migration Simulation Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--simulate-migration` | flag | False | Enable migration simulation |
| `--batch-size` | int | 100 | Batch size for migration processing |
| `--migration-strategy` | str | "staged" | Migration strategy: staged, big_bang, parallel |
| `--migration-report` | str | None | Output migration report file |

### Examples

```bash
# Basic generation
python3 -m src.core.synthetic_patient_generator --num-records 500

# CSV output only with custom directory
python3 -m src.core.synthetic_patient_generator --num-records 1000 --csv --output-dir ./csv_data

# With migration simulation
python3 -m src.core.synthetic_patient_generator --num-records 500 --simulate-migration --batch-size 50

# Full configuration
python3 -m src.core.synthetic_patient_generator \
  --config config.yaml \
  --simulate-migration \
  --migration-report detailed_report.txt \
  --report-file generation_report.txt
```

---

## YAML Configuration

### Complete Configuration Example

```yaml
# Core Generation Settings
num_records: 1000
output_dir: healthcare_output
seed: 42
output_format: both  # Options: csv, parquet, both

# Demographic Distributions (must sum to 1.0)
age_dist:
  0-18: 0.1      # Pediatric
  19-40: 0.2     # Young adults
  41-65: 0.4     # Middle-aged
  66-120: 0.3    # Elderly

gender_dist:
  male: 0.5
  female: 0.5

race_dist:
  White: 0.6
  Black: 0.15
  Asian: 0.1
  Hispanic: 0.1
  Native American: 0.03
  Other: 0.02

# Social Determinants of Health (SDOH)
smoking_dist:
  Never: 0.6
  Former: 0.2
  Current: 0.2

alcohol_dist:
  Never: 0.4
  Occasional: 0.3
  Regular: 0.2
  Heavy: 0.1

education_dist:
  None: 0.05
  Primary: 0.1
  Secondary: 0.15
  High School: 0.3
  Associate: 0.1
  Bachelor: 0.2
  Master: 0.08
  Doctorate: 0.02

employment_dist:
  Employed: 0.6
  Unemployed: 0.1
  Student: 0.15
  Retired: 0.1
  Disabled: 0.05

housing_dist:
  Stable: 0.85
  Homeless: 0.05
  Temporary: 0.08
  Assisted Living: 0.02

# Migration Simulation Settings
migration_settings:
  source_system: "vista"           # Source EHR system
  target_system: "oracle_health"   # Target EHR system
  migration_strategy: "staged"     # Options: staged, big_bang, parallel
  
  # Success rates for each migration stage
  success_rates:
    extract: 0.98    # VistA data extraction
    transform: 0.95  # Data transformation
    validate: 0.92   # Data validation
    load: 0.90       # Oracle Health loading
  
  # Error injection rates (for realistic simulation)
  network_failure_rate: 0.05      # 5% network issues
  system_overload_rate: 0.03      # 3% system overload
  data_corruption_rate: 0.01      # 1% data corruption

# Migration flags (can be overridden by CLI)
simulate_migration: false
batch_size: 100
migration_strategy: "staged"
migration_report: "migration_analysis.txt"

# Report generation
report_file: "generation_summary.txt"
```

### Configuration Sections

#### 1. **Core Settings**
```yaml
num_records: 1000        # Number of patients to generate
output_dir: ./output     # Output directory
seed: 42                 # Reproducibility seed
output_format: both      # csv, parquet, or both
```

#### 2. **Demographic Distributions**
All distribution sections must sum to 1.0:
```yaml
age_dist:
  0-18: 0.2      # 20% pediatric patients
  19-40: 0.3     # 30% young adults
  41-65: 0.3     # 30% middle-aged
  66-120: 0.2    # 20% elderly
```

#### 3. **Social Determinants of Health (SDOH)**
Configure realistic population health factors:
```yaml
smoking_dist:
  Never: 0.7     # 70% never smoked
  Former: 0.2    # 20% former smokers
  Current: 0.1   # 10% current smokers
```

#### 4. **Migration Simulation**
```yaml
migration_settings:
  source_system: "vista"
  target_system: "oracle_health"
  success_rates:
    extract: 0.98
    transform: 0.95
    validate: 0.92
    load: 0.90
```

---

## Output Formats

The generator produces comprehensive healthcare datasets in multiple formats:

### 1. **Relational Data Tables (CSV/Parquet)**

#### Core Tables
- **`patients.csv`** - Patient demographics, SDOH, identifiers
- **`encounters.csv`** - Healthcare visits with realistic patterns
- **`conditions.csv`** - ICD-10 coded diagnoses with onset dates
- **`medications.csv`** - NDC coded prescriptions linked to conditions
- **`allergies.csv`** - Substance allergies with reaction severity
- **`procedures.csv`** - CPT coded medical procedures
- **`immunizations.csv`** - CVX coded vaccination records
- **`observations.csv`** - LOINC coded vitals and lab results
- **`deaths.csv`** - Mortality data with cause mapping
- **`family_history.csv`** - Genetic predisposition modeling

#### Schema Examples

**patients.csv**
```csv
patient_id,mrn,ssn,first_name,last_name,gender,birthdate,race,ethnicity,language,marital_status,phone,email,address,city,state,zip,insurance,smoking,alcohol,education,employment,housing
```

**conditions.csv**
```csv
patient_id,condition_id,encounter_id,condition_name,icd10_code,snomed_code,status,onset_date,resolution_date
```

**medications.csv**
```csv
patient_id,medication_id,encounter_id,medication_name,rxnorm_code,ndc_code,dosage,frequency,start_date,end_date
```

### 2. **Healthcare Interoperability Formats**

#### FHIR R4 Bundle (`fhir_bundle.json`)
US Core compliant FHIR resources:
```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "va-patient-123",
        "meta": {
          "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [
          {
            "use": "usual",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
            "system": "https://va.gov/patient-id",
            "value": "MRN123456"
          }
        ]
      }
    }
  ]
}
```

#### HL7 v2 Messages
- **`hl7_messages_adt.hl7`** - ADT (Admit/Discharge/Transfer) messages
- **`hl7_messages_oru.hl7`** - ORU (Observation Result) messages

**ADT Message Example:**
```
MSH|^~\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|20231215120000||ADT^A04|MSG001|P|2.5
PID|1||MRN123456^^^VA^MR~123456789^^^USA^SS||DOE^JOHN^M||19800115|M|||123 MAIN ST^^ANYTOWN^VA^12345||555-123-4567||EN|M||ACC123|||W^White^HL70005
PV1|1|I|ICU^101^A|||E|||ATTENDING123|REFERRING456||||ADM||||20231215120000
```

#### VistA MUMPS Global Format (`vista_globals.mumps`)
Production-accurate VA FileMan global structures:
```mumps
^DPT(123,0)=DOE,JOHN M
^DPT(123,.03)=2800115
^DPT(123,.02)=M
^DPT(123,.09)=123456789
^DGPM(456,0)=123^3231215^A
^DGPM(456,.01)=123
^DGPM(456,.02)=3231215
```

---

## Migration Simulation

The migration simulation feature provides realistic VistA-to-Oracle Health migration testing capabilities.

### Migration Strategies

#### 1. **Staged Migration** (Default)
Processes patients in controlled batches through all stages:
- Extract → Transform → Validate → Load
- Realistic delays and failure injection
- Patient-level status tracking

#### 2. **Big Bang Migration**
Attempts to migrate all patients simultaneously:
- Higher risk but faster completion
- Suitable for smaller datasets
- Stress testing capabilities

#### 3. **Parallel Migration**
Concurrent processing with multiple workers:
- Optimal for large datasets
- Configurable worker count
- Load balancing

### Migration Stages

#### 1. **Extract Stage**
- **Connect**: Establish VistA database connection
- **Query**: Execute patient data queries
- **Export**: Extract data to staging format

#### 2. **Transform Stage**
- **Parse**: Parse VistA MUMPS data structures
- **Map**: Map VistA fields to Oracle Health schema
- **Standardize**: Convert to standard formats

#### 3. **Validate Stage**
- **Schema Check**: Validate against target schema
- **Business Rules**: Apply clinical validation rules
- **Data Integrity**: Check referential integrity

#### 4. **Load Stage**
- **Staging**: Load to Oracle Health staging area
- **Production**: Move to production environment
- **Verification**: Verify successful migration

### Migration Configuration

#### Basic Migration Setup
```yaml
migration_settings:
  source_system: "vista"
  target_system: "oracle_health"
  migration_strategy: "staged"
  success_rates:
    extract: 0.98
    transform: 0.95
    validate: 0.92
    load: 0.90
```

#### Advanced Error Injection
```yaml
migration_settings:
  network_failure_rate: 0.05      # Network connectivity issues
  system_overload_rate: 0.03      # System resource exhaustion
  data_corruption_rate: 0.01      # Data integrity issues
  
  # Stage-specific configurations
  extract_timeout: 30              # seconds
  transform_memory_limit: 2048     # MB
  validate_strict_mode: true       # Strict validation
  load_batch_size: 50             # Records per batch
```

### Migration Analytics

The system provides comprehensive migration analytics:

#### Performance Metrics
- **Throughput**: Patients processed per minute
- **Success Rates**: Success percentage by stage
- **Processing Times**: Average duration per stage
- **Error Rates**: Failure frequency and types

#### Quality Tracking
- **Data Quality Scores**: Individual patient quality metrics (0.0-1.0)
- **Quality Degradation**: Realistic quality decline during migration
- **Quality Distribution**: Statistical analysis of quality scores

#### Failure Analysis
- **Common Failure Types**: Most frequent error patterns
- **Stage Performance**: Success/failure rates by stage
- **Bottleneck Identification**: Performance constraint analysis

### Running Migration Simulations

#### Command Line Examples

```bash
# Basic migration simulation
python3 -m src.core.synthetic_patient_generator \
  --num-records 500 \
  --simulate-migration

# Advanced migration with custom parameters
python3 -m src.core.synthetic_patient_generator \
  --num-records 1000 \
  --simulate-migration \
  --batch-size 50 \
  --migration-strategy staged \
  --migration-report detailed_analysis.txt

# High-volume migration testing
python3 -m src.core.synthetic_patient_generator \
  --num-records 10000 \
  --simulate-migration \
  --batch-size 250 \
  --migration-strategy parallel
```

#### Programmatic Usage

```python
from src.core.enhanced_migration_simulator import EnhancedMigrationSimulator
from src.core.enhanced_migration_tracker import EnhancedMigrationTracker
from src.core.synthetic_patient_generator import SyntheticPatientGenerator
from src.config.healthcare_migration_config import HealthcareMigrationConfig

# Custom configuration
config = HealthcareMigrationConfig()
config.migration_settings.stage_success_rates = {
    "extract": 0.95,
    "transform": 0.90,
    "validate": 0.85,
    "load": 0.80
}
config.batch_size = 100

# Generate patients and simulate migration
generator = SyntheticPatientGenerator(config)
patients = generator.generate_patients(1000)

# Run migration simulation
simulator = EnhancedMigrationSimulator(config)
tracker = EnhancedMigrationTracker()
result = simulator.simulate_staged_migration(patients, "test_batch_001", tracker)

# Analyze results
analytics = tracker.get_migration_analytics()
print(f"Overall success rate: {analytics['overall_success_rate']:.2%}")
print(f"Average processing time: {analytics['average_processing_time']:.2f}s")

# Export detailed report
tracker.export_migration_report("migration_analysis.txt")
```

---

## Advanced Configuration

### Performance Tuning

#### Parallel Processing
```yaml
# Enable concurrent processing
concurrent_workers: 4        # Number of worker threads
batch_size: 250             # Records per batch
memory_limit: 4096          # MB per worker
```

#### Large Dataset Optimization
```yaml
# For 10,000+ patients
num_records: 50000
concurrent_workers: 8
batch_size: 500
output_format: parquet      # More efficient for large data
```

### Healthcare-Specific Settings

#### Clinical Data Generation
```yaml
# Customize clinical data complexity
clinical_complexity: "high"  # Options: low, medium, high
condition_prevalence:
  diabetes: 0.12
  hypertension: 0.25
  heart_disease: 0.08
```

#### Terminology Systems
```yaml
# Configure medical coding systems
terminology_systems:
  conditions: ["icd10", "snomed", "icd9"]
  medications: ["rxnorm", "ndc"]
  procedures: ["cpt", "snomed"]
```

### Data Quality Settings

#### Quality Thresholds
```yaml
data_quality:
  minimum_quality_score: 0.85    # Minimum acceptable quality
  quality_degradation_rate: 0.02 # Per-stage degradation
  validation_strictness: "high"  # low, medium, high
```

#### Error Injection Patterns
```yaml
error_patterns:
  medication_errors:
    dosage_corruption: 0.03
    drug_interaction: 0.02
  demographic_errors:
    missing_fields: 0.05
    format_errors: 0.02
```

---

## Performance & Scalability

### Performance Benchmarks

| Patient Count | Processing Time | Memory Usage | Throughput |
|---------------|----------------|--------------|------------|
| 1,000 | 3-5 seconds | 50MB | 200-300/sec |
| 10,000 | 30-45 seconds | 200MB | 250-350/sec |
| 100,000 | 5-8 minutes | 1.5GB | 300-400/sec |

### Scalability Guidelines

#### Small Deployments (< 1,000 patients)
```bash
python3 -m src.core.synthetic_patient_generator --num-records 500
```

#### Medium Deployments (1,000 - 10,000 patients)
```bash
python3 -m src.core.synthetic_patient_generator \
  --num-records 5000 \
  --parquet \
  --simulate-migration \
  --batch-size 250
```

#### Large Deployments (10,000+ patients)
```yaml
# config.yaml for large deployments
num_records: 50000
output_format: parquet
concurrent_workers: 8
batch_size: 500
simulate_migration: true
migration_strategy: "parallel"
```

### Memory Management

#### Memory-Efficient Settings
```yaml
# For memory-constrained environments
batch_size: 100             # Smaller batches
concurrent_workers: 2       # Fewer workers
output_format: csv          # Less memory than Parquet generation
```

#### High-Performance Settings
```yaml
# For high-performance environments
batch_size: 1000
concurrent_workers: 16
output_format: parquet
memory_limit: 8192
```

---

## Examples

### Example 1: Basic Healthcare Data Generation

**Command:**
```bash
python3 -m src.core.synthetic_patient_generator --num-records 1000 --output-dir ./hospital_data
```

**Output:**
- 1,000 synthetic patient records
- Complete medical histories with encounters, conditions, medications
- CSV format tables with referential integrity
- Generated in `./hospital_data/` directory

### Example 2: EHR Migration Testing

**Configuration File (`migration_test.yaml`):**
```yaml
num_records: 500
output_dir: migration_test
simulate_migration: true
batch_size: 50
migration_strategy: staged
migration_settings:
  source_system: "vista"
  target_system: "oracle_health"
  success_rates:
    extract: 0.95
    transform: 0.90
    validate: 0.88
    load: 0.85
report_file: "test_report.txt"
migration_report: "migration_analysis.txt"
```

**Command:**
```bash
python3 -m src.core.synthetic_patient_generator --config migration_test.yaml
```

**Output:**
- 500 patients with simulated VistA-to-Oracle migration
- Realistic failure injection and quality degradation
- Comprehensive migration analytics report
- Patient-level migration status tracking

### Example 3: Multi-Format Interoperability Testing

**Configuration:**
```yaml
num_records: 200
output_dir: interop_test
output_format: both
seed: 12345

# Generate diverse patient population
age_dist:
  0-18: 0.25    # High pediatric population
  19-40: 0.25
  41-65: 0.25
  66-120: 0.25

race_dist:
  White: 0.4
  Black: 0.2
  Asian: 0.15
  Hispanic: 0.2
  Other: 0.05
```

**Command:**
```bash
python3 -m src.core.synthetic_patient_generator --config interop_test.yaml
```

**Output:**
- Diverse patient population across age groups
- FHIR R4 Bundle with US Core compliance
- HL7 v2 ADT and ORU messages
- VistA MUMPS global format
- CSV/Parquet relational tables

### Example 4: Performance Testing

**Large Volume Test:**
```bash
python3 -m src.core.synthetic_patient_generator \
  --num-records 10000 \
  --parquet \
  --simulate-migration \
  --batch-size 500 \
  --migration-strategy parallel \
  --output-dir performance_test
```

**Expected Results:**
- 10,000 patients processed in ~2-3 minutes
- Parallel migration simulation with realistic timing
- Performance metrics and bottleneck analysis
- Memory usage optimization

---

## Troubleshooting

### Common Issues

#### 1. **Memory Errors with Large Datasets**

**Problem:** `MemoryError` when generating 10,000+ patients

**Solution:**
```yaml
# Reduce memory usage
batch_size: 100
concurrent_workers: 2
output_format: csv  # Less memory-intensive than Parquet
```

#### 2. **Slow Performance**

**Problem:** Generation taking longer than expected

**Solutions:**
- Increase batch size: `--batch-size 500`
- Use parallel processing: `concurrent_workers: 4`
- Use SSD storage for output directory
- Reduce number of concurrent workers if CPU-bound

#### 3. **Configuration File Errors**

**Problem:** `yaml.YAMLError` when loading config

**Solutions:**
- Validate YAML syntax using online validators
- Ensure all distributions sum to 1.0
- Check indentation (use spaces, not tabs)
- Verify all required fields are present

#### 4. **Distribution Sum Errors**

**Problem:** `ValueError: Distribution values must sum to 1.0`

**Solution:**
```yaml
# Ensure distributions sum exactly to 1.0
age_dist:
  0-18: 0.2
  19-40: 0.3
  41-65: 0.3
  66-120: 0.2  # Total: 1.0
```

#### 5. **Migration Simulation Failures**

**Problem:** All patients failing migration

**Solutions:**
- Check success rates aren't too low
- Verify batch size isn't too large
- Review error injection rates
- Check system resources

### Performance Optimization

#### For Large Datasets (10,000+ patients)
```yaml
num_records: 50000
output_format: parquet      # More efficient
concurrent_workers: 8       # Parallel processing
batch_size: 1000           # Large batches
migration_strategy: "parallel"
```

#### For Memory-Constrained Systems
```yaml
batch_size: 50             # Small batches
concurrent_workers: 1      # Single-threaded
output_format: csv         # Less memory
```

#### For Maximum Performance
```yaml
concurrent_workers: 16     # High parallelism
batch_size: 2000          # Large batches
output_format: parquet    # Efficient format
memory_limit: 16384       # 16GB memory limit
```

### Debug Mode

Enable verbose logging for troubleshooting:
```bash
python3 -m src.core.synthetic_patient_generator \
  --num-records 100 \
  --simulate-migration \
  --verbose  # Add verbose flag for detailed logging
```

### Validation Commands

**Test configuration file:**
```bash
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

**Verify output files:**
```bash
ls -la output_directory/
wc -l output_directory/*.csv
```

**Check memory usage:**
```bash
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

---

## Support

### Getting Help

- **Documentation**: Review this user guide and README.md
- **Examples**: Check the `demos/` directory for comprehensive usage examples:
  - `demos/migration_demo.py` - Basic migration simulation
  - `demos/enhanced_migration_demo.py` - Advanced migration with analytics
  - `demos/migration_analytics_demo.py` - Migration analytics and reporting
  - `demos/final_performance_demo.py` - Performance testing framework
- **Testing**: Run test files in `tests/` directory:
  - `tests/simple_performance_test.py` - Basic performance validation
  - `tests/test_migration_simulator.py` - Migration simulation testing
  - `tests/run_performance_tests.py` - Comprehensive test suite

### Performance Monitoring

Monitor system performance during generation:
```bash
# Monitor memory usage
htop

# Monitor disk I/O
iotop

# Check output file sizes
du -sh output_directory/
```

### Best Practices

1. **Start Small**: Test with 100-500 patients first
2. **Use Configuration Files**: Easier to reproduce and modify
3. **Monitor Resources**: Watch memory and disk usage
4. **Backup Configurations**: Save working config files
5. **Version Control**: Track configuration changes
6. **Test Migration Settings**: Validate migration parameters before large runs

This comprehensive user guide provides all the information needed to effectively use the Synthetic Healthcare Data Generator for healthcare data generation and migration simulation testing.