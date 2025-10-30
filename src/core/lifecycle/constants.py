"""Shared lifecycle generation constants."""
from __future__ import annotations

GENDERS = ["male", "female", "other"]
RACES = ["White", "Black", "Asian", "Hispanic", "Native American", "Other"]
ETHNICITIES = ["Not Hispanic or Latino", "Hispanic or Latino"]
MARITAL_STATUSES = ["Never Married", "Married", "Divorced", "Widowed", "Separated"]
LANGUAGES = ["English", "Spanish", "Chinese", "French", "German", "Vietnamese"]
INSURANCES = ["Medicare", "Medicaid", "Private", "Uninsured"]
ENCOUNTER_TYPES = [
    "Wellness Visit",
    "Primary Care Follow-up",
    "Cardiology Clinic",
    "Endocrinology Follow-up",
    "Pulmonology Clinic",
    "Behavioral Health Session",
    "Neurology Clinic",
    "Dermatology Clinic",
    "Gastroenterology Consult",
    "Orthopedic Visit",
    "Rehabilitation Therapy",
    "Pediatric Visit",
    "Obstetrics Prenatal Visit",
    "Oncology Visit",
    "Urgent Care Visit",
    "Emergency Department Visit",
    "Telehealth Check-in",
    "Laboratory Workup",
    "Imaging Study",
    "Surgery",
]
ENCOUNTER_REASONS = [
    "Preventive care",
    "Injury",
    "Acute illness",
    "Chronic disease management",
    "Medication review",
    "Vaccination",
    "Mental health follow-up",
    "Pregnancy care",
    "Rehabilitation session",
    "Diagnostic imaging",
    "Post-surgical follow-up",
    "Specialty consultation",
    "Lab monitoring",
]
CONDITION_STATUSES = ["active", "resolved", "remission"]

SDOH_SMOKING = ["Never", "Former", "Current"]
SDOH_ALCOHOL = ["Never", "Occasional", "Regular", "Heavy"]
SDOH_EDUCATION = ["None", "Primary", "Secondary", "High School", "Associate", "Bachelor", "Master", "Doctorate"]
SDOH_EMPLOYMENT = ["Unemployed", "Employed", "Student", "Retired", "Disabled"]
SDOH_HOUSING = ["Stable", "Homeless", "Temporary", "Assisted Living"]

MAX_PATIENT_AGE = 95

AGE_BINS = [(0, 18), (19, 40), (41, 65), (66, MAX_PATIENT_AGE)]
AGE_BIN_LABELS = [f"{a}-{b}" for a, b in AGE_BINS]
