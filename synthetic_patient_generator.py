import polars as pl
from faker import Faker
import random
import concurrent.futures
import sys
from datetime import datetime, timedelta
import uuid
from collections import defaultdict
import argparse
import os
import yaml

# Constants for data generation
GENDERS = ["male", "female", "other"]
RACES = ["White", "Black", "Asian", "Hispanic", "Native American", "Other"]
ETHNICITIES = ["Not Hispanic or Latino", "Hispanic or Latino"]
MARITAL_STATUSES = ["Never Married", "Married", "Divorced", "Widowed", "Separated"]
LANGUAGES = ["English", "Spanish", "Chinese", "French", "German", "Vietnamese"]
INSURANCES = ["Medicare", "Medicaid", "Private", "Uninsured"]
ENCOUNTER_TYPES = ["Wellness Visit", "Emergency", "Follow-up", "Specialist", "Lab", "Surgery"]
ENCOUNTER_REASONS = ["Checkup", "Injury", "Illness", "Chronic Disease", "Vaccination", "Lab Work"]
CONDITION_NAMES = ["Hypertension", "Diabetes", "Asthma", "COPD", "Heart Disease", "Obesity", "Depression", "Anxiety", "Arthritis", "Cancer", "Flu", "COVID-19", "Migraine", "Allergy"]
CONDITION_STATUSES = ["active", "resolved", "remission"]
MEDICATIONS = ["Metformin", "Lisinopril", "Atorvastatin", "Albuterol", "Insulin", "Ibuprofen", "Amoxicillin", "Levothyroxine", "Amlodipine", "Omeprazole"]
ALLERGY_SUBSTANCES = ["Penicillin", "Peanuts", "Shellfish", "Latex", "Bee venom", "Aspirin", "Eggs", "Milk"]
ALLERGY_REACTIONS = ["Rash", "Anaphylaxis", "Hives", "Swelling", "Nausea", "Vomiting"]
ALLERGY_SEVERITIES = ["mild", "moderate", "severe"]
PROCEDURES = ["Appendectomy", "Colonoscopy", "MRI Scan", "X-ray", "Blood Test", "Vaccination", "Physical Therapy", "Cataract Surgery"]
IMMUNIZATIONS = ["Influenza", "COVID-19", "Tetanus", "Hepatitis B", "MMR", "Varicella", "HPV"]
OBSERVATION_TYPES = ["Height", "Weight", "Blood Pressure", "Heart Rate", "Temperature", "Hemoglobin A1c", "Cholesterol"]

SDOH_SMOKING = ["Never", "Former", "Current"]
SDOH_ALCOHOL = ["Never", "Occasional", "Regular", "Heavy"]
SDOH_EDUCATION = ["None", "Primary", "Secondary", "High School", "Associate", "Bachelor", "Master", "Doctorate"]
SDOH_EMPLOYMENT = ["Unemployed", "Employed", "Student", "Retired", "Disabled"]
SDOH_HOUSING = ["Stable", "Homeless", "Temporary", "Assisted Living"]

DEATH_CAUSES = [
    "Heart Disease", "Cancer", "Stroke", "COPD", "Accident", "Alzheimer's", "Diabetes", "Kidney Disease", "Sepsis", "Pneumonia", "COVID-19", "Liver Disease", "Suicide", "Homicide"
]

FAMILY_RELATIONSHIPS = ["Mother", "Father", "Sibling"]

fake = Faker()

def weighted_choice(choices):
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    return choices[-1][0]

# Condition prevalence by age, gender, race, SDOH
CONDITION_PREVALENCE = {
    # name: (age_min, age_max, gender, race, smoking, alcohol, weight)
    "Asthma": [(0, 18, None, None, None, None, 0.12), (19, 65, None, None, None, None, 0.06)],
    "COPD": [(40, 120, None, None, "Current", None, 0.15)],
    "Hypertension": [(30, 120, None, None, None, None, 0.25)],
    "Diabetes": [(40, 120, None, None, None, None, 0.12)],
    "Heart Disease": [(50, 120, "male", None, None, None, 0.18), (50, 120, "female", None, None, None, 0.10)],
    "Cancer": [(50, 120, None, None, None, None, 0.10)],
    "Depression": [(12, 120, None, None, None, None, 0.15)],
    "Anxiety": [(12, 120, None, None, None, None, 0.18)],
    "Obesity": [(10, 120, None, None, None, None, 0.20)],
    "Arthritis": [(40, 120, None, None, None, None, 0.15)],
    "Flu": [(0, 120, None, None, None, None, 0.08)],
    "COVID-19": [(0, 120, None, None, None, None, 0.05)],
    "Migraine": [(10, 60, "female", None, None, None, 0.12), (10, 60, "male", None, None, None, 0.06)],
    "Allergy": [(0, 30, None, None, None, None, 0.15)],
    "Stroke": [(60, 120, None, None, None, None, 0.07)],
    "Alzheimer's": [(70, 120, None, None, None, None, 0.10)],
}

# Map conditions to likely medications, observations, and death causes
CONDITION_MEDICATIONS = {
    "Hypertension": ["Lisinopril", "Amlodipine"],
    "Diabetes": ["Metformin", "Insulin"],
    "Asthma": ["Albuterol"],
    "COPD": ["Albuterol"],
    "Heart Disease": ["Atorvastatin", "Amlodipine"],
    "Obesity": [],
    "Depression": ["Levothyroxine"],
    "Anxiety": ["Levothyroxine"],
    "Arthritis": ["Ibuprofen"],
    "Cancer": ["Amoxicillin"],
    "Flu": ["Amoxicillin"],
    "COVID-19": ["Amoxicillin"],
    "Migraine": ["Ibuprofen"],
    "Allergy": [],
    "Stroke": ["Atorvastatin"],
    "Alzheimer's": [],
}
CONDITION_OBSERVATIONS = {
    "Hypertension": ["Blood Pressure"],
    "Diabetes": ["Hemoglobin A1c", "Cholesterol"],
    "Asthma": ["Heart Rate"],
    "COPD": ["Heart Rate"],
    "Heart Disease": ["Cholesterol"],
    "Obesity": ["Weight"],
    "Depression": [],
    "Anxiety": [],
    "Arthritis": [],
    "Cancer": [],
    "Flu": ["Temperature"],
    "COVID-19": ["Temperature"],
    "Migraine": [],
    "Allergy": [],
    "Stroke": [],
    "Alzheimer's": [],
}
CONDITION_DEATH_CAUSES = {
    "Hypertension": "Heart Disease",
    "Diabetes": "Diabetes",
    "Asthma": "COPD",
    "COPD": "COPD",
    "Heart Disease": "Heart Disease",
    "Obesity": "Heart Disease",
    "Depression": "Suicide",
    "Anxiety": "Suicide",
    "Arthritis": "Heart Disease",
    "Cancer": "Cancer",
    "Flu": "Pneumonia",
    "COVID-19": "COVID-19",
    "Migraine": "Stroke",
    "Allergy": "Anaphylaxis",
    "Stroke": "Stroke",
    "Alzheimer's": "Alzheimer's",
}

def assign_conditions(patient):
    age = patient["age"]
    gender = patient["gender"]
    race = patient["race"]
    smoking = patient["smoking_status"]
    alcohol = patient["alcohol_use"]
    assigned = []
    for cond, rules in CONDITION_PREVALENCE.items():
        prob = 0
        for rule in rules:
            amin, amax, g, r, s, a, w = rule
            if amin <= age <= amax:
                if (g is None or g == gender) and (r is None or r == race) and (s is None or s == smoking) and (a is None or a == alcohol):
                    prob = max(prob, w)
        if random.random() < prob:
            assigned.append(cond)
    return assigned

def parse_distribution(dist_str, valid_keys, value_type="str", default_dist=None):
    if not dist_str:
        return default_dist
    if isinstance(dist_str, dict):
        # Validate keys and sum
        total = sum(dist_str.values())
        for k in dist_str.keys():
            if k not in valid_keys:
                raise ValueError(f"Invalid key '{k}' in distribution. Valid: {valid_keys}")
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Distribution must sum to 1.0, got {total}")
        return dist_str
    dist = {}
    total = 0.0
    for part in dist_str.split(","):
        k, v = part.split(":")
        k = k.strip()
        v = float(v.strip())
        if value_type == "int":
            k = int(k)
        if k not in valid_keys:
            raise ValueError(f"Invalid key '{k}' in distribution. Valid: {valid_keys}")
        dist[k] = v
        total += v
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Distribution must sum to 1.0, got {total}")
    return dist

def sample_from_dist(dist):
    keys = list(dist.keys())
    weights = list(dist.values())
    return random.choices(keys, weights=weights, k=1)[0]

def generate_patient(_):
    birthdate = fake.date_of_birth(minimum_age=0, maximum_age=100)
    age = (datetime.now().date() - birthdate).days // 365
    patient_id = str(uuid.uuid4())
    income = random.randint(0, 200000) if age >= 18 else 0
    return {
        "patient_id": patient_id,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "gender": random.choice(GENDERS),
        "birthdate": birthdate.isoformat(),
        "age": age,
        "race": random.choice(RACES),
        "ethnicity": random.choice(ETHNICITIES),
        "address": fake.street_address(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "zip": fake.zipcode(),
        "country": "US",
        "marital_status": random.choice(MARITAL_STATUSES),
        "language": random.choice(LANGUAGES),
        "insurance": random.choice(INSURANCES),
        "ssn": fake.ssn(),
        # SDOH fields
        "smoking_status": random.choice(SDOH_SMOKING),
        "alcohol_use": random.choice(SDOH_ALCOHOL),
        "education": random.choice(SDOH_EDUCATION) if age >= 18 else "None",
        "employment_status": random.choice(SDOH_EMPLOYMENT) if age >= 16 else "Student",
        "income": income,
        "housing_status": random.choice(SDOH_HOUSING),
    }

def generate_encounters(patient, conditions=None, min_enc=1, max_enc=8):
    # More chronic conditions = more encounters
    n = random.randint(min_enc, max_enc)
    if conditions:
        n += int(len([c for c in conditions if c["name"] in CONDITION_MEDICATIONS]) * 1.5)
    encounters = []
    start_date = datetime.strptime(patient["birthdate"], "%Y-%m-%d")
    for _ in range(n):
        days_offset = random.randint(0, (datetime.now() - start_date).days)
        encounter_date = start_date + timedelta(days=days_offset)
        encounters.append({
            "encounter_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "date": encounter_date.date().isoformat(),
            "type": random.choice(ENCOUNTER_TYPES),
            "reason": random.choice(ENCOUNTER_REASONS),
            "provider": fake.company(),
            "location": fake.city(),
        })
    return encounters

def generate_conditions(patient, encounters, min_cond=1, max_cond=5):
    # Use assigned conditions for realism
    assigned = assign_conditions(patient)
    n = max(min_cond, len(assigned))
    conditions = []
    for cond in assigned:
        enc = random.choice(encounters) if encounters else None
        onset_date = enc["date"] if enc else patient["birthdate"]
        conditions.append({
            "condition_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "name": cond,
            "status": random.choice(CONDITION_STATUSES),
            "onset_date": onset_date,
        })
    # Add a few random acute conditions
    for _ in range(random.randint(0, 2)):
        cond = random.choice([c for c in CONDITION_NAMES if c not in assigned])
        enc = random.choice(encounters) if encounters else None
        onset_date = enc["date"] if enc else patient["birthdate"]
        conditions.append({
            "condition_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "name": cond,
            "status": random.choice(CONDITION_STATUSES),
            "onset_date": onset_date,
        })
    return conditions

def generate_medications(patient, encounters, conditions=None, min_med=0, max_med=4):
    n = random.randint(min_med, max_med)
    medications = []
    # Add medications for chronic conditions
    if conditions:
        for cond in conditions:
            meds = CONDITION_MEDICATIONS.get(cond["name"], [])
            for med in meds:
                enc = random.choice(encounters) if encounters else None
                start_date = enc["date"] if enc else patient["birthdate"]
                if isinstance(start_date, str):
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                else:
                    start_date_obj = start_date
                if random.random() < 0.7:
                    end_date = None
                else:
                    end_date = fake.date_between(start_date=start_date_obj, end_date="today").isoformat()
                medications.append({
                    "medication_id": str(uuid.uuid4()),
                    "patient_id": patient["patient_id"],
                    "encounter_id": enc["encounter_id"] if enc else None,
                    "name": med,
                    "start_date": start_date,
                    "end_date": end_date,
                })
    # Add a few random medications
    for _ in range(n):
        enc = random.choice(encounters) if encounters else None
        start_date = enc["date"] if enc else patient["birthdate"]
        if isinstance(start_date, str):
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start_date_obj = start_date
        if random.random() < 0.7:
            end_date = None
        else:
            end_date = fake.date_between(start_date=start_date_obj, end_date="today").isoformat()
        medications.append({
            "medication_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "name": random.choice(MEDICATIONS),
            "start_date": start_date,
            "end_date": end_date,
        })
    return medications

def generate_allergies(patient, min_all=0, max_all=2):
    n = random.randint(min_all, max_all)
    allergies = []
    for _ in range(n):
        allergies.append({
            "allergy_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "substance": random.choice(ALLERGY_SUBSTANCES),
            "reaction": random.choice(ALLERGY_REACTIONS),
            "severity": random.choice(ALLERGY_SEVERITIES),
        })
    return allergies

def generate_procedures(patient, encounters, min_proc=0, max_proc=3):
    n = random.randint(min_proc, max_proc)
    procedures = []
    for _ in range(n):
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        procedures.append({
            "procedure_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "name": random.choice(PROCEDURES),
            "date": date,
            "outcome": random.choice(["successful", "complication", "failed"]),
        })
    return procedures

def generate_immunizations(patient, encounters, min_imm=0, max_imm=3):
    n = random.randint(min_imm, max_imm)
    immunizations = []
    for _ in range(n):
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        immunizations.append({
            "immunization_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "vaccine": random.choice(IMMUNIZATIONS),
            "date": date,
        })
    return immunizations

def generate_observations(patient, encounters, conditions=None, min_obs=1, max_obs=8):
    n = random.randint(min_obs, max_obs)
    observations = []
    # Add observations for chronic conditions
    if conditions:
        for cond in conditions:
            obs_types = CONDITION_OBSERVATIONS.get(cond["name"], [])
            for obs_type in obs_types:
                enc = random.choice(encounters) if encounters else None
                date = enc["date"] if enc else patient["birthdate"]
                value = None
                if obs_type == "Height":
                    value = round(random.uniform(140, 200), 1)
                elif obs_type == "Weight":
                    value = round(random.uniform(40, 150), 1)
                elif obs_type == "Blood Pressure":
                    value = f"{random.randint(90, 180)}/{random.randint(60, 110)}"
                elif obs_type == "Heart Rate":
                    value = random.randint(50, 120)
                elif obs_type == "Temperature":
                    value = round(random.uniform(36.0, 39.0), 1)
                elif obs_type == "Hemoglobin A1c":
                    value = round(random.uniform(4.5, 12.0), 1)
                elif obs_type == "Cholesterol":
                    value = random.randint(120, 300)
                observations.append({
                    "observation_id": str(uuid.uuid4()),
                    "patient_id": patient["patient_id"],
                    "encounter_id": enc["encounter_id"] if enc else None,
                    "type": obs_type,
                    "value": value,
                    "date": date,
                })
    # Add a few random observations
    for _ in range(n):
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        obs_type = random.choice(OBSERVATION_TYPES)
        value = None
        if obs_type == "Height":
            value = round(random.uniform(140, 200), 1)
        elif obs_type == "Weight":
            value = round(random.uniform(40, 150), 1)
        elif obs_type == "Blood Pressure":
            value = f"{random.randint(90, 180)}/{random.randint(60, 110)}"
        elif obs_type == "Heart Rate":
            value = random.randint(50, 120)
        elif obs_type == "Temperature":
            value = round(random.uniform(36.0, 39.0), 1)
        elif obs_type == "Hemoglobin A1c":
            value = round(random.uniform(4.5, 12.0), 1)
        elif obs_type == "Cholesterol":
            value = random.randint(120, 300)
        observations.append({
            "observation_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "type": obs_type,
            "value": value,
            "date": date,
        })
    return observations

def generate_death(patient, conditions=None):
    # Simulate a 10% chance of death for realism
    if random.random() < 0.1:
        birth = datetime.strptime(patient["birthdate"], "%Y-%m-%d").date()
        min_death_age = max(1, int(patient["age"] * 0.5))
        death_age = random.randint(min_death_age, patient["age"]) if patient["age"] > 1 else 1
        death_date = birth + timedelta(days=death_age * 365)
        if death_date > datetime.now().date():
            death_date = datetime.now().date()
        # Prefer cause of death from chronic conditions
        cause = None
        if conditions:
            for cond in conditions:
                if cond["name"] in CONDITION_DEATH_CAUSES:
                    cause = CONDITION_DEATH_CAUSES[cond["name"]]
                    break
        if not cause:
            cause = random.choice(DEATH_CAUSES)
        return {
            "patient_id": patient["patient_id"],
            "death_date": death_date.isoformat(),
            "cause": cause,
        }
    else:
        return None

def generate_family_history(patient, min_fam=0, max_fam=3):
    n = random.randint(min_fam, max_fam)
    family = []
    for _ in range(n):
        relation = random.choice(FAMILY_RELATIONSHIPS)
        n_conditions = random.randint(1, 3)
        for _ in range(n_conditions):
            family.append({
                "patient_id": patient["patient_id"],
                "relation": relation,
                "condition": random.choice(CONDITION_NAMES),
            })
    return family

def load_yaml_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def print_and_save_report(report, report_file=None):
    print("\n=== Synthetic Data Summary Report ===")
    print(report)
    if report_file:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Synthetic Patient Data Generator")
    parser.add_argument("--num-records", type=int, default=1000, help="Number of patient records to generate")
    parser.add_argument("--output-dir", type=str, default=".", help="Directory to save output files")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--csv", action="store_true", help="Output CSV files only")
    parser.add_argument("--parquet", action="store_true", help="Output Parquet files only")
    parser.add_argument("--both", action="store_true", help="Output both CSV and Parquet files (default)")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config file")
    parser.add_argument("--report-file", type=str, default=None, help="Path to save summary report (optional)")
    args, unknown = parser.parse_known_args()

    config = {}
    if args.config:
        config = load_yaml_config(args.config)

    def get_config(key, default=None):
        # CLI flag overrides config file
        val = getattr(args, key, None)
        if val not in [None, False]:
            return val
        return config.get(key, default)

    num_records = int(get_config('num_records', 1000))
    output_dir = get_config('output_dir', '.')
    seed = get_config('seed', None)
    output_format = get_config('output_format', 'both')
    age_dist = get_config('age_dist', None)
    gender_dist = get_config('gender_dist', None)
    race_dist = get_config('race_dist', None)
    smoking_dist = get_config('smoking_dist', None)
    alcohol_dist = get_config('alcohol_dist', None)
    education_dist = get_config('education_dist', None)
    employment_dist = get_config('employment_dist', None)
    housing_dist = get_config('housing_dist', None)

    if seed is not None:
        random.seed(int(seed))
        Faker.seed(int(seed))

    os.makedirs(output_dir, exist_ok=True)

    # Determine output formats
    output_csv = output_format in ["csv", "both"]
    output_parquet = output_format in ["parquet", "both"]

    # Parse distributions
    age_bins = [(0, 18), (19, 40), (41, 65), (66, 120)]
    age_bin_labels = [f"{a}-{b}" for a, b in age_bins]
    age_dist = parse_distribution(age_dist, age_bin_labels, default_dist={l: 1/len(age_bin_labels) for l in age_bin_labels})
    gender_dist = parse_distribution(gender_dist, GENDERS, default_dist={g: 1/len(GENDERS) for g in GENDERS})
    race_dist = parse_distribution(race_dist, RACES, default_dist={r: 1/len(RACES) for r in RACES})
    smoking_dist = parse_distribution(smoking_dist, SDOH_SMOKING, default_dist={s: 1/len(SDOH_SMOKING) for s in SDOH_SMOKING})
    alcohol_dist = parse_distribution(alcohol_dist, SDOH_ALCOHOL, default_dist={a: 1/len(SDOH_ALCOHOL) for a in SDOH_ALCOHOL})
    education_dist = parse_distribution(education_dist, SDOH_EDUCATION, default_dist={e: 1/len(SDOH_EDUCATION) for e in SDOH_EDUCATION})
    employment_dist = parse_distribution(employment_dist, SDOH_EMPLOYMENT, default_dist={e: 1/len(SDOH_EMPLOYMENT) for e in SDOH_EMPLOYMENT})
    housing_dist = parse_distribution(housing_dist, SDOH_HOUSING, default_dist={h: 1/len(SDOH_HOUSING) for h in SDOH_HOUSING})

    def generate_patient_with_dist(_):
        # Age bin
        age_bin_label = sample_from_dist(age_dist)
        a_min, a_max = map(int, age_bin_label.split("-"))
        age = random.randint(a_min, a_max)
        birthdate = datetime.now().date() - timedelta(days=age * 365)
        patient_id = str(uuid.uuid4())
        income = random.randint(0, 200000) if age >= 18 else 0
        gender = sample_from_dist(gender_dist)
        race = sample_from_dist(race_dist)
        smoking_status = sample_from_dist(smoking_dist)
        alcohol_use = sample_from_dist(alcohol_dist)
        education = sample_from_dist(education_dist) if age >= 18 else "None"
        employment_status = sample_from_dist(employment_dist) if age >= 16 else "Student"
        housing_status = sample_from_dist(housing_dist)
        return {
            "patient_id": patient_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "gender": gender,
            "birthdate": birthdate.isoformat(),
            "age": age,
            "race": race,
            "ethnicity": random.choice(ETHNICITIES),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip": fake.zipcode(),
            "country": "US",
            "marital_status": random.choice(MARITAL_STATUSES),
            "language": random.choice(LANGUAGES),
            "insurance": random.choice(INSURANCES),
            "ssn": fake.ssn(),
            # SDOH fields
            "smoking_status": smoking_status,
            "alcohol_use": alcohol_use,
            "education": education,
            "employment_status": employment_status,
            "income": income,
            "housing_status": housing_status,
        }

    print(f"Generating {num_records} patients and related tables in parallel...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        patients = list(executor.map(generate_patient_with_dist, range(num_records)))

    all_encounters = []
    all_conditions = []
    all_medications = []
    all_allergies = []
    all_procedures = []
    all_immunizations = []
    all_observations = []
    all_deaths = []
    all_family_history = []

    for patient in patients:
        conditions = generate_conditions(patient, [], min_cond=1, max_cond=5)
        encounters = generate_encounters(patient, conditions)
        all_encounters.extend(encounters)
        for cond in conditions:
            enc = random.choice(encounters) if encounters else None
            cond["encounter_id"] = enc["encounter_id"] if enc else None
            cond["onset_date"] = enc["date"] if enc else patient["birthdate"]
        all_conditions.extend(conditions)
        all_medications.extend(generate_medications(patient, encounters, conditions))
        all_allergies.extend(generate_allergies(patient))
        all_procedures.extend(generate_procedures(patient, encounters))
        all_immunizations.extend(generate_immunizations(patient, encounters))
        all_observations.extend(generate_observations(patient, encounters, conditions))
        death = generate_death(patient, conditions)
        if death:
            all_deaths.append(death)
        all_family_history.extend(generate_family_history(patient))

    def save(df, name):
        if output_csv:
            df.write_csv(os.path.join(output_dir, f"{name}.csv"))
        if output_parquet:
            df.write_parquet(os.path.join(output_dir, f"{name}.parquet"))

    save(pl.DataFrame(patients), "patients")
    save(pl.DataFrame(all_encounters), "encounters")
    save(pl.DataFrame(all_conditions), "conditions")
    save(pl.DataFrame(all_medications), "medications")
    save(pl.DataFrame(all_allergies), "allergies")
    save(pl.DataFrame(all_procedures), "procedures")
    save(pl.DataFrame(all_immunizations), "immunizations")
    save(pl.DataFrame(all_observations), "observations")
    if all_deaths:
        save(pl.DataFrame(all_deaths), "deaths")
    if all_family_history:
        save(pl.DataFrame(all_family_history), "family_history")

    print(f"Done! Files written to {output_dir}: patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history (CSV and/or Parquet)")

    # Summary report
    import collections
    def value_counts(lst, bins=None):
        if bins:
            binned = collections.Counter()
            for v in lst:
                for label, (a, b) in bins.items():
                    if a <= v <= b:
                        binned[label] += 1
                        break
            return binned
        return collections.Counter(lst)

    age_bins_dict = {f"{a}-{b}": (a, b) for a, b in age_bins}
    patients_df = pl.DataFrame(patients)
    report_lines = []
    report_lines.append(f"Patients: {len(patients)}")
    report_lines.append(f"Encounters: {len(all_encounters)}")
    report_lines.append(f"Conditions: {len(all_conditions)}")
    report_lines.append(f"Medications: {len(all_medications)}")
    report_lines.append(f"Allergies: {len(all_allergies)}")
    report_lines.append(f"Procedures: {len(all_procedures)}")
    report_lines.append(f"Immunizations: {len(all_immunizations)}")
    report_lines.append(f"Observations: {len(all_observations)}")
    report_lines.append(f"Deaths: {len(all_deaths)}")
    report_lines.append(f"Family History: {len(all_family_history)}")
    report_lines.append("")
    # Age
    ages = patients_df['age'].to_list()
    age_counts = value_counts(ages, bins=age_bins_dict)
    report_lines.append("Age distribution:")
    for k, v in age_counts.items():
        report_lines.append(f"  {k}: {v}")
    # Gender
    report_lines.append("Gender distribution:")
    for k, v in value_counts(patients_df['gender'].to_list()).items():
        report_lines.append(f"  {k}: {v}")
    # Race
    report_lines.append("Race distribution:")
    for k, v in value_counts(patients_df['race'].to_list()).items():
        report_lines.append(f"  {k}: {v}")
    # SDOH fields
    for field, label in [
        ('smoking_status', 'Smoking'),
        ('alcohol_use', 'Alcohol'),
        ('education', 'Education'),
        ('employment_status', 'Employment'),
        ('housing_status', 'Housing')]:
        report_lines.append(f"{label} distribution:")
        for k, v in value_counts(patients_df[field].to_list()).items():
            report_lines.append(f"  {k}: {v}")
    # Top conditions
    cond_names = [c['name'] for c in all_conditions]
    cond_counts = value_counts(cond_names)
    report_lines.append("Top 10 conditions:")
    for k, v in cond_counts.most_common(10):
        report_lines.append(f"  {k}: {v}")
    report = "\n".join(report_lines)
    print_and_save_report(report, get_config('report_file', None))

if __name__ == "__main__":
    main() 