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