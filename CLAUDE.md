# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a synthetic patient data generator that creates realistic, Synthea-like healthcare data for research and development. The main script generates normalized tables (patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history) in CSV and/or Parquet formats.

## Development Commands

### Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run Data Generation
```bash
# Basic usage (prompts for number of records)
python3 synthetic_patient_generator.py

# With specific number of records
python3 synthetic_patient_generator.py --num-records 1000

# Using YAML configuration
python3 synthetic_patient_generator.py --config config.yaml

# Generate with report file
python3 synthetic_patient_generator.py --config config.yaml --report-file output_report.txt

# Output format options
python3 synthetic_patient_generator.py --csv           # CSV only
python3 synthetic_patient_generator.py --parquet      # Parquet only  
python3 synthetic_patient_generator.py --both         # Both formats (default)
```

## Architecture

### Core Components
- **synthetic_patient_generator.py**: Main script containing all data generation logic
- **config.yaml**: YAML configuration file for customizing generation parameters
- **requirements.txt**: Python dependencies (polars, faker, PyYAML)

### Key Data Structures
- Uses Polars DataFrames for efficient data processing
- Weighted choice functions for realistic demographic distributions
- Condition prevalence mappings based on age, gender, race, and SDOH factors
- Interconnected data generation ensuring referential integrity between tables

### Generated Output Tables
All tables linked by `patient_id` (and `encounter_id` where applicable):
- `patients`: Demographics and SDOH data
- `encounters`: Healthcare visits
- `conditions`: Medical diagnoses
- `medications`: Prescriptions linked to conditions
- `allergies`: Patient allergies and reactions
- `procedures`: Medical procedures
- `immunizations`: Vaccination records
- `observations`: Vitals and lab results
- `deaths`: Death records (subset of patients)
- `family_history`: Family medical history

### Configuration System
- CLI arguments override YAML config values
- Supports customizable distributions for demographics and SDOH factors
- Output directory, format, and seed configuration
- Report generation with summary statistics

### Data Generation Strategy
- Parallelized processing using concurrent.futures
- Realistic medical relationships (conditions → medications → observations)
- Age/gender/race-based condition prevalence
- SDOH factors influence health outcomes
- Family history generation with genetic predispositions