# Synthetic Patient Data Generator

This project generates highly realistic, Synthea-like synthetic patient data for research, analytics, and software development. It outputs normalized tables (patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family history) in both CSV and Parquet formats.

## Features
- Fast, parallelized data generation using Python and Polars
- Realistic demographics, social determinants, and medical histories
- Interdependent conditions, medications, encounters, and outcomes
- Output as normalized CSV and Parquet files

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

## Output

The following files will be created in the current directory (both CSV and Parquet formats):

- `patients.csv` / `patients.parquet`: Demographics, SDOH, etc.
- `encounters.csv` / `encounters.parquet`: Healthcare visits
- `conditions.csv` / `conditions.parquet`: Diagnoses (chronic/acute)
- `medications.csv` / `medications.parquet`: Prescriptions
- `allergies.csv` / `allergies.parquet`: Allergies and reactions
- `procedures.csv` / `procedures.parquet`: Medical procedures
- `immunizations.csv` / `immunizations.parquet`: Vaccines
- `observations.csv` / `observations.parquet`: Vitals and labs
- `deaths.csv` / `deaths.parquet`: Death date and cause (subset of patients)
- `family_history.csv` / `family_history.parquet`: Family member conditions

Each table is normalized and linked by `patient_id` (and `encounter_id` where appropriate).

## Customization
- The generator can be extended to add more fields, logic, or output formats.
- For large datasets, use higher numbers when prompted.

## Requirements
- Python 3.8+
- See `requirements.txt` for dependencies

## License
MIT License (see LICENSE file) 