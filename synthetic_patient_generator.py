import polars as pl
from faker import Faker
import random
import concurrent.futures
import sys
from datetime import datetime, timedelta
import uuid
from collections import defaultdict

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

def main():
    try:
        n = int(input("How many synthetic patient records do you want to generate? "))
    except Exception:
        print("Invalid input. Please enter an integer.")
        sys.exit(1)

    print(f"Generating {n} patients and related tables in parallel...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        patients = list(executor.map(generate_patient, range(n)))

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
        # Assign conditions based on demographics/SDOH
        conditions = generate_conditions(patient, [], min_cond=1, max_cond=5)
        # Generate encounters based on conditions
        encounters = generate_encounters(patient, conditions)
        all_encounters.extend(encounters)
        # Re-link conditions to actual encounters
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

    # Output each table as CSV and Parquet
    pl.DataFrame(patients).write_csv("patients.csv")
    pl.DataFrame(patients).write_parquet("patients.parquet")
    pl.DataFrame(all_encounters).write_csv("encounters.csv")
    pl.DataFrame(all_encounters).write_parquet("encounters.parquet")
    pl.DataFrame(all_conditions).write_csv("conditions.csv")
    pl.DataFrame(all_conditions).write_parquet("conditions.parquet")
    pl.DataFrame(all_medications).write_csv("medications.csv")
    pl.DataFrame(all_medications).write_parquet("medications.parquet")
    pl.DataFrame(all_allergies).write_csv("allergies.csv")
    pl.DataFrame(all_allergies).write_parquet("allergies.parquet")
    pl.DataFrame(all_procedures).write_csv("procedures.csv")
    pl.DataFrame(all_procedures).write_parquet("procedures.parquet")
    pl.DataFrame(all_immunizations).write_csv("immunizations.csv")
    pl.DataFrame(all_immunizations).write_parquet("immunizations.parquet")
    pl.DataFrame(all_observations).write_csv("observations.csv")
    pl.DataFrame(all_observations).write_parquet("observations.parquet")
    if all_deaths:
        pl.DataFrame(all_deaths).write_csv("deaths.csv")
        pl.DataFrame(all_deaths).write_parquet("deaths.parquet")
    if all_family_history:
        pl.DataFrame(all_family_history).write_csv("family_history.csv")
        pl.DataFrame(all_family_history).write_parquet("family_history.parquet")
    print("Done! Files written: patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history (CSV and Parquet)")

if __name__ == "__main__":
    main() 