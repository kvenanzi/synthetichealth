# Synthetic Healthcare Data Generator

A comprehensive synthetic patient data generator designed for healthcare migration simulations, EHR system testing, and interoperability research. This project generates realistic, Synthea-like healthcare data with multi-format export capabilities including **FHIR R4**, **HL7 v2.x**, **VistA MUMPS**, **CSV**, and **Parquet** formats.

## 🎯 Current Status

**Production-Ready Multi-Format Healthcare Data Generator**

✅ **Core Data Generation** - Complete normalized healthcare datasets with realistic relationships  
✅ **FHIR R4 Export** - US Core compliant Patient and Condition resources with proper terminology mappings  
✅ **HL7 v2 Support** - ADT (Admit/Discharge/Transfer) and ORU (Observation Result) messages with validation  
✅ **VistA MUMPS Format** - Production-accurate VA global structures for healthcare migration simulation  
✅ **Multi-Format Output** - CSV, Parquet, JSON with configurable export options  
✅ **Advanced Configuration** - YAML-based customization of demographics and social determinants

## 🚀 Key Features

### Multi-Format Healthcare Data Export
- **FHIR R4** - US Core Patient/Condition resources with proper coding systems
- **HL7 v2.x** - ADT and ORU messages with validation and terminology mapping  
- **VistA MUMPS** - Production-accurate VA FileMan global structures
- **CSV/Parquet** - Normalized relational tables for analytics
- **JSON Bundles** - Structured healthcare data packages

### Advanced Data Generation
- **Realistic Demographics** - Age, gender, race, ethnicity with configurable distributions
- **Social Determinants** - Smoking, alcohol, education, employment, housing status
- **Clinical Relationships** - Conditions → medications → observations with medical accuracy
- **Family History** - Genetic predispositions and inherited conditions
- **Parallelized Processing** - High-performance generation using concurrent futures

### Healthcare Migration Simulation
- **VistA-to-Oracle Migration** - Accurate data format transformation for VA systems
- **Multi-System Integration** - Cross-platform healthcare data compatibility
- **Production Validation** - Real-world tested format structures and mappings

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd synthetichealth
   ```

2. **Create and activate a Python virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the generator script:

```bash
source .venv/bin/activate
python synthetic_patient_generator.py
```

You will be prompted for the number of synthetic patient records to generate (e.g., `1000`).

## 📊 Output Formats

### Relational Data Tables (CSV/Parquet)
- `patients` - Demographics, SDOH, multiple identifiers
- `encounters` - Healthcare visits with realistic patterns
- `conditions` - ICD-10 coded diagnoses with onset dates
- `medications` - NDC coded prescriptions linked to conditions
- `allergies` - Substance allergies with reaction severity
- `procedures` - CPT coded medical procedures
- `immunizations` - CVX coded vaccination records
- `observations` - LOINC coded vitals and lab results
- `deaths` - Mortality data with cause mapping
- `family_history` - Genetic predisposition modeling

### Healthcare Interoperability Formats
- `fhir_bundle.json` - FHIR R4 Bundle with Patient/Condition resources
- `hl7_messages_adt.hl7` - HL7 v2 Admit/Discharge/Transfer messages
- `hl7_messages_oru.hl7` - HL7 v2 Observation Result messages  
- `vista_globals.mumps` - VistA FileMan global structures (default: FileMan-internal pointers)

VistA export modes:
- `--vista-mode fileman_internal` (default): emits pointer-clean globals with ICD pointers under `^ICD9`, Clinic Stops under `^DIC(40.7)`, and quoted phone numbers; visit GUIDs are stored as `^AUPNVSIT("GUID",IEN)`.
- `--vista-mode legacy`: retains earlier text-based encoding for compatibility.

All tables linked by `patient_id` with referential integrity maintained across formats.

## 🔮 Remaining Development Phases

Based on the original technical specifications, the following phases are planned but not yet implemented:

### Phase 4: Migration Simulation 
- **MigrationSimulator Class** - Staged migration logic with realistic delays and failures
- **Migration Status Tracking** - Patient-level migration status and data quality scoring
- **Data Quality Degradation** - Simulate realistic data quality issues during migration
- **Migration Analytics** - Comprehensive logging and success/failure reporting
- **Multi-stage Processing** - Extract → Transform → Validate → Load pipeline simulation

### Phase 5: Integration & Testing
- **MultiFormatHealthcareGenerator** - Unified architecture replacing individual formatters
- **Enhanced Configuration** - Migration settings, data quality controls, error injection
- **Advanced Validation** - Comprehensive FHIR R4 schema validation and HL7 v2 structure validation  
- **Performance Analytics** - Migration performance metrics and optimization
- **End-to-end Testing** - Complete migration simulation testing framework

### Technical Debt & Architecture Improvements
- **Unified Class Architecture** - Replace function-based approach with class-based design
- **Enhanced Dependencies** - Add fhir.resources, hl7apy, jsonschema for better validation
- **Configuration Extensions** - Add migration_settings and data_quality sections to YAML config
- **Error Injection System** - Configurable error rates and error type simulation

## 🛠️ Technical Requirements
- **Python 3.8+** with concurrent.futures support
- **Core Dependencies**: polars, faker, PyYAML for high-performance data processing
- **Optional**: fhir.resources for enhanced FHIR validation (planned)

## 📜 License
MIT License - See LICENSE file for details

## 🤝 Contributing
This project supports healthcare interoperability research and migration testing. Contributions welcome for additional formats, clinical accuracy improvements, and performance optimizations. 

## YAML Configuration

You can specify all advanced options in a YAML config file and pass it with `--config config.yaml`. CLI flags override config file values.

Example `config.yaml`:

```yaml
num_records: 1000
output_dir: demo_dist
seed: 42
output_format: csv  # or 'parquet' or 'both'
age_dist:
  0-18: 0.1
  19-40: 0.2
  41-65: 0.4
  66-120: 0.3
gender_dist:
  male: 0.7
  female: 0.3
race_dist:
  White: 0.5
  Black: 0.2
  Asian: 0.1
  Hispanic: 0.1
  Other: 0.1
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
  High School: 0.2
  Bachelor: 0.3
  Master: 0.2
  Doctorate: 0.1
  None: 0.2
employment_dist:
  Employed: 0.5
  Unemployed: 0.1
  Student: 0.2
  Retired: 0.1
  Disabled: 0.1
housing_dist:
  Stable: 0.8
  Homeless: 0.05
  Temporary: 0.1
  Assisted Living: 0.05
```

Run with:
```bash
python synthetic_patient_generator.py --config config.yaml
``` 

## Sample Report

After data generation, a summary report is printed to the console and can optionally be saved to a file using the `--report-file` flag or `report_file` in the YAML config. The report includes:
- Counts for each table (patients, encounters, conditions, etc.)
- Distributions for age, gender, race, and SDOH fields (smoking, alcohol, education, employment, housing)
- Top 10 most common conditions

**Example usage:**
```bash
python synthetic_patient_generator.py --config config.yaml --report-file sample_report.txt
```

This will print the report and save it to `sample_report.txt`. 

## ELI5: How to Use the YAML Config File and Set Distributions

**What is this file?**
- You can set how many patients to make, where to save the files, and what your synthetic population should look like (age, gender, race, etc.).

**How do I use it?**
1. Make a file called `config.yaml` (or any name you like).
2. Copy and paste this example, then change the numbers to match the population you want:

```yaml
num_records: 1000
output_dir: my_output
seed: 42
output_format: csv
age_dist:
  0-18: 0.2
  19-40: 0.3
  41-65: 0.3
  66-120: 0.2
gender_dist:
  male: 0.5
  female: 0.5
race_dist:
  White: 0.6
  Black: 0.15
  Asian: 0.1
  Hispanic: 0.1
  Other: 0.05
smoking_dist:
  Never: 0.7
  Former: 0.2
  Current: 0.1
# ...and so on for alcohol, education, employment, housing
```

**How do I run it?**
```bash
python synthetic_patient_generator.py --config config.yaml
```

**How do the distributions work?**
- Each group (like age or gender) has options that add up to 1.0 (or 100%).
- For example, if you want 20% kids, 30% young adults, 30% middle-aged, and 20% seniors, set the age_dist like above.
- The generator will try to match these percentages in the data it creates.

**Tip:**
- You can leave out any group you don't care about, and the generator will use a default (even mix). 
