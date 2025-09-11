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
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from tqdm import tqdm

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
# PHASE 2: Comprehensive laboratory panels with clinical accuracy
COMPREHENSIVE_LAB_PANELS = {
    "Basic_Metabolic_Panel": {
        "tests": [
            {"name": "Sodium", "loinc": "2951-2", "units": "mmol/L", "normal_range": (136, 145), "critical_low": 120, "critical_high": 160},
            {"name": "Potassium", "loinc": "2823-3", "units": "mmol/L", "normal_range": (3.5, 5.1), "critical_low": 2.5, "critical_high": 6.5},
            {"name": "Chloride", "loinc": "2075-0", "units": "mmol/L", "normal_range": (98, 107), "critical_low": 80, "critical_high": 120},
            {"name": "CO2", "loinc": "2028-9", "units": "mmol/L", "normal_range": (22, 28), "critical_low": 15, "critical_high": 40},
            {"name": "BUN", "loinc": "3094-0", "units": "mg/dL", "normal_range": (7, 20), "critical_low": None, "critical_high": 100},
            {"name": "Creatinine", "loinc": "2160-0", "units": "mg/dL", "normal_range": (0.7, 1.3), "critical_low": None, "critical_high": 10},
            {"name": "Glucose", "loinc": "2345-7", "units": "mg/dL", "normal_range": (70, 99), "critical_low": 40, "critical_high": 500},
            {"name": "eGFR", "loinc": "33914-3", "units": "mL/min/1.73m²", "normal_range": (90, 120), "critical_low": 15, "critical_high": None}
        ],
        "frequency": "routine",
        "indications": ["routine_screening", "kidney_function", "electrolyte_monitoring"]
    },
    
    "Complete_Blood_Count": {
        "tests": [
            {"name": "WBC", "loinc": "6690-2", "units": "K/uL", "normal_range": (4.5, 11.0), "critical_low": 1.0, "critical_high": 30.0},
            {"name": "RBC", "loinc": "789-8", "units": "M/uL", "normal_range": (4.2, 5.4), "critical_low": 2.0, "critical_high": 7.0},
            {"name": "Hemoglobin", "loinc": "718-7", "units": "g/dL", "normal_range": (12.0, 15.5), "critical_low": 5.0, "critical_high": 20.0},
            {"name": "Hematocrit", "loinc": "4544-3", "units": "%", "normal_range": (36.0, 46.0), "critical_low": 15.0, "critical_high": 60.0},
            {"name": "Platelets", "loinc": "777-3", "units": "K/uL", "normal_range": (150, 450), "critical_low": 20, "critical_high": 1000},
            {"name": "MCV", "loinc": "787-2", "units": "fL", "normal_range": (80, 100), "critical_low": None, "critical_high": None},
            {"name": "MCH", "loinc": "785-6", "units": "pg", "normal_range": (27, 32), "critical_low": None, "critical_high": None},
            {"name": "MCHC", "loinc": "786-4", "units": "g/dL", "normal_range": (32, 36), "critical_low": None, "critical_high": None}
        ],
        "frequency": "routine",
        "indications": ["anemia_workup", "bleeding_disorders", "infection_monitoring", "routine_screening"]
    },
    
    "Lipid_Panel": {
        "tests": [
            {"name": "Total_Cholesterol", "loinc": "2093-3", "units": "mg/dL", "normal_range": (125, 200), "critical_low": None, "critical_high": 500},
            {"name": "HDL_Cholesterol", "loinc": "2085-9", "units": "mg/dL", "normal_range": (40, 60), "critical_low": None, "critical_high": None},
            {"name": "LDL_Cholesterol", "loinc": "2089-1", "units": "mg/dL", "normal_range": (0, 100), "critical_low": None, "critical_high": 400},
            {"name": "Triglycerides", "loinc": "2571-8", "units": "mg/dL", "normal_range": (0, 150), "critical_low": None, "critical_high": 1000},
            {"name": "Non_HDL_Cholesterol", "loinc": "13457-7", "units": "mg/dL", "normal_range": (0, 130), "critical_low": None, "critical_high": None}
        ],
        "frequency": "annual",
        "indications": ["cardiovascular_risk", "diabetes_monitoring", "statin_therapy"]
    },
    
    "Liver_Function_Panel": {
        "tests": [
            {"name": "ALT", "loinc": "1742-6", "units": "U/L", "normal_range": (7, 56), "critical_low": None, "critical_high": 1000},
            {"name": "AST", "loinc": "1920-8", "units": "U/L", "normal_range": (10, 40), "critical_low": None, "critical_high": 1000},
            {"name": "Alkaline_Phosphatase", "loinc": "6768-6", "units": "U/L", "normal_range": (44, 147), "critical_low": None, "critical_high": 1000},
            {"name": "Total_Bilirubin", "loinc": "1975-2", "units": "mg/dL", "normal_range": (0.3, 1.2), "critical_low": None, "critical_high": 20},
            {"name": "Direct_Bilirubin", "loinc": "1968-7", "units": "mg/dL", "normal_range": (0.0, 0.4), "critical_low": None, "critical_high": None},
            {"name": "Albumin", "loinc": "1751-7", "units": "g/dL", "normal_range": (3.5, 5.0), "critical_low": 2.0, "critical_high": None}
        ],
        "frequency": "as_needed",
        "indications": ["liver_disease", "medication_monitoring", "hepatitis_screening"]
    },
    
    "Thyroid_Function": {
        "tests": [
            {"name": "TSH", "loinc": "3016-3", "units": "mIU/L", "normal_range": (0.27, 4.20), "critical_low": 0.01, "critical_high": 100},
            {"name": "Free_T4", "loinc": "3024-7", "units": "ng/dL", "normal_range": (0.93, 1.70), "critical_low": 0.2, "critical_high": 7.0},
            {"name": "Free_T3", "loinc": "3051-0", "units": "pg/mL", "normal_range": (2.0, 4.4), "critical_low": None, "critical_high": None}
        ],
        "frequency": "annual",
        "indications": ["thyroid_disorders", "fatigue_workup", "weight_changes"]
    },
    
    "Diabetes_Monitoring": {
        "tests": [
            {"name": "Hemoglobin_A1c", "loinc": "4548-4", "units": "%", "normal_range": (4.0, 5.6), "critical_low": None, "critical_high": 15},
            {"name": "Fasting_Glucose", "loinc": "1558-6", "units": "mg/dL", "normal_range": (70, 99), "critical_low": 40, "critical_high": 500},
            {"name": "Random_Glucose", "loinc": "2345-7", "units": "mg/dL", "normal_range": (70, 140), "critical_low": 40, "critical_high": 500},
            {"name": "Microalbumin", "loinc": "14957-5", "units": "mg/g", "normal_range": (0, 30), "critical_low": None, "critical_high": None}
        ],
        "frequency": "quarterly",
        "indications": ["diabetes_management", "prediabetes_screening"]
    },
    
    "Cardiac_Markers": {
        "tests": [
            {"name": "Troponin_I", "loinc": "10839-9", "units": "ng/mL", "normal_range": (0.0, 0.04), "critical_low": None, "critical_high": 50},
            {"name": "CK_MB", "loinc": "13969-1", "units": "ng/mL", "normal_range": (0.0, 6.3), "critical_low": None, "critical_high": 300},
            {"name": "BNP", "loinc": "30934-4", "units": "pg/mL", "normal_range": (0, 100), "critical_low": None, "critical_high": 5000},
            {"name": "NT_proBNP", "loinc": "33762-6", "units": "pg/mL", "normal_range": (0, 125), "critical_low": None, "critical_high": 35000}
        ],
        "frequency": "acute",
        "indications": ["chest_pain", "heart_failure", "myocardial_infarction"]
    },
    
    "Inflammatory_Markers": {
        "tests": [
            {"name": "ESR", "loinc": "4537-7", "units": "mm/hr", "normal_range": (0, 30), "critical_low": None, "critical_high": 150},
            {"name": "CRP", "loinc": "1988-5", "units": "mg/L", "normal_range": (0.0, 3.0), "critical_low": None, "critical_high": 500},
            {"name": "Procalcitonin", "loinc": "33747-0", "units": "ng/mL", "normal_range": (0.0, 0.25), "critical_low": None, "critical_high": 100}
        ],
        "frequency": "as_needed",
        "indications": ["infection", "inflammation", "sepsis_workup"]
    }
}

# Age and gender-specific reference range adjustments
AGE_GENDER_ADJUSTMENTS = {
    "Hemoglobin": {
        "male": {"normal_range": (13.5, 17.5)},
        "female": {"normal_range": (12.0, 15.5)},
        "pediatric": {"normal_range": (11.0, 14.0)}
    },
    "Hematocrit": {
        "male": {"normal_range": (41.0, 50.0)},
        "female": {"normal_range": (36.0, 46.0)},
        "pediatric": {"normal_range": (32.0, 42.0)}
    },
    "Creatinine": {
        "male": {"normal_range": (0.9, 1.3)},
        "female": {"normal_range": (0.7, 1.1)},
        "elderly": {"normal_range": (0.8, 1.4)}
    },
    "eGFR": {
        "elderly": {"normal_range": (60, 89)},
        "adult": {"normal_range": (90, 120)}
    }
}

# PHASE 2: Condition complexity modeling with staging and complications
CONDITION_COMPLEXITY_MODELS = {
    "Diabetes": {
        "stages": {
            "Prediabetes": {
                "criteria": {"hba1c_range": (5.7, 6.4), "fasting_glucose_range": (100, 125)},
                "complications": [],
                "medications": ["lifestyle_modification"],
                "monitoring": ["Diabetes_Monitoring"]
            },
            "Type_2_Diabetes_Early": {
                "criteria": {"hba1c_range": (6.5, 8.0), "years_since_diagnosis": (0, 5)},
                "complications": ["Microalbuminuria"],
                "medications": ["Metformin"],
                "monitoring": ["Diabetes_Monitoring", "Basic_Metabolic_Panel"]
            },
            "Type_2_Diabetes_Established": {
                "criteria": {"hba1c_range": (7.0, 10.0), "years_since_diagnosis": (5, 15)},
                "complications": ["Diabetic_Nephropathy", "Diabetic_Retinopathy", "Peripheral_Neuropathy"],
                "medications": ["Metformin", "Insulin", "Glipizide"],
                "monitoring": ["Diabetes_Monitoring", "Basic_Metabolic_Panel", "Lipid_Panel"]
            },
            "Type_2_Diabetes_Advanced": {
                "criteria": {"hba1c_range": (8.5, 15.0), "years_since_diagnosis": (15, 30)},
                "complications": ["End_Stage_Renal_Disease", "Diabetic_Foot_Ulcer", "Coronary_Artery_Disease"],
                "medications": ["Insulin", "multiple_agents"],
                "monitoring": ["Diabetes_Monitoring", "Cardiac_Markers", "Complete_Blood_Count"]
            }
        },
        "complications": {
            "Diabetic_Nephropathy": {"icd10": "E11.21", "progression_risk": 0.3},
            "Diabetic_Retinopathy": {"icd10": "E11.311", "progression_risk": 0.25},
            "Peripheral_Neuropathy": {"icd10": "E11.40", "progression_risk": 0.4},
            "Diabetic_Foot_Ulcer": {"icd10": "E11.621", "progression_risk": 0.15},
            "End_Stage_Renal_Disease": {"icd10": "N18.6", "progression_risk": 0.1}
        }
    },
    
    "Cancer": {
        "staging": {
            "TNM_Stage_I": {
                "criteria": {"tumor_size": "small", "lymph_nodes": "negative", "metastasis": "none"},
                "prognosis": "excellent",
                "treatment": ["surgery", "radiation"],
                "survival_5yr": 0.90
            },
            "TNM_Stage_II": {
                "criteria": {"tumor_size": "moderate", "lymph_nodes": "limited", "metastasis": "none"},
                "prognosis": "good", 
                "treatment": ["surgery", "chemotherapy", "radiation"],
                "survival_5yr": 0.75
            },
            "TNM_Stage_III": {
                "criteria": {"tumor_size": "large", "lymph_nodes": "extensive", "metastasis": "regional"},
                "prognosis": "fair",
                "treatment": ["chemotherapy", "radiation", "surgery"],
                "survival_5yr": 0.45
            },
            "TNM_Stage_IV": {
                "criteria": {"tumor_size": "any", "lymph_nodes": "any", "metastasis": "distant"},
                "prognosis": "poor",
                "treatment": ["palliative_chemotherapy", "supportive_care"],
                "survival_5yr": 0.15
            }
        },
        "subtypes": {
            "Breast_Cancer": {"icd10": "C50.911", "common_staging": ["TNM_Stage_I", "TNM_Stage_II"]},
            "Lung_Cancer": {"icd10": "C78.00", "common_staging": ["TNM_Stage_III", "TNM_Stage_IV"]},
            "Colon_Cancer": {"icd10": "C18.9", "common_staging": ["TNM_Stage_II", "TNM_Stage_III"]},
            "Prostate_Cancer": {"icd10": "C61", "common_staging": ["TNM_Stage_I", "TNM_Stage_II"]},
            "Pancreatic_Cancer": {"icd10": "C25.9", "common_staging": ["TNM_Stage_III", "TNM_Stage_IV"]}
        }
    },
    
    "Heart_Disease": {
        "risk_stratification": {
            "Low_Risk": {
                "criteria": {"framingham_score": (0, 10), "ejection_fraction": (55, 70)},
                "medications": ["lifestyle_modification", "statin"],
                "monitoring": ["Lipid_Panel"],
                "procedures": ["stress_test"]
            },
            "Moderate_Risk": {
                "criteria": {"framingham_score": (10, 20), "ejection_fraction": (40, 54)},
                "medications": ["statin", "ace_inhibitor", "beta_blocker"],
                "monitoring": ["Lipid_Panel", "Cardiac_Markers"],
                "procedures": ["echocardiogram", "cardiac_catheterization"]
            },
            "High_Risk": {
                "criteria": {"framingham_score": (20, 100), "ejection_fraction": (30, 39)},
                "medications": ["multiple_agents", "antiplatelet"],
                "monitoring": ["Cardiac_Markers", "Inflammatory_Markers"],
                "procedures": ["PCI", "CABG"]
            },
            "Heart_Failure": {
                "criteria": {"ejection_fraction": (0, 29), "nyha_class": (3, 4)},
                "medications": ["ace_inhibitor", "beta_blocker", "diuretic"],
                "monitoring": ["Cardiac_Markers", "Basic_Metabolic_Panel"],
                "procedures": ["device_therapy", "transplant_evaluation"]
            }
        },
        "complications": {
            "Myocardial_Infarction": {"icd10": "I21.9", "risk_factor": 3.0},
            "Heart_Failure": {"icd10": "I50.9", "risk_factor": 2.5},
            "Atrial_Fibrillation": {"icd10": "I48.91", "risk_factor": 1.8},
            "Stroke": {"icd10": "I64", "risk_factor": 2.2}
        }
    },
    
    "Hypertension": {
        "stages": {
            "Stage_1": {
                "criteria": {"systolic": (130, 139), "diastolic": (80, 89)},
                "medications": ["lifestyle_modification"],
                "target": {"systolic": 130, "diastolic": 80}
            },
            "Stage_2": {
                "criteria": {"systolic": (140, 179), "diastolic": (90, 119)},
                "medications": ["ace_inhibitor", "thiazide_diuretic"],
                "target": {"systolic": 130, "diastolic": 80}
            },
            "Hypertensive_Crisis": {
                "criteria": {"systolic": (180, 250), "diastolic": (120, 150)},
                "medications": ["multiple_agents", "emergency_treatment"],
                "target": {"systolic": 140, "diastolic": 90}
            }
        },
        "complications": {
            "Left_Ventricular_Hypertrophy": {"icd10": "I51.7", "risk": 0.3},
            "Chronic_Kidney_Disease": {"icd10": "N18.9", "risk": 0.25},
            "Retinopathy": {"icd10": "H35.039", "risk": 0.2}
        }
    }
}

# Enhanced procedure-condition relationships with CPT codes
CLINICAL_PROCEDURES = {
    "Cardiovascular": {
        "diagnostic": [
            {"name": "Echocardiogram", "cpt": "93306", "conditions": ["Heart_Disease", "Heart_Failure", "Hypertension"], "complexity": "routine"},
            {"name": "Cardiac_Catheterization", "cpt": "93458", "conditions": ["Coronary_Artery_Disease", "Myocardial_Infarction"], "complexity": "high"},
            {"name": "Stress_Test", "cpt": "93017", "conditions": ["Chest_Pain", "Coronary_Artery_Disease"], "complexity": "routine"},
            {"name": "Holter_Monitor", "cpt": "93224", "conditions": ["Arrhythmia", "Atrial_Fibrillation"], "complexity": "routine"},
            {"name": "CT_Angiography", "cpt": "75571", "conditions": ["Coronary_Artery_Disease", "Peripheral_Artery_Disease"], "complexity": "moderate"}
        ],
        "therapeutic": [
            {"name": "Percutaneous_Coronary_Intervention", "cpt": "92928", "conditions": ["STEMI", "NSTEMI", "Unstable_Angina"], "complexity": "high"},
            {"name": "Coronary_Artery_Bypass", "cpt": "33533", "conditions": ["Multivessel_CAD", "Left_Main_Disease"], "complexity": "very_high"},
            {"name": "Pacemaker_Insertion", "cpt": "33206", "conditions": ["Heart_Block", "Bradycardia"], "complexity": "high"},
            {"name": "ICD_Implantation", "cpt": "33249", "conditions": ["Heart_Failure", "Ventricular_Arrhythmia"], "complexity": "high"}
        ]
    },
    
    "Endocrinology": {
        "diagnostic": [
            {"name": "Glucose_Tolerance_Test", "cpt": "82951", "conditions": ["Prediabetes", "Gestational_Diabetes"], "complexity": "routine"},
            {"name": "Thyroid_Ultrasound", "cpt": "76536", "conditions": ["Thyroid_Nodule", "Hyperthyroidism"], "complexity": "routine"},
            {"name": "Diabetic_Eye_Exam", "cpt": "92012", "conditions": ["Diabetes", "Diabetic_Retinopathy"], "complexity": "routine"}
        ],
        "therapeutic": [
            {"name": "Insulin_Pump_Insertion", "cpt": "95990", "conditions": ["Type_1_Diabetes", "Brittle_Diabetes"], "complexity": "moderate"},
            {"name": "Continuous_Glucose_Monitor", "cpt": "95249", "conditions": ["Diabetes", "Hypoglycemia"], "complexity": "routine"}
        ]
    },
    
    "Oncology": {
        "diagnostic": [
            {"name": "CT_Chest_Abdomen_Pelvis", "cpt": "71250", "conditions": ["Cancer", "Metastatic_Disease"], "complexity": "routine"},
            {"name": "PET_Scan", "cpt": "78815", "conditions": ["Cancer", "Staging"], "complexity": "moderate"},
            {"name": "Bone_Marrow_Biopsy", "cpt": "38221", "conditions": ["Leukemia", "Lymphoma"], "complexity": "moderate"},
            {"name": "Tumor_Biopsy", "cpt": "19083", "conditions": ["Breast_Mass", "Lung_Nodule"], "complexity": "moderate"}
        ],
        "therapeutic": [
            {"name": "Chemotherapy_Administration", "cpt": "96413", "conditions": ["Active_Cancer"], "complexity": "moderate"},
            {"name": "Radiation_Therapy", "cpt": "77301", "conditions": ["Localized_Cancer"], "complexity": "moderate"},
            {"name": "Tumor_Resection", "cpt": "19301", "conditions": ["Breast_Cancer", "Lung_Cancer"], "complexity": "high"}
        ]
    },
    
    "Gastroenterology": {
        "diagnostic": [
            {"name": "Colonoscopy", "cpt": "45378", "conditions": ["Colorectal_Screening", "GI_Bleeding", "IBD"], "complexity": "routine"},
            {"name": "Upper_Endoscopy", "cpt": "43235", "conditions": ["GERD", "Peptic_Ulcer", "GI_Bleeding"], "complexity": "routine"},
            {"name": "ERCP", "cpt": "43260", "conditions": ["Pancreatic_Disease", "Biliary_Obstruction"], "complexity": "high"}
        ],
        "therapeutic": [
            {"name": "Polypectomy", "cpt": "45385", "conditions": ["Colon_Polyps"], "complexity": "routine"},
            {"name": "Variceal_Banding", "cpt": "43244", "conditions": ["Esophageal_Varices", "Cirrhosis"], "complexity": "moderate"}
        ]
    }
}

# Backward compatibility - simplified observation types for legacy functions
OBSERVATION_TYPES = ["Height", "Weight", "Blood Pressure", "Heart Rate", "Temperature", "Hemoglobin A1c", "Cholesterol"]

SDOH_SMOKING = ["Never", "Former", "Current"]
SDOH_ALCOHOL = ["Never", "Occasional", "Regular", "Heavy"]
SDOH_EDUCATION = ["None", "Primary", "Secondary", "High School", "Associate", "Bachelor", "Master", "Doctorate"]
SDOH_EMPLOYMENT = ["Unemployed", "Employed", "Student", "Retired", "Disabled"]
SDOH_HOUSING = ["Stable", "Homeless", "Temporary", "Assisted Living"]

# PHASE 1: Expanded death causes with ICD-10-CM coding and age stratification
DEATH_CAUSES_BY_AGE = {
    # Neonatal/Infant deaths (0-1 years)
    (0, 1): [
        {"icd10": "P07.30", "description": "Extremely low birth weight newborn, unspecified weight", "weight": 15},
        {"icd10": "Q24.9", "description": "Congenital malformation of heart, unspecified", "weight": 12},
        {"icd10": "P22.0", "description": "Respiratory distress syndrome of newborn", "weight": 10},
        {"icd10": "P36.9", "description": "Bacterial sepsis of newborn, unspecified", "weight": 8},
        {"icd10": "R95", "description": "Sudden infant death syndrome", "weight": 5}
    ],
    
    # Pediatric deaths (1-14 years)  
    (1, 14): [
        {"icd10": "W87.XXXA", "description": "Exposure to unspecified electric current, initial encounter", "weight": 15},
        {"icd10": "V43.52XA", "description": "Car passenger injured in collision with car in traffic accident, initial encounter", "weight": 12},
        {"icd10": "C95.90", "description": "Leukemia, unspecified of unspecified cell type not having achieved remission", "weight": 10},
        {"icd10": "Q90.9", "description": "Down syndrome, unspecified", "weight": 8},
        {"icd10": "W65.XXXA", "description": "Drowning and submersion while in bathtub, initial encounter", "weight": 7},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 5}
    ],
    
    # Young adult deaths (15-34 years)
    (15, 34): [
        {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 20},
        {"icd10": "V43.52XA", "description": "Car passenger injured in collision with car in traffic accident, initial encounter", "weight": 18},
        {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 15},
        {"icd10": "X95.XXXA", "description": "Assault by other and unspecified firearm discharge, initial encounter", "weight": 12},
        {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 8},
        {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 7},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 5}
    ],
    
    # Middle-aged deaths (35-64 years)
    (35, 64): [
        {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 25},
        {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 20},
        {"icd10": "K72.90", "description": "Hepatic failure, unspecified without coma", "weight": 12},
        {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 10},
        {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 8},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 8},
        {"icd10": "E14.9", "description": "Unspecified diabetes mellitus with unspecified complications", "weight": 7},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 5},
        {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 5}
    ],
    
    # Elderly deaths (65+ years)
    (65, 120): [
        {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 30},
        {"icd10": "C78.00", "description": "Secondary malignant neoplasm of unspecified lung", "weight": 25},
        {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 15},
        {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 12},
        {"icd10": "G30.9", "description": "Alzheimer disease, unspecified", "weight": 10},
        {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 8},
        {"icd10": "J18.9", "description": "Pneumonia, unspecified organism", "weight": 8},
        {"icd10": "N18.6", "description": "End stage renal disease", "weight": 7},
        {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 5},
        {"icd10": "U07.1", "description": "COVID-19", "weight": 10}
    ]
}

# Condition-specific death cause mappings with ICD-10-CM codes
CONDITION_MORTALITY_RISK = {
    "Hypertension": {
        "relative_risk": 1.3,
        "likely_deaths": [
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 40},
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 30},
            {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 20},
            {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 10}
        ]
    },
    "Diabetes": {
        "relative_risk": 1.8,
        "likely_deaths": [
            {"icd10": "E14.9", "description": "Unspecified diabetes mellitus with unspecified complications", "weight": 30},
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 25},
            {"icd10": "N18.6", "description": "End stage renal disease", "weight": 20},
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 15},
            {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 10}
        ]
    },
    "Cancer": {
        "relative_risk": 3.5,
        "likely_deaths": [
            {"icd10": "C80.1", "description": "Malignant neoplasm, unspecified", "weight": 40},
            {"icd10": "C78.00", "description": "Secondary malignant neoplasm of unspecified lung", "weight": 30},
            {"icd10": "C25.9", "description": "Malignant neoplasm of pancreas, unspecified", "weight": 15},
            {"icd10": "C50.911", "description": "Malignant neoplasm of unspecified site of right female breast", "weight": 15}
        ]
    },
    "Heart Disease": {
        "relative_risk": 2.2,
        "likely_deaths": [
            {"icd10": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "weight": 35},
            {"icd10": "I21.9", "description": "Acute myocardial infarction, unspecified", "weight": 30},
            {"icd10": "I50.9", "description": "Heart failure, unspecified", "weight": 25},
            {"icd10": "I46.9", "description": "Cardiac arrest, cause unspecified", "weight": 10}
        ]
    },
    "COPD": {
        "relative_risk": 2.0,
        "likely_deaths": [
            {"icd10": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "weight": 50},
            {"icd10": "J44.1", "description": "Chronic obstructive pulmonary disease with acute exacerbation", "weight": 30},
            {"icd10": "J80", "description": "Acute respiratory distress syndrome", "weight": 20}
        ]
    },
    "Depression": {
        "relative_risk": 1.5,
        "likely_deaths": [
            {"icd10": "X83.8XXA", "description": "Intentional self-harm by other specified means, initial encounter", "weight": 60},
            {"icd10": "X84.XXXA", "description": "Intentional self-harm by unspecified means, initial encounter", "weight": 30},
            {"icd10": "X44.XXXA", "description": "Accidental poisoning by and exposure to other and unspecified drugs, initial encounter", "weight": 10}
        ]
    },
    "Stroke": {
        "relative_risk": 2.5,
        "likely_deaths": [
            {"icd10": "I64", "description": "Stroke, not specified as hemorrhage or infarction", "weight": 70},
            {"icd10": "I61.9", "description": "Nontraumatic intracerebral hemorrhage, unspecified", "weight": 20},
            {"icd10": "I63.9", "description": "Cerebral infarction, unspecified", "weight": 10}
        ]
    },
    "Alzheimer's": {
        "relative_risk": 2.8,
        "likely_deaths": [
            {"icd10": "G30.9", "description": "Alzheimer disease, unspecified", "weight": 80},
            {"icd10": "J18.9", "description": "Pneumonia, unspecified organism", "weight": 15},
            {"icd10": "A41.9", "description": "Sepsis, unspecified organism", "weight": 5}
        ]
    }
}

FAMILY_RELATIONSHIPS = ["Mother", "Father", "Sibling"]

# Migration simulation constants
MIGRATION_STAGES = ["extract", "transform", "validate", "load"]
ETL_SUBSTAGES = {
    "extract": ["connect", "query", "export"],
    "transform": ["parse", "map", "standardize"],
    "validate": ["schema_check", "business_rules", "data_integrity"],
    "load": ["staging", "production", "verification"]
}
FAILURE_TYPES = [
    "network_timeout", "data_corruption", "mapping_error", "validation_failure", 
    "resource_exhaustion", "security_violation", "system_unavailable"
]

# Basic terminology mappings for Phase 1
TERMINOLOGY_MAPPINGS = {
    'conditions': {
        'Diabetes': {
            'icd10': 'E11.9',
            'snomed': '44054006'
        },
        'Hypertension': {
            'icd10': 'I10',
            'snomed': '38341003'
        },
        'Asthma': {
            'icd10': 'J45.9',
            'snomed': '195967001'
        },
        'COPD': {
            'icd10': 'J44.1',
            'snomed': '13645005'
        },
        'Heart Disease': {
            'icd10': 'I25.9',
            'snomed': '53741008'
        },
        'Depression': {
            'icd10': 'F32.9',
            'snomed': '35489007'
        },
        'Anxiety': {
            'icd10': 'F41.9',
            'snomed': '48694002'
        }
    },
    'medications': {
        'Metformin': {
            'rxnorm': '6809',
            'ndc': '00093-1087-01'
        },
        'Lisinopril': {
            'rxnorm': '29046',
            'ndc': '00093-2744-01'
        },
        'Atorvastatin': {
            'rxnorm': '83367',
            'ndc': '00071-0155-23'
        },
        'Albuterol': {
            'rxnorm': '1154602',
            'ndc': '00173-0682-26'
        },
        'Insulin': {
            'rxnorm': '51428',
            'ndc': '00088-2220-33'
        }
    }
}

@dataclass
class PatientRecord:
    """Enhanced patient record with multiple healthcare identifiers and metadata"""
    
    # Core identifiers
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vista_id: Optional[str] = None
    mrn: Optional[str] = None
    ssn: Optional[str] = None
    
    # Demographics
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    gender: str = ""
    birthdate: str = ""
    age: int = 0
    race: str = ""
    ethnicity: str = ""
    
    # Address
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "US"
    
    # Contact and administrative
    phone: str = ""
    email: str = ""
    marital_status: str = ""
    language: str = ""
    insurance: str = ""
    
    # SDOH fields
    smoking_status: str = ""
    alcohol_use: str = ""
    education: str = ""
    employment_status: str = ""
    income: int = 0
    housing_status: str = ""
    
    # Clinical data containers
    encounters: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    medications: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    immunizations: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata for migration simulation
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        'source_system': 'synthetic',
        'migration_status': 'pending',
        'data_quality_score': 1.0,
        'created_timestamp': datetime.now().isoformat()
    })
    
    def generate_vista_id(self) -> str:
        """Generate VistA-style patient identifier (simple version for Phase 1)"""
        if not self.vista_id:
            self.vista_id = str(random.randint(1, 9999999))
        return self.vista_id
    
    def generate_mrn(self) -> str:
        """Generate Medical Record Number"""
        if not self.mrn:
            self.mrn = f"MRN{random.randint(100000, 999999)}"
        return self.mrn
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return {
            'patient_id': self.patient_id,
            'vista_id': self.vista_id,
            'mrn': self.mrn,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'gender': self.gender,
            'birthdate': self.birthdate,
            'age': self.age,
            'race': self.race,
            'ethnicity': self.ethnicity,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'country': self.country,
            'phone': self.phone,
            'email': self.email,
            'marital_status': self.marital_status,
            'language': self.language,
            'insurance': self.insurance,
            'ssn': self.ssn,
            'smoking_status': self.smoking_status,
            'alcohol_use': self.alcohol_use,
            'education': self.education,
            'employment_status': self.employment_status,
            'income': self.income,
            'housing_status': self.housing_status,
        }

# Migration Simulation Classes

@dataclass
class MigrationStageResult:
    """Result of a migration stage execution"""
    stage: str
    substage: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    data_quality_impact: float = 0.0
    
    def __post_init__(self):
        if self.start_time and self.end_time:
            self.duration_seconds = (self.end_time - self.start_time).total_seconds()

@dataclass
class BatchMigrationStatus:
    """Migration status for a batch of patients"""
    batch_id: str
    batch_size: int
    source_system: str = "vista"
    target_system: str = "oracle_health"
    migration_strategy: str = "staged"  # staged, big_bang, parallel
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_stage: str = "pending"
    stage_results: List[MigrationStageResult] = field(default_factory=list)
    patient_statuses: Dict[str, str] = field(default_factory=dict)
    overall_success_rate: float = 0.0
    average_quality_score: float = 1.0
    total_errors: int = 0
    
    def get_stage_result(self, stage: str, substage: Optional[str] = None) -> Optional[MigrationStageResult]:
        """Get result for a specific stage/substage"""
        for result in self.stage_results:
            if result.stage == stage and result.substage == substage:
                return result
        return None
    
    def calculate_metrics(self):
        """Calculate overall migration metrics"""
        if self.stage_results:
            successful_stages = sum(1 for r in self.stage_results if r.status == "completed")
            self.overall_success_rate = successful_stages / len(self.stage_results)
            self.total_errors = sum(r.records_failed for r in self.stage_results)

@dataclass
class MigrationConfig:
    """Configuration for migration simulation"""
    # Stage success rates (0.0-1.0)
    stage_success_rates: Dict[str, float] = field(default_factory=lambda: {
        "extract": 0.98,
        "transform": 0.95,
        "validate": 0.92,
        "load": 0.90
    })
    
    # Substage success rates
    substage_success_rates: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "extract": {"connect": 0.99, "query": 0.98, "export": 0.97},
        "transform": {"parse": 0.98, "map": 0.95, "standardize": 0.93},
        "validate": {"schema_check": 0.96, "business_rules": 0.92, "data_integrity": 0.89},
        "load": {"staging": 0.95, "production": 0.88, "verification": 0.92}
    })
    
    # Timing configurations (seconds)
    stage_base_duration: Dict[str, float] = field(default_factory=lambda: {
        "extract": 2.5,
        "transform": 4.0,
        "validate": 3.5,
        "load": 5.0
    })
    
    # Duration variance (multiplier)
    duration_variance: float = 0.3
    
    # Data quality degradation per failure
    quality_degradation_per_failure: float = 0.15
    quality_degradation_per_success: float = 0.02  # Slight degradation even on success
    
    # Network and system simulation
    network_failure_rate: float = 0.05
    system_overload_rate: float = 0.03
    data_corruption_rate: float = 0.01
    
    # Batch processing parameters
    max_concurrent_patients: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0

class MigrationSimulator:
    """
    Comprehensive migration simulator for VistA-to-Oracle Health transitions.
    
    This class simulates realistic healthcare data migration scenarios including:
    - Multi-stage ETL pipeline execution
    - Realistic failure injection and error handling  
    - Data quality degradation tracking
    - Patient and batch-level status monitoring
    - Migration analytics and reporting
    """
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or MigrationConfig()
        self.fake = Faker()
        self.migration_history: List[BatchMigrationStatus] = []
        self.current_batch: Optional[BatchMigrationStatus] = None
        
    def simulate_staged_migration(
        self, 
        patients: List[PatientRecord], 
        batch_id: Optional[str] = None,
        migration_strategy: str = "staged"
    ) -> BatchMigrationStatus:
        """
        Simulate a complete staged migration for a batch of patients.
        
        Args:
            patients: List of patient records to migrate
            batch_id: Optional batch identifier
            migration_strategy: Migration approach (staged, big_bang, parallel)
            
        Returns:
            BatchMigrationStatus with complete migration results
        """
        batch_id = batch_id or f"batch_{uuid.uuid4().hex[:8]}"
        
        # Initialize batch status
        batch_status = BatchMigrationStatus(
            batch_id=batch_id,
            batch_size=len(patients),
            migration_strategy=migration_strategy,
            started_at=datetime.now(),
            patient_statuses={p.patient_id: "pending" for p in patients}
        )
        
        self.current_batch = batch_status
        
        try:
            # Execute each migration stage
            for stage in MIGRATION_STAGES:
                batch_status.current_stage = stage
                stage_success = self._execute_migration_stage(patients, stage, batch_status)
                
                if not stage_success and migration_strategy == "fail_fast":
                    break
                    
            # Calculate final metrics
            batch_status.completed_at = datetime.now()
            batch_status.calculate_metrics()
            self._calculate_quality_metrics(patients, batch_status)
            
        except Exception as e:
            batch_status.current_stage = "failed"
            print(f"Migration batch {batch_id} failed with error: {str(e)}")
            
        self.migration_history.append(batch_status)
        return batch_status
    
    def _execute_migration_stage(
        self, 
        patients: List[PatientRecord], 
        stage: str, 
        batch_status: BatchMigrationStatus
    ) -> bool:
        """Execute a specific migration stage for all patients"""
        
        # Execute substages
        substages = ETL_SUBSTAGES.get(stage, [stage])
        stage_successful = True
        
        for substage in substages:
            substage_result = MigrationStageResult(
                stage=stage,
                substage=substage,
                status="running",
                start_time=datetime.now(),
                records_processed=len(patients)
            )
            
            # Simulate processing time
            processing_time = self._calculate_processing_time(stage, len(patients))
            
            # Simulate realistic delays for healthcare environments
            import time
            time.sleep(min(processing_time, 0.1))  # Cap at 0.1s for demo
            
            # Simulate failures and process patients
            successful_count = 0
            failed_count = 0
            
            for patient in patients:
                patient_success = self._process_patient_stage(patient, stage, substage)
                if patient_success:
                    successful_count += 1
                    if batch_status.patient_statuses[patient.patient_id] != "failed":
                        batch_status.patient_statuses[patient.patient_id] = f"{stage}_{substage}_complete"
                else:
                    failed_count += 1
                    batch_status.patient_statuses[patient.patient_id] = "failed"
                    stage_successful = False
            
            # Complete substage result
            substage_result.end_time = datetime.now()
            substage_result.records_successful = successful_count
            substage_result.records_failed = failed_count
            substage_result.status = "completed" if failed_count == 0 else "partial_failure"
            
            if failed_count > 0:
                substage_result.error_type = random.choice(FAILURE_TYPES)
                substage_result.error_message = self._generate_error_message(substage_result.error_type, stage, substage)
            
            batch_status.stage_results.append(substage_result)
        
        return stage_successful
    
    def _process_patient_stage(self, patient: PatientRecord, stage: str, substage: str) -> bool:
        """Process a single patient through a migration stage/substage"""
        
        # Get success rate for this substage
        stage_rates = self.config.substage_success_rates.get(stage, {})
        success_rate = stage_rates.get(substage, self.config.stage_success_rates.get(stage, 0.9))
        
        # Apply additional failure factors
        if random.random() < self.config.network_failure_rate:
            success_rate *= 0.5  # Network issues reduce success rate
            
        if random.random() < self.config.system_overload_rate:
            success_rate *= 0.7  # System overload reduces success rate
        
        # Determine if this patient succeeds in this substage
        patient_succeeds = random.random() < success_rate
        
        # Update patient data quality score
        if patient_succeeds:
            # Even successful migrations cause slight quality degradation
            quality_impact = self.config.quality_degradation_per_success
            patient.metadata['data_quality_score'] = max(
                0.0, 
                patient.metadata['data_quality_score'] - quality_impact
            )
        else:
            # Failed migrations cause more significant quality degradation
            quality_impact = self.config.quality_degradation_per_failure
            patient.metadata['data_quality_score'] = max(
                0.0,
                patient.metadata['data_quality_score'] - quality_impact
            )
            
        # Update patient migration status
        if patient_succeeds:
            patient.metadata['migration_status'] = f"{stage}_{substage}_complete"
        else:
            patient.metadata['migration_status'] = f"{stage}_{substage}_failed"
            
        return patient_succeeds
    
    def _calculate_processing_time(self, stage: str, patient_count: int) -> float:
        """Calculate realistic processing time for a stage"""
        base_time = self.config.stage_base_duration.get(stage, 3.0)
        
        # Scale with patient count (logarithmic scaling for realism)
        import math
        scaling_factor = 1 + math.log10(max(1, patient_count / 10))
        
        # Add variance
        variance = random.uniform(
            1 - self.config.duration_variance,
            1 + self.config.duration_variance
        )
        
        return base_time * scaling_factor * variance
    
    def _generate_error_message(self, error_type: str, stage: str, substage: str) -> str:
        """Generate realistic error messages for healthcare migrations"""
        error_templates = {
            "network_timeout": f"Network timeout during {stage}.{substage}: Connection to VistA server timed out after 30 seconds",
            "data_corruption": f"Data corruption detected in {stage}.{substage}: Invalid character encoding in patient demographics",
            "mapping_error": f"Mapping error in {stage}.{substage}: Unable to map VistA field ^DPT({{}},0.35) to Oracle Health schema",
            "validation_failure": f"Validation failed in {stage}.{substage}: Patient SSN format does not match target system requirements",
            "resource_exhaustion": f"Resource exhaustion in {stage}.{substage}: Insufficient memory to process batch, consider reducing batch size",
            "security_violation": f"Security violation in {stage}.{substage}: Access denied to PHI data during migration",
            "system_unavailable": f"System unavailable in {stage}.{substage}: Oracle Health target system is currently in maintenance mode"
        }
        return error_templates.get(error_type, f"Unknown error in {stage}.{substage}")
    
    def _calculate_quality_metrics(self, patients: List[PatientRecord], batch_status: BatchMigrationStatus):
        """Calculate data quality metrics for the batch"""
        if not patients:
            batch_status.average_quality_score = 0.0
            return
            
        total_quality = sum(p.metadata['data_quality_score'] for p in patients)
        batch_status.average_quality_score = total_quality / len(patients)
    
    def get_migration_analytics(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive migration analytics and reporting.
        
        Args:
            batch_id: Optional specific batch to analyze, None for overall analytics
            
        Returns:
            Dictionary containing detailed analytics
        """
        if batch_id:
            # Single batch analytics
            batch = next((b for b in self.migration_history if b.batch_id == batch_id), None)
            if not batch:
                return {"error": f"Batch {batch_id} not found"}
            batches = [batch]
        else:
            # Overall analytics
            batches = self.migration_history
            
        if not batches:
            return {"error": "No migration data available"}
        
        analytics = {
            "summary": {
                "total_batches": len(batches),
                "total_patients": sum(b.batch_size for b in batches),
                "overall_success_rate": sum(b.overall_success_rate for b in batches) / len(batches),
                "average_quality_score": sum(b.average_quality_score for b in batches) / len(batches),
                "total_errors": sum(b.total_errors for b in batches)
            },
            "stage_performance": self._analyze_stage_performance(batches),
            "failure_analysis": self._analyze_failures(batches),
            "quality_trends": self._analyze_quality_trends(batches),
            "timing_analysis": self._analyze_timing(batches),
            "recommendations": self._generate_recommendations(batches)
        }
        
        return analytics
    
    def _analyze_stage_performance(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        """Analyze performance by migration stage"""
        stage_stats = {}
        
        for stage in MIGRATION_STAGES:
            stage_results = []
            for batch in batches:
                stage_results.extend([r for r in batch.stage_results if r.stage == stage])
            
            if stage_results:
                successful = sum(1 for r in stage_results if r.status == "completed")
                total_duration = sum(r.duration_seconds for r in stage_results)
                avg_records_processed = sum(r.records_processed for r in stage_results) / len(stage_results)
                
                stage_stats[stage] = {
                    "success_rate": successful / len(stage_results),
                    "average_duration": total_duration / len(stage_results),
                    "average_records_processed": avg_records_processed,
                    "total_executions": len(stage_results)
                }
        
        return stage_stats
    
    def _analyze_failures(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        """Analyze failure patterns and types"""
        failure_types = defaultdict(int)
        failure_stages = defaultdict(int)
        
        for batch in batches:
            for result in batch.stage_results:
                if result.status in ["failed", "partial_failure"] and result.error_type:
                    failure_types[result.error_type] += 1
                    failure_stages[result.stage] += 1
        
        return {
            "failure_types": dict(failure_types),
            "failure_by_stage": dict(failure_stages),
            "most_common_failure": max(failure_types.items(), key=lambda x: x[1])[0] if failure_types else None
        }
    
    def _analyze_quality_trends(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        """Analyze data quality degradation trends"""
        quality_scores = [b.average_quality_score for b in batches]
        
        if len(quality_scores) > 1:
            quality_trend = quality_scores[-1] - quality_scores[0]  # Simple trend
            quality_variance = max(quality_scores) - min(quality_scores)
        else:
            quality_trend = 0.0
            quality_variance = 0.0
        
        return {
            "initial_quality": quality_scores[0] if quality_scores else 0.0,
            "final_quality": quality_scores[-1] if quality_scores else 0.0,
            "quality_trend": quality_trend,
            "quality_variance": quality_variance,
            "min_quality": min(quality_scores) if quality_scores else 0.0,
            "max_quality": max(quality_scores) if quality_scores else 0.0
        }
    
    def _analyze_timing(self, batches: List[BatchMigrationStatus]) -> Dict[str, Any]:
        """Analyze migration timing patterns"""
        durations = []
        for batch in batches:
            if batch.started_at and batch.completed_at:
                duration = (batch.completed_at - batch.started_at).total_seconds()
                durations.append(duration)
        
        if not durations:
            return {"error": "No timing data available"}
        
        return {
            "average_batch_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_migration_time": sum(durations)
        }
    
    def _generate_recommendations(self, batches: List[BatchMigrationStatus]) -> List[str]:
        """Generate actionable recommendations based on migration analytics"""
        recommendations = []
        
        if not batches:
            return ["No data available for recommendations"]
        
        # Analyze overall success rate
        avg_success_rate = sum(b.overall_success_rate for b in batches) / len(batches)
        if avg_success_rate < 0.8:
            recommendations.append("Overall success rate is below 80%. Consider reducing batch sizes and implementing additional error handling.")
        
        # Analyze quality degradation
        avg_quality = sum(b.average_quality_score for b in batches) / len(batches)
        if avg_quality < 0.85:
            recommendations.append("Significant data quality degradation detected. Review data transformation rules and implement additional validation checkpoints.")
        
        # Analyze failure patterns
        failure_analysis = self._analyze_failures(batches)
        if failure_analysis.get("most_common_failure"):
            most_common = failure_analysis["most_common_failure"]
            recommendations.append(f"Most common failure type is '{most_common}'. Implement specific handling for this error type.")
        
        # Timing recommendations
        timing = self._analyze_timing(batches)
        if "average_batch_duration" in timing and timing["average_batch_duration"] > 300:  # 5 minutes
            recommendations.append("Average batch processing time is high. Consider parallel processing or batch size optimization.")
        
        return recommendations
    
    def export_migration_report(self, output_file: str, batch_id: Optional[str] = None):
        """Export detailed migration report to file"""
        analytics = self.get_migration_analytics(batch_id)
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("HEALTHCARE DATA MIGRATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if batch_id:
            report_lines.append(f"Batch ID: {batch_id}")
        else:
            report_lines.append("Report Type: Overall Migration Analytics")
        
        report_lines.append("")
        
        # Summary section
        if "summary" in analytics:
            summary = analytics["summary"]
            report_lines.append("EXECUTIVE SUMMARY")
            report_lines.append("-" * 40)
            report_lines.append(f"Total Batches Processed: {summary['total_batches']}")
            report_lines.append(f"Total Patients Migrated: {summary['total_patients']}")
            report_lines.append(f"Overall Success Rate: {summary['overall_success_rate']:.2%}")
            report_lines.append(f"Average Data Quality Score: {summary['average_quality_score']:.3f}")
            report_lines.append(f"Total Errors Encountered: {summary['total_errors']}")
            report_lines.append("")
        
        # Stage performance
        if "stage_performance" in analytics:
            report_lines.append("STAGE PERFORMANCE ANALYSIS")
            report_lines.append("-" * 40)
            for stage, stats in analytics["stage_performance"].items():
                report_lines.append(f"Stage: {stage.upper()}")
                report_lines.append(f"  Success Rate: {stats['success_rate']:.2%}")
                report_lines.append(f"  Average Duration: {stats['average_duration']:.2f} seconds")
                report_lines.append(f"  Average Records: {stats['average_records_processed']:.0f}")
                report_lines.append("")
        
        # Failure analysis
        if "failure_analysis" in analytics:
            failure = analytics["failure_analysis"]
            report_lines.append("FAILURE ANALYSIS")
            report_lines.append("-" * 40)
            if failure.get("failure_types"):
                report_lines.append("Failure Types:")
                for failure_type, count in failure["failure_types"].items():
                    report_lines.append(f"  {failure_type}: {count}")
                report_lines.append("")
            
            if failure.get("most_common_failure"):
                report_lines.append(f"Most Common Failure: {failure['most_common_failure']}")
                report_lines.append("")
        
        # Recommendations
        if "recommendations" in analytics:
            report_lines.append("RECOMMENDATIONS")
            report_lines.append("-" * 40)
            for i, rec in enumerate(analytics["recommendations"], 1):
                report_lines.append(f"{i}. {rec}")
            report_lines.append("")
        
        # Write report to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))

class FHIRFormatter:
    """Basic FHIR R4 formatter for Phase 1"""
    
    @staticmethod
    def create_patient_resource(patient_record: PatientRecord) -> Dict[str, Any]:
        """Create basic FHIR R4 Patient resource"""
        return {
            "resourceType": "Patient",
            "id": patient_record.patient_id,
            "identifier": [
                {
                    "use": "usual",
                    "type": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]
                    },
                    "value": patient_record.mrn or patient_record.generate_mrn()
                },
                {
                    "use": "official",
                    "type": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]
                    },
                    "system": "http://hl7.org/fhir/sid/us-ssn",
                    "value": patient_record.ssn
                }
            ] if patient_record.ssn else [
                {
                    "use": "usual",
                    "type": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]
                    },
                    "value": patient_record.mrn or patient_record.generate_mrn()
                }
            ],
            "active": True,
            "name": [{
                "use": "official",
                "family": patient_record.last_name,
                "given": [patient_record.first_name]
            }],
            "gender": patient_record.gender,
            "birthDate": patient_record.birthdate,
            "address": [{
                "use": "home",
                "line": [patient_record.address],
                "city": patient_record.city,
                "state": patient_record.state,
                "postalCode": patient_record.zip,
                "country": patient_record.country
            }] if patient_record.address else []
        }
    
    @staticmethod
    def create_condition_resource(patient_id: str, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic FHIR R4 Condition resource with terminology mappings"""
        condition_name = condition.get('name', '')
        codes = TERMINOLOGY_MAPPINGS['conditions'].get(condition_name, {})
        
        coding = []
        if 'icd10' in codes:
            coding.append({
                "system": "http://hl7.org/fhir/sid/icd-10-cm",
                "code": codes['icd10'],
                "display": condition_name
            })
        if 'snomed' in codes:
            coding.append({
                "system": "http://snomed.info/sct",
                "code": codes['snomed'],
                "display": condition_name
            })
        
        # Fallback if no coding found
        if not coding:
            coding.append({
                "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                "code": "unknown",
                "display": condition_name
            })
        
        return {
            "resourceType": "Condition",
            "id": condition.get('condition_id', str(uuid.uuid4())),
            "subject": {"reference": f"Patient/{patient_id}"},
            "code": {"coding": coding},
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": condition.get('status', 'active')
                }]
            },
            "onsetDateTime": condition.get('onset_date')
        }

class HL7v2Formatter:
    """HL7 v2.x message formatter for Phase 2"""
    
    @staticmethod
    def create_adt_message(patient_record: PatientRecord, encounter: Dict[str, Any] = None, message_type: str = "A04") -> str:
        """Create HL7 v2 ADT (Admit/Discharge/Transfer) message"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        message_control_id = f"MSG{random.randint(100000, 999999)}"
        
        segments = []
        
        # MSH - Message Header
        msh = (f"MSH|^~\\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|{timestamp}||"
               f"ADT^{message_type}|{message_control_id}|P|2.5")
        segments.append(msh)
        
        # EVN - Event Type  
        evn = f"EVN|{message_type}|{timestamp}|||"
        segments.append(evn)
        
        # PID - Patient Identification
        pid_segments = [
            "PID",
            "1",  # Set ID
            "",   # External ID
            f"{patient_record.mrn}^^^VA^MR~{patient_record.ssn}^^^USA^SS" if patient_record.ssn else f"{patient_record.mrn}^^^VA^MR",
            "",   # Alternate Patient ID
            f"{patient_record.last_name}^{patient_record.first_name}^{patient_record.middle_name}",
            "",   # Mother's Maiden Name
            patient_record.birthdate.replace('-', ''),
            patient_record.gender.upper()[0] if patient_record.gender else "U",
            "",   # Patient Alias
            HL7v2Formatter._get_hl7_race_code(patient_record.race),
            f"{patient_record.address}^^{patient_record.city}^{patient_record.state}^{patient_record.zip}",
            "",   # County Code
            patient_record.phone if hasattr(patient_record, 'phone') and patient_record.phone else "",
            "",   # Business Phone
            HL7v2Formatter._get_hl7_language_code(patient_record.language),
            HL7v2Formatter._get_hl7_marital_code(patient_record.marital_status),
            "",   # Religion
            f"{patient_record.patient_id}^^^VA^AN",  # Account Number
            patient_record.ssn if patient_record.ssn else "",
            "",   # Driver's License
            "",   # Mother's Identifier
            HL7v2Formatter._get_hl7_ethnicity_code(patient_record.ethnicity),
            "",   # Birth Place
            "",   # Multiple Birth Indicator
            "",   # Birth Order
            "",   # Citizenship
            "",   # Veterans Military Status
            "",   # Nationality
            "",   # Death Date
            "",   # Death Indicator
            "",   # Identity Unknown
            "",   # Identity Reliability
            "",   # Last Update Date
            "",   # Last Update Facility
            "",   # Species Code
            "",   # Breed Code
            "",   # Strain
            "",   # Production Class Code
            ""    # Tribal Citizenship
        ]
        
        pid = "|".join(pid_segments)
        segments.append(pid)
        
        # PV1 - Patient Visit (if encounter provided)
        if encounter:
            pv1_segments = [
                "PV1",
                "1",  # Set ID
                encounter.get('type', 'O'),  # Patient Class (O=Outpatient, I=Inpatient)
                "CLINIC1^^^VA^CLINIC",  # Assigned Patient Location
                "",   # Admission Type
                "",   # Preadmit Number
                "",   # Prior Patient Location
                "DOE^JOHN^A^^^DR",  # Attending Doctor
                "",   # Referring Doctor
                "",   # Consulting Doctor
                "GIM",  # Hospital Service
                "",   # Temporary Location
                "",   # Preadmit Test Indicator
                "",   # Re-admission Indicator
                "",   # Admit Source
                "",   # Ambulatory Status
                "",   # VIP Indicator
                "",   # Admitting Doctor
                "",   # Patient Type
                "",   # Visit Number
                "",   # Financial Class
                "",   # Charge Price Indicator
                "",   # Courtesy Code
                "",   # Credit Rating
                "",   # Contract Code
                "",   # Contract Effective Date
                "",   # Contract Amount
                "",   # Contract Period
                "",   # Interest Code
                "",   # Transfer to Bad Debt Code
                "",   # Transfer to Bad Debt Date
                "",   # Bad Debt Agency Code
                "",   # Bad Debt Transfer Amount
                "",   # Bad Debt Recovery Amount
                "",   # Delete Account Indicator
                "",   # Delete Account Date
                "",   # Discharge Disposition
                "",   # Discharged to Location
                "",   # Diet Type
                "",   # Servicing Facility
                "",   # Bed Status
                "",   # Account Status
                "",   # Pending Location
                "",   # Prior Temporary Location
                encounter.get('date', '').replace('-', '') if encounter.get('date') else timestamp[:8],  # Admit Date/Time
                "",   # Discharge Date/Time
                "",   # Current Patient Balance
                "",   # Total Charges
                "",   # Total Adjustments
                "",   # Total Payments
                "",   # Alternate Visit ID
                "",   # Visit Indicator
                ""    # Other Healthcare Provider
            ]
            
            pv1 = "|".join(pv1_segments)
            segments.append(pv1)
        
        return "\r".join(segments)
    
    @staticmethod
    def create_oru_message(patient_record: PatientRecord, observations: list) -> str:
        """Create HL7 v2 ORU (Observation Result) message for lab results"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        message_control_id = f"LAB{random.randint(100000, 999999)}"
        
        segments = []
        
        # MSH - Message Header
        msh = (f"MSH|^~\\&|VistA|VA_FACILITY|LAB|LAB_FACILITY|{timestamp}||"
               f"ORU^R01|{message_control_id}|P|2.5")
        segments.append(msh)
        
        # PID - Patient Identification (same as ADT)
        pid = (f"PID|1||{patient_record.mrn}^^^VA^MR~{patient_record.ssn}^^^USA^SS||"
               f"{patient_record.last_name}^{patient_record.first_name}^{patient_record.middle_name}||"
               f"{patient_record.birthdate.replace('-', '')}|{patient_record.gender.upper()[0]}|||"
               f"{patient_record.address}^^{patient_record.city}^{patient_record.state}^{patient_record.zip}")
        segments.append(pid)
        
        # OBR - Observation Request
        obr = (f"OBR|1|{random.randint(100000, 999999)}|{random.randint(100000, 999999)}|"
               f"CBC^Complete Blood Count^L|||{timestamp}||||||||||DOE^JOHN^A")
        segments.append(obr)
        
        # OBX - Observation/Result segments
        for i, obs in enumerate(observations[:5], 1):  # Limit to 5 observations
            obs_type = obs.get('type', 'Unknown')
            obs_value = obs.get('value', '')
            
            # Map observation types to LOINC codes
            loinc_code = HL7v2Formatter._get_loinc_code(obs_type)
            data_type = HL7v2Formatter._get_hl7_data_type(obs_type)
            units = HL7v2Formatter._get_observation_units(obs_type)
            
            obx = (f"OBX|{i}|{data_type}|{loinc_code}^{obs_type}^LN||{obs_value}|{units}||||F|||"
                   f"{timestamp}")
            segments.append(obx)
        
        return "\r".join(segments)
    
    @staticmethod
    def _get_hl7_race_code(race: str) -> str:
        """Map race to HL7 codes"""
        race_mapping = {
            "White": "2106-3^White^HL70005",
            "Black": "2054-5^Black or African American^HL70005", 
            "Asian": "2028-9^Asian^HL70005",
            "Hispanic": "2131-1^Other Race^HL70005",
            "Native American": "1002-5^American Indian or Alaska Native^HL70005",
            "Other": "2131-1^Other Race^HL70005"
        }
        return race_mapping.get(race, "2131-1^Other Race^HL70005")
    
    @staticmethod
    def _get_hl7_ethnicity_code(ethnicity: str) -> str:
        """Map ethnicity to HL7 codes"""
        return "2135-2^Hispanic or Latino^HL70189" if ethnicity == "Hispanic or Latino" else "2186-5^Not Hispanic or Latino^HL70189"
    
    @staticmethod
    def _get_hl7_language_code(language: str) -> str:
        """Map language to HL7 codes"""
        lang_mapping = {
            "English": "en^English^ISO639",
            "Spanish": "es^Spanish^ISO639",
            "Chinese": "zh^Chinese^ISO639",
            "French": "fr^French^ISO639",
            "German": "de^German^ISO639",
            "Vietnamese": "vi^Vietnamese^ISO639"
        }
        return lang_mapping.get(language, "en^English^ISO639")
    
    @staticmethod
    def _get_hl7_marital_code(marital_status: str) -> str:
        """Map marital status to HL7 codes"""
        marital_mapping = {
            "Never Married": "S^Single^HL70002",
            "Married": "M^Married^HL70002",
            "Divorced": "D^Divorced^HL70002",
            "Widowed": "W^Widowed^HL70002",
            "Separated": "A^Separated^HL70002"
        }
        return marital_mapping.get(marital_status, "U^Unknown^HL70002")
    
    @staticmethod
    def _get_loinc_code(observation_type: str) -> str:
        """Map observation types to LOINC codes"""
        loinc_mapping = {
            "Height": "8302-2",
            "Weight": "29463-7", 
            "Blood Pressure": "85354-9",
            "Heart Rate": "8867-4",
            "Temperature": "8310-5",
            "Hemoglobin A1c": "4548-4",
            "Cholesterol": "2093-3"
        }
        return loinc_mapping.get(observation_type, "8310-5")  # Default to temperature
    
    @staticmethod
    def _get_hl7_data_type(observation_type: str) -> str:
        """Get HL7 data type for observation"""
        if observation_type in ["Blood Pressure"]:
            return "ST"  # String
        else:
            return "NM"  # Numeric
    
    @staticmethod
    def _get_observation_units(observation_type: str) -> str:
        """Get units for observation values"""
        units_mapping = {
            "Height": "cm",
            "Weight": "kg",
            "Blood Pressure": "mmHg",
            "Heart Rate": "bpm",
            "Temperature": "Cel",
            "Hemoglobin A1c": "%",
            "Cholesterol": "mg/dL"
        }
        return units_mapping.get(observation_type, "")

class VistaFormatter:
    """VistA MUMPS global formatter for Phase 3 - Production accurate VA migration simulation"""
    
    @staticmethod
    def vista_date_format(date_str: str) -> str:
        """Convert ISO date to VistA internal date format (days since 1841-01-01)"""
        if not date_str:
            return ""
        
        try:
            from datetime import date
            if isinstance(date_str, str):
                input_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                input_date = date_str
            
            # VistA uses days since 1841-01-01 (FileMan date format)
            vista_epoch = date(1841, 1, 1)
            days_since_epoch = (input_date - vista_epoch).days
            return str(days_since_epoch)
        except:
            return ""
    
    @staticmethod
    def vista_datetime_format(date_str: str, time_str: str = None) -> str:
        """Convert to VistA datetime format (YYYMMDD.HHMMSS where YYY is years since 1700)"""
        if not date_str:
            return ""
            
        try:
            if isinstance(date_str, str):
                input_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                input_date = date_str
            
            # VistA datetime: years since 1700 + MMDD.HHMMSS
            years_since_1700 = input_date.year - 1700
            month_day = f"{input_date.month:02d}{input_date.day:02d}"
            
            if time_str:
                time_part = time_str.replace(":", "")
            else:
                # Default to noon for encounters
                time_part = "120000"
            
            return f"{years_since_1700}{month_day}.{time_part}"
        except:
            return ""
    
    @staticmethod
    def sanitize_mumps_string(text: str) -> str:
        """Sanitize string for MUMPS global storage - handle special characters"""
        if not text:
            return ""
        
        # Remove or replace characters that would break MUMPS syntax
        sanitized = str(text).replace("^", " ").replace('"', "'").replace("\r", "").replace("\n", " ")
        # Limit length for FileMan fields
        return sanitized[:30] if len(sanitized) > 30 else sanitized
    
    @staticmethod
    def generate_vista_ien() -> str:
        """Generate VistA Internal Entry Number (IEN)"""
        return str(random.randint(1, 999999))
    
    @staticmethod
    def create_dpt_global(patient_record: PatientRecord) -> Dict[str, str]:
        """Create ^DPT Patient File #2 global structure"""
        vista_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Patient name in LAST,FIRST MIDDLE format
        full_name = f"{patient_record.last_name.upper()},{patient_record.first_name.upper()}"
        if patient_record.middle_name:
            full_name += f" {patient_record.middle_name.upper()}"
        full_name = VistaFormatter.sanitize_mumps_string(full_name)
        
        # Convert gender to VistA format
        vista_sex = "M" if patient_record.gender.lower() in ["male", "m"] else "F"
        
        # Convert date of birth to VistA format
        vista_dob = VistaFormatter.vista_date_format(patient_record.birthdate)
        
        # Sanitize SSN (remove dashes)
        vista_ssn = patient_record.ssn.replace("-", "") if patient_record.ssn else ""
        
        # Convert marital status to VistA codes
        marital_mapping = {
            "Never Married": "S",
            "Married": "M", 
            "Divorced": "D",
            "Widowed": "W",
            "Separated": "A"
        }
        vista_marital = marital_mapping.get(patient_record.marital_status, "U")
        
        # Convert race to VistA codes (simplified)
        race_mapping = {
            "White": "5",
            "Black": "3",
            "Asian": "6", 
            "Hispanic": "7",
            "Native American": "1",
            "Other": "8"
        }
        vista_race = race_mapping.get(patient_record.race, "8")
        
        globals_dict = {}
        
        # Main patient record - ^DPT(IEN,0)
        # Format: NAME^SEX^DOB^EMPLOYMENT^MARITAL^RACE^OCCUPATION^RELIGION^SSN
        zero_node = f"{full_name}^{vista_sex}^{vista_dob}^^^{vista_race}^^{vista_ssn}"
        globals_dict[f"^DPT({vista_ien},0)"] = zero_node
        
        # Address information - ^DPT(IEN,.11)
        if patient_record.address:
            address_node = f"{VistaFormatter.sanitize_mumps_string(patient_record.address)}^{VistaFormatter.sanitize_mumps_string(patient_record.city)}^{patient_record.state}^{patient_record.zip}"
            globals_dict[f"^DPT({vista_ien},.11)"] = address_node
        
        # Phone number - ^DPT(IEN,.13)
        if patient_record.phone:
            globals_dict[f"^DPT({vista_ien},.13)"] = VistaFormatter.sanitize_mumps_string(patient_record.phone)
        
        # Cross-reference: "B" index for name lookup
        globals_dict[f'^DPT("B","{full_name}",{vista_ien})'] = ""
        
        # Cross-reference: SSN index
        if vista_ssn:
            globals_dict[f'^DPT("SSN","{vista_ssn}",{vista_ien})'] = ""
        
        # Cross-reference: DOB index  
        if vista_dob:
            globals_dict[f'^DPT("DOB",{vista_dob},{vista_ien})'] = ""
        
        return globals_dict
    
    @staticmethod
    def create_aupnvsit_global(patient_record: PatientRecord, encounter: Dict[str, Any]) -> Dict[str, str]:
        """Create ^AUPNVSIT Visit File #9000010 global structure"""
        visit_ien = VistaFormatter.generate_vista_ien()
        patient_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Visit date/time in VistA format
        visit_datetime = VistaFormatter.vista_datetime_format(encounter.get('date', ''))
        
        # Map encounter types to VistA stop codes (simplified)
        stop_code_mapping = {
            "Wellness Visit": "323",
            "Emergency": "130", 
            "Follow-up": "323",
            "Specialist": "301",
            "Lab": "175",
            "Surgery": "162"
        }
        stop_code = stop_code_mapping.get(encounter.get('type', ''), "323")
        
        # Service category mapping
        service_category = "A"  # Ambulatory care
        if encounter.get('type') == "Emergency":
            service_category = "E"  # Emergency
        elif encounter.get('type') == "Surgery":
            service_category = "I"  # Inpatient
        
        globals_dict = {}
        
        # Main visit record - ^AUPNVSIT(IEN,0)
        # Format: PATIENT_IEN^VISIT_DATE^VISIT_TYPE^STOP_CODE^SERVICE_CATEGORY
        zero_node = f"{patient_ien}^{visit_datetime}^{service_category}^{stop_code}^{encounter.get('encounter_id', '')}"
        globals_dict[f"^AUPNVSIT({visit_ien},0)"] = zero_node
        
        # Visit location - ^AUPNVSIT(IEN,.06)
        if encounter.get('location'):
            globals_dict[f"^AUPNVSIT({visit_ien},.06)"] = VistaFormatter.sanitize_mumps_string(encounter.get('location', ''))
        
        # Cross-reference: "B" index by patient and date
        globals_dict[f'^AUPNVSIT("B",{patient_ien},{visit_datetime},{visit_ien})'] = ""
        
        # Cross-reference: Date index
        globals_dict[f'^AUPNVSIT("D",{visit_datetime},{visit_ien})'] = ""
        
        return globals_dict
    
    @staticmethod 
    def create_aupnprob_global(patient_record: PatientRecord, condition: Dict[str, Any]) -> Dict[str, str]:
        """Create ^AUPNPROB Problem List File #9000011 global structure"""
        problem_ien = VistaFormatter.generate_vista_ien()
        patient_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Problem onset date
        onset_date = VistaFormatter.vista_date_format(condition.get('onset_date', ''))
        
        # Problem status mapping
        status_mapping = {
            "active": "A",
            "resolved": "I",  # Inactive
            "remission": "A"
        }
        problem_status = status_mapping.get(condition.get('status', 'active'), "A")
        
        # Get ICD codes from existing mappings
        condition_name = condition.get('name', '')
        icd_code = ""
        if condition_name in TERMINOLOGY_MAPPINGS.get('conditions', {}):
            icd_code = TERMINOLOGY_MAPPINGS['conditions'][condition_name].get('icd10', '')
        
        globals_dict = {}
        
        # Main problem record - ^AUPNPROB(IEN,0)
        # Format: PATIENT_IEN^PROBLEM_TEXT^STATUS^ONSET_DATE^ICD_CODE
        problem_text = VistaFormatter.sanitize_mumps_string(condition_name)
        zero_node = f"{patient_ien}^{problem_text}^{problem_status}^{onset_date}^{icd_code}"
        globals_dict[f"^AUPNPROB({problem_ien},0)"] = zero_node
        
        # Problem narrative - ^AUPNPROB(IEN,.05)
        if condition_name:
            globals_dict[f"^AUPNPROB({problem_ien},.05)"] = problem_text
        
        # Cross-reference: "B" index by patient
        globals_dict[f'^AUPNPROB("B",{patient_ien},{problem_ien})'] = ""
        
        # Cross-reference: Status index
        globals_dict[f'^AUPNPROB("S","{problem_status}",{patient_ien},{problem_ien})'] = ""
        
        # Cross-reference: ICD index
        if icd_code:
            globals_dict[f'^AUPNPROB("ICD","{icd_code}",{patient_ien},{problem_ien})'] = ""
        
        return globals_dict
    
    @staticmethod
    def export_vista_globals(patients: List[PatientRecord], encounters: List[Dict], conditions: List[Dict], output_file: str):
        """Export all VistA globals to MUMPS format file"""
        all_globals = {}
        
        print(f"Generating VistA MUMPS globals for {len(patients)} patients...")
        
        # Process patients
        for patient in tqdm(patients, desc="Creating VistA patient globals", unit="patients"):
            patient_globals = VistaFormatter.create_dpt_global(patient)
            all_globals.update(patient_globals)
        
        # Process encounters
        encounter_map = {}
        for encounter in encounters:
            patient_id = encounter.get('patient_id')
            if patient_id not in encounter_map:
                encounter_map[patient_id] = []
            encounter_map[patient_id].append(encounter)
        
        for patient in tqdm(patients, desc="Creating VistA encounter globals", unit="patients"):
            patient_encounters = encounter_map.get(patient.patient_id, [])
            for encounter in patient_encounters:
                visit_globals = VistaFormatter.create_aupnvsit_global(patient, encounter)
                all_globals.update(visit_globals)
        
        # Process conditions
        condition_map = {}
        for condition in conditions:
            patient_id = condition.get('patient_id')
            if patient_id not in condition_map:
                condition_map[patient_id] = []
            condition_map[patient_id].append(condition)
        
        for patient in tqdm(patients, desc="Creating VistA condition globals", unit="patients"):
            patient_conditions = condition_map.get(patient.patient_id, [])
            for condition in patient_conditions:
                problem_globals = VistaFormatter.create_aupnprob_global(patient, condition)
                all_globals.update(problem_globals)
        
        # Write to file in proper MUMPS global syntax
        with open(output_file, 'w') as f:
            f.write(";; VistA MUMPS Global Export for Synthetic Patient Data\n")
            f.write(f";; Generated on {datetime.now().isoformat()}\n")
            f.write(f";; Total global nodes: {len(all_globals)}\n")
            f.write(";;\n")
            
            # Sort globals for consistent output
            sorted_globals = sorted(all_globals.items())
            
            for global_ref, value in sorted_globals:
                if value:
                    f.write(f'S {global_ref}="{value}"\n')
                else:
                    f.write(f'S {global_ref}=""\n')
        
        print(f"VistA MUMPS globals exported to {output_file} ({len(all_globals)} global nodes)")
        
        # Generate summary statistics
        dpt_count = sum(1 for k in all_globals.keys() if k.startswith("^DPT(") and ",0)" in k)
        visit_count = sum(1 for k in all_globals.keys() if k.startswith("^AUPNVSIT(") and ",0)" in k)
        problem_count = sum(1 for k in all_globals.keys() if k.startswith("^AUPNPROB(") and ",0)" in k)
        
        return {
            "total_globals": len(all_globals),
            "patient_records": dpt_count,
            "visit_records": visit_count, 
            "problem_records": problem_count,
            "cross_references": len(all_globals) - dpt_count - visit_count - problem_count
        }

class HL7MessageValidator:
    """Basic HL7 v2 message validation for Phase 2"""
    
    @staticmethod
    def validate_message_structure(message: str) -> Dict[str, Any]:
        """Validate basic HL7 message structure"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "segments_found": []
        }
        
        if not message:
            validation_result["valid"] = False
            validation_result["errors"].append("Empty message")
            return validation_result
        
        segments = message.split('\r')
        
        # Check for required MSH segment
        if not segments or not segments[0].startswith('MSH'):
            validation_result["valid"] = False
            validation_result["errors"].append("Missing or invalid MSH segment")
            return validation_result
        
        # Validate each segment
        for i, segment in enumerate(segments):
            if not segment:
                continue
                
            segment_type = segment[:3]
            validation_result["segments_found"].append(segment_type)
            
            # Basic field count validation
            fields = segment.split('|')
            if segment_type == "MSH" and len(fields) < 10:
                validation_result["errors"].append(f"MSH segment has insufficient fields: {len(fields)}")
            elif segment_type == "PID" and len(fields) < 5:
                validation_result["errors"].append(f"PID segment has insufficient fields: {len(fields)}")
            elif segment_type in ["OBX", "OBR"] and len(fields) < 4:
                validation_result["errors"].append(f"{segment_type} segment has insufficient fields: {len(fields)}")
        
        # Check message type specific requirements
        if "PID" not in validation_result["segments_found"]:
            validation_result["warnings"].append("No PID segment found")
        
        if validation_result["errors"]:
            validation_result["valid"] = False
        
        return validation_result

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
# PHASE 1: Evidence-based medication mappings with clinical accuracy
CONDITION_MEDICATIONS = {
    "Hypertension": {
        "first_line": ["Lisinopril", "Amlodipine", "Hydrochlorothiazide"],
        "second_line": ["Metoprolol", "Losartan", "Indapamide"],
        "combinations": ["Lisinopril/Hydrochlorothiazide"]
    },
    "Diabetes": {
        "first_line": ["Metformin"],
        "second_line": ["Glipizide", "Sitagliptin", "Empagliflozin"],
        "insulin": ["Insulin_glargine", "Insulin_lispro"]
    },
    "Asthma": {
        "controller": ["Fluticasone", "Budesonide/Formoterol"],
        "rescue": ["Albuterol", "Levalbuterol"]
    },
    "COPD": {
        "bronchodilators": ["Tiotropium", "Salmeterol/Fluticasone"],
        "rescue": ["Albuterol", "Ipratropium"]
    },
    "Heart Disease": {
        "statins": ["Atorvastatin", "Rosuvastatin", "Simvastatin"],
        "antiplatelet": ["Aspirin", "Clopidogrel"],
        "ace_inhibitors": ["Lisinopril", "Enalapril"]
    },
    "Obesity": {
        "lifestyle": [],  # Primarily lifestyle interventions
        "medications": ["Orlistat", "Phentermine"]  # When BMI >30 with comorbidities
    },
    "Depression": {
        "ssri": ["Sertraline", "Escitalopram", "Fluoxetine"],
        "snri": ["Venlafaxine", "Duloxetine"],
        "atypical": ["Bupropion", "Mirtazapine"]
    },
    "Anxiety": {
        "ssri": ["Sertraline", "Paroxetine", "Escitalopram"],
        "benzodiazepines": ["Lorazepam", "Alprazolam"],
        "other": ["Buspirone"]
    },
    "Arthritis": {
        "nsaids": ["Ibuprofen", "Naproxen", "Celecoxib"],
        "dmards": ["Methotrexate", "Hydroxychloroquine"],
        "biologics": ["Adalimumab", "Etanercept"]
    },
    "Cancer": {
        "chemotherapy": ["Doxorubicin", "Cyclophosphamide", "Paclitaxel"],
        "targeted": ["Trastuzumab", "Bevacizumab"],
        "supportive": ["Ondansetron", "Dexamethasone", "Filgrastim"]
    },
    "Flu": {
        "antivirals": ["Oseltamivir", "Zanamivir"],  # Only if started within 48 hours
        "supportive": ["Acetaminophen", "Ibuprofen"]
    },
    "COVID-19": {
        "antivirals": ["Paxlovid", "Remdesivir"],  # For high-risk patients
        "supportive": ["Acetaminophen", "Dexamethasone"]  # Dex for severe cases
    },
    "Migraine": {
        "acute": ["Sumatriptan", "Rizatriptan", "Ibuprofen"],
        "prophylaxis": ["Propranolol", "Topiramate", "Amitriptyline"]
    },
    "Allergy": {
        "antihistamines": ["Loratadine", "Cetirizine", "Fexofenadine"],
        "nasal_steroids": ["Fluticasone_nasal", "Mometasone_nasal"],
        "emergency": ["Epinephrine"]  # For severe allergic reactions
    },
    "Stroke": {
        "antiplatelet": ["Aspirin", "Clopidogrel"],
        "anticoagulants": ["Warfarin", "Apixaban", "Rivaroxaban"],
        "statins": ["Atorvastatin", "Rosuvastatin"]
    },
    "Alzheimer's": {
        "cholinesterase_inhibitors": ["Donepezil", "Rivastigmine", "Galantamine"],
        "nmda_antagonist": ["Memantine"],
        "behavioral": []  # Primarily non-pharmacological
    }
}

# Basic contraindications to prevent dangerous prescribing
MEDICATION_CONTRAINDICATIONS = {
    "Metformin": ["eGFR_less_than_30", "Severe_heart_failure", "Metabolic_acidosis"],
    "Lisinopril": ["Pregnancy", "Hyperkalemia", "Angioedema_history", "Bilateral_renal_artery_stenosis"],
    "Warfarin": ["Active_bleeding", "Severe_liver_disease", "Recent_surgery"],
    "Aspirin": ["Active_GI_bleeding", "Severe_asthma", "Age_under_16_with_viral_illness"],
    "Ibuprofen": ["Active_GI_bleeding", "Severe_kidney_disease", "Heart_failure"],
    "Lorazepam": ["Severe_respiratory_disease", "Myasthenia_gravis", "Sleep_apnea"],
    "Alprazolam": ["Severe_respiratory_disease", "Myasthenia_gravis", "Sleep_apnea"],
    "Methotrexate": ["Pregnancy", "Severe_liver_disease", "Severe_kidney_disease", "Active_infection"]
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
# CONDITION_DEATH_CAUSES removed - replaced by CONDITION_MORTALITY_RISK with ICD-10-CM coding

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
    """Generate patient using enhanced PatientRecord class"""
    birthdate = fake.date_of_birth(minimum_age=0, maximum_age=100)
    age = (datetime.now().date() - birthdate).days // 365
    income = random.randint(0, 200000) if age >= 18 else 0
    
    patient = PatientRecord(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        middle_name=fake.first_name()[:1],  # Simple middle initial
        gender=random.choice(GENDERS),
        birthdate=birthdate.isoformat(),
        age=age,
        race=random.choice(RACES),
        ethnicity=random.choice(ETHNICITIES),
        address=fake.street_address(),
        city=fake.city(),
        state=fake.state_abbr(),
        zip=fake.zipcode(),
        country="US",
        phone=fake.phone_number(),
        email=fake.email(),
        marital_status=random.choice(MARITAL_STATUSES),
        language=random.choice(LANGUAGES),
        insurance=random.choice(INSURANCES),
        ssn=fake.ssn(),
        # SDOH fields
        smoking_status=random.choice(SDOH_SMOKING),
        alcohol_use=random.choice(SDOH_ALCOHOL),
        education=random.choice(SDOH_EDUCATION) if age >= 18 else "None",
        employment_status=random.choice(SDOH_EMPLOYMENT) if age >= 16 else "Student",
        income=income,
        housing_status=random.choice(SDOH_HOUSING),
    )
    
    # Generate healthcare IDs
    patient.generate_vista_id()
    patient.generate_mrn()
    
    return patient

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

# PHASE 1: Evidence-based medication generation with contraindication checking
def generate_medications(patient, encounters, conditions=None, min_med=0, max_med=4):
    medications = []
    patient_contraindications = get_patient_contraindications(patient)
    
    # Add evidence-based medications for chronic conditions
    if conditions:
        for cond in conditions:
            condition_meds = prescribe_evidence_based_medication(patient, cond, encounters, patient_contraindications)
            medications.extend(condition_meds)
    
    return medications

def get_patient_contraindications(patient):
    """Determine patient-specific contraindications based on age, conditions, etc."""
    contraindications = []
    
    age = patient.get("age", 0)
    gender = patient.get("gender", "")
    
    # Age-based contraindications
    if age < 16:
        contraindications.append("Age_under_16_with_viral_illness")
    
    # Gender-based contraindications
    if gender == "female" and 18 <= age <= 50:
        # Assume 5% chance of pregnancy for women of childbearing age
        if random.random() < 0.05:
            contraindications.append("Pregnancy")
    
    # Condition-based contraindications (simplified for Phase 1)
    # In a real system, this would check actual conditions
    if random.random() < 0.03:  # 3% chance of kidney disease
        contraindications.append("Severe_kidney_disease")
    if random.random() < 0.02:  # 2% chance of liver disease
        contraindications.append("Severe_liver_disease")
    if random.random() < 0.01:  # 1% chance of bleeding disorder
        contraindications.append("Active_bleeding")
    
    return contraindications

def prescribe_evidence_based_medication(patient, condition, encounters, contraindications):
    """Generate clinically appropriate medication prescriptions"""
    age = patient.get("age", 0)
    condition_name = condition["name"]
    treatment_guidelines = CONDITION_MEDICATIONS.get(condition_name, {})
    
    if not treatment_guidelines:
        return []
    
    medications = []
    
    # Select appropriate medication category based on condition
    if condition_name in ["Hypertension", "Heart Disease", "Stroke"]:
        # Prioritize first-line therapy
        if "first_line" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["first_line"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "first_line"))
    
    elif condition_name == "Diabetes":
        # Always start with Metformin if no contraindications
        metformin_safe = not any(contra in contraindications for contra in MEDICATION_CONTRAINDICATIONS.get("Metformin", []))
        if metformin_safe:
            medications.append(create_medication_record(patient, condition, encounters, "Metformin", "first_line"))
        else:
            # Use second-line if Metformin contraindicated
            selected_med = select_safe_medication(treatment_guidelines["second_line"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "second_line"))
    
    elif condition_name in ["Depression", "Anxiety"]:
        # Start with SSRI (safer than benzodiazepines)
        if "ssri" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["ssri"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "ssri"))
    
    elif condition_name in ["Flu", "COVID-19"]:
        # Only prescribe antivirals if within appropriate timeframe, otherwise supportive care
        if random.random() < 0.3:  # 30% get antivirals (early presentation)
            if "antivirals" in treatment_guidelines:
                selected_med = select_safe_medication(treatment_guidelines["antivirals"], contraindications)
                if selected_med:
                    medications.append(create_medication_record(patient, condition, encounters, selected_med, "antiviral"))
        
        # Add supportive care
        if "supportive" in treatment_guidelines:
            selected_med = select_safe_medication(treatment_guidelines["supportive"], contraindications)
            if selected_med:
                medications.append(create_medication_record(patient, condition, encounters, selected_med, "supportive"))
    
    else:
        # For other conditions, select from first available category
        for category, med_list in treatment_guidelines.items():
            if med_list:  # Skip empty categories
                selected_med = select_safe_medication(med_list, contraindications)
                if selected_med:
                    medications.append(create_medication_record(patient, condition, encounters, selected_med, category))
                    break
    
    return medications

def select_safe_medication(medication_list, contraindications):
    """Select a medication that doesn't have contraindications"""
    safe_medications = []
    
    for med in medication_list:
        med_contraindications = MEDICATION_CONTRAINDICATIONS.get(med, [])
        is_safe = not any(contra in contraindications for contra in med_contraindications)
        if is_safe:
            safe_medications.append(med)
    
    return random.choice(safe_medications) if safe_medications else None

def create_medication_record(patient, condition, encounters, medication_name, therapy_category):
    """Create a standardized medication record"""
    enc = random.choice(encounters) if encounters else None
    start_date = enc["date"] if enc else patient["birthdate"]
    
    if isinstance(start_date, str):
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date_obj = start_date
    
    # Chronic medications typically don't have end dates
    chronic_conditions = ["Hypertension", "Diabetes", "Heart Disease", "Depression", "Anxiety"]
    if condition["name"] in chronic_conditions:
        end_date = None
    else:
        # Acute medications have limited duration
        if random.random() < 0.8:  # 80% have end date
            end_date = fake.date_between(start_date=start_date_obj, end_date="today").isoformat()
        else:
            end_date = None
    
    return {
        "medication_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": enc["encounter_id"] if enc else None,
        "name": medication_name,
        "indication": condition["name"],
        "therapy_category": therapy_category,
        "start_date": start_date,
        "end_date": end_date,
    }

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

# PHASE 2: Enhanced procedure generation with clinical appropriateness and CPT coding
def generate_procedures(patient, encounters, conditions=None, min_proc=0, max_proc=3):
    procedures = []
    age = patient.get("age", 30)
    
    # Generate condition-appropriate procedures
    if conditions:
        for condition in conditions:
            condition_procedures = generate_condition_procedures(patient, encounters, condition)
            procedures.extend(condition_procedures)
    
    # Add age-appropriate screening procedures
    screening_procedures = generate_screening_procedures(patient, encounters, age)
    procedures.extend(screening_procedures)
    
    # Add random procedures (simulate incidental findings or routine care)
    n_random = random.randint(min_proc, max_proc)
    for _ in range(n_random):
        random_procedure = generate_random_procedure(patient, encounters)
        if random_procedure:
            procedures.append(random_procedure)
    
    return procedures

def generate_condition_procedures(patient, encounters, condition):
    """Generate clinically appropriate procedures for specific conditions"""
    procedures = []
    condition_name = condition["name"]
    
    # Find appropriate procedures for this condition
    applicable_procedures = []
    
    for specialty, procedure_categories in CLINICAL_PROCEDURES.items():
        for category, procedure_list in procedure_categories.items():
            for procedure in procedure_list:
                if condition_name in procedure.get("conditions", []):
                    applicable_procedures.append({
                        **procedure,
                        "specialty": specialty,
                        "category": category
                    })
    
    # Select procedures based on clinical appropriateness
    for procedure in applicable_procedures:
        # Probability based on complexity and clinical need
        complexity_probability = {
            "routine": 0.6,
            "moderate": 0.3,
            "high": 0.1,
            "very_high": 0.05
        }
        
        complexity = procedure.get("complexity", "routine")
        if random.random() < complexity_probability.get(complexity, 0.3):
            enc = random.choice(encounters) if encounters else None
            date = enc["date"] if enc else patient["birthdate"]
            
            # Determine outcome based on complexity
            outcome = generate_procedure_outcome(complexity, patient.get("age", 30))
            
            procedures.append({
                "procedure_id": str(uuid.uuid4()),
                "patient_id": patient["patient_id"],
                "encounter_id": enc["encounter_id"] if enc else None,
                "name": procedure["name"],
                "cpt_code": procedure.get("cpt", ""),
                "specialty": procedure["specialty"],
                "category": procedure["category"],
                "complexity": complexity,
                "indication": condition_name,
                "date": date,
                "outcome": outcome,
            })
    
    return procedures

def generate_screening_procedures(patient, encounters, age):
    """Generate age-appropriate screening procedures"""
    procedures = []
    gender = patient.get("gender", "")
    
    # Age-based screening guidelines
    screening_guidelines = {
        "Colonoscopy": {"age_range": (50, 75), "frequency_years": 10, "gender": "both"},
        "Mammography": {"age_range": (40, 74), "frequency_years": 2, "gender": "female"},
        "Cervical_Cancer_Screening": {"age_range": (21, 65), "frequency_years": 3, "gender": "female"},
        "Prostate_Screening": {"age_range": (50, 75), "frequency_years": 2, "gender": "male"},
        "Bone_Density_Scan": {"age_range": (65, 85), "frequency_years": 2, "gender": "female"},
        "Cardiac_Stress_Test": {"age_range": (40, 80), "frequency_years": 5, "gender": "both"}
    }
    
    for procedure_name, guidelines in screening_guidelines.items():
        age_min, age_max = guidelines["age_range"]
        required_gender = guidelines["gender"]
        
        # Check if patient meets screening criteria
        if age_min <= age <= age_max:
            if required_gender == "both" or gender == required_gender:
                # 70% chance of having age-appropriate screening
                if random.random() < 0.7:
                    enc = random.choice(encounters) if encounters else None
                    date = enc["date"] if enc else patient["birthdate"]
                    
                    # Find CPT code from clinical procedures
                    cpt_code = find_procedure_cpt(procedure_name)
                    
                    procedures.append({
                        "procedure_id": str(uuid.uuid4()),
                        "patient_id": patient["patient_id"],
                        "encounter_id": enc["encounter_id"] if enc else None,
                        "name": procedure_name,
                        "cpt_code": cpt_code,
                        "specialty": "Preventive_Medicine",
                        "category": "screening",
                        "complexity": "routine",
                        "indication": "routine_screening",
                        "date": date,
                        "outcome": "normal" if random.random() < 0.85 else "abnormal",
                    })
    
    return procedures

def generate_random_procedure(patient, encounters):
    """Generate random procedure from legacy list for variety"""
    enc = random.choice(encounters) if encounters else None
    date = enc["date"] if enc else patient["birthdate"]
    
    # Use legacy procedure list for backward compatibility
    procedure_name = random.choice(PROCEDURES)
    
    return {
        "procedure_id": str(uuid.uuid4()),
        "patient_id": patient["patient_id"],
        "encounter_id": enc["encounter_id"] if enc else None,
        "name": procedure_name,
        "cpt_code": "",  # Legacy procedures don't have CPT codes
        "specialty": "General",
        "category": "other",
        "complexity": "routine",
        "indication": "clinical_judgment",
        "date": date,
        "outcome": random.choice(["successful", "complication", "failed"]),
    }

def generate_procedure_outcome(complexity, age):
    """Generate realistic procedure outcomes based on complexity and patient age"""
    base_success_rate = 0.95
    
    # Adjust success rate based on complexity
    complexity_adjustment = {
        "routine": 0.0,
        "moderate": -0.05,
        "high": -0.10,
        "very_high": -0.20
    }
    
    # Adjust success rate based on age (older patients have higher complication rates)
    age_adjustment = 0.0
    if age >= 65:
        age_adjustment = -0.05
    elif age >= 80:
        age_adjustment = -0.10
    
    final_success_rate = base_success_rate + complexity_adjustment.get(complexity, 0) + age_adjustment
    
    rand = random.random()
    if rand < final_success_rate:
        return "successful"
    elif rand < final_success_rate + 0.03:  # 3% complication rate
        return "complication"
    else:
        return "failed"

def find_procedure_cpt(procedure_name):
    """Find CPT code for a procedure"""
    for specialty, procedure_categories in CLINICAL_PROCEDURES.items():
        for category, procedure_list in procedure_categories.items():
            for procedure in procedure_list:
                if procedure_name.lower() in procedure["name"].lower():
                    return procedure.get("cpt", "")
    return ""

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

# PHASE 2: Enhanced observation generation with comprehensive lab panels
def generate_observations(patient, encounters, conditions=None, min_obs=1, max_obs=8):
    observations = []
    age = patient.get("age", 30)
    gender = patient.get("gender", "")
    
    # Determine appropriate lab panels based on conditions and demographics
    required_panels = determine_lab_panels(patient, conditions)
    
    # Generate condition-specific lab panels
    for panel_name in required_panels:
        panel_observations = generate_lab_panel(patient, encounters, panel_name, age, gender)
        observations.extend(panel_observations)
    
    # Add routine vitals and basic observations
    routine_obs = generate_routine_observations(patient, encounters, min_obs, max_obs)
    observations.extend(routine_obs)
    
    return observations

def determine_lab_panels(patient, conditions):
    """Determine which lab panels are clinically appropriate"""
    panels = set()
    age = patient.get("age", 30)
    
    # Age-based routine screening
    if age >= 18:
        panels.add("Basic_Metabolic_Panel")
    if age >= 20:
        panels.add("Lipid_Panel")
    if age >= 30:
        panels.add("Complete_Blood_Count")
    
    # Condition-based lab panels
    if conditions:
        for condition in conditions:
            condition_name = condition["name"]
            complexity_model = CONDITION_COMPLEXITY_MODELS.get(condition_name, {})
            
            if condition_name == "Diabetes":
                panels.add("Diabetes_Monitoring")
                panels.add("Basic_Metabolic_Panel")
                panels.add("Lipid_Panel")
            elif condition_name in ["Heart Disease", "Hypertension"]:
                panels.add("Lipid_Panel")
                panels.add("Cardiac_Markers")
            elif condition_name == "Cancer":
                panels.add("Complete_Blood_Count")
                panels.add("Liver_Function_Panel")
            elif "Thyroid" in condition_name or random.random() < 0.1:  # 10% get thyroid screening
                panels.add("Thyroid_Function")
    
    # Random additional panels (simulate clinical judgment)
    if random.random() < 0.3:  # 30% chance of inflammatory markers
        panels.add("Inflammatory_Markers")
    
    return list(panels)

def generate_lab_panel(patient, encounters, panel_name, age, gender):
    """Generate all tests in a specific lab panel"""
    panel_data = COMPREHENSIVE_LAB_PANELS.get(panel_name, {})
    tests = panel_data.get("tests", [])
    observations = []
    
    for test in tests:
        test_name = test["name"]
        value = generate_lab_value(test_name, age, gender, test)
        
        # Select appropriate encounter
        enc = random.choice(encounters) if encounters else None
        date = enc["date"] if enc else patient["birthdate"]
        
        # Determine if value is critical
        is_critical = is_critical_value(value, test)
        status = "critical" if is_critical else "normal" if is_normal_value(value, test, age, gender) else "abnormal"
        
        observations.append({
            "observation_id": str(uuid.uuid4()),
            "patient_id": patient["patient_id"],
            "encounter_id": enc["encounter_id"] if enc else None,
            "type": test_name,
            "loinc_code": test.get("loinc", ""),
            "value": value,
            "units": test.get("units", ""),
            "reference_range": get_reference_range_string(test, age, gender),
            "status": status,
            "date": date,
            "panel": panel_name
        })
    
    return observations

def generate_lab_value(test_name, age, gender, test_config):
    """Generate clinically realistic lab values"""
    normal_range = get_adjusted_normal_range(test_name, age, gender, test_config)
    
    # 85% of values should be normal, 10% slightly abnormal, 5% significantly abnormal
    rand = random.random()
    
    if rand < 0.85:  # Normal values
        return round(random.uniform(normal_range[0], normal_range[1]), 2)
    elif rand < 0.95:  # Slightly abnormal
        if random.random() < 0.5:  # Below normal
            low_abnormal = normal_range[0] * 0.8
            return round(random.uniform(low_abnormal, normal_range[0]), 2)
        else:  # Above normal
            high_abnormal = normal_range[1] * 1.2
            return round(random.uniform(normal_range[1], high_abnormal), 2)
    else:  # Significantly abnormal
        critical_low = test_config.get("critical_low")
        critical_high = test_config.get("critical_high")
        
        if random.random() < 0.5 and critical_low:  # Critically low
            return round(random.uniform(critical_low, normal_range[0] * 0.7), 2)
        elif critical_high:  # Critically high
            return round(random.uniform(normal_range[1] * 1.5, critical_high), 2)
        else:
            return round(random.uniform(normal_range[0], normal_range[1]), 2)

def get_adjusted_normal_range(test_name, age, gender, test_config):
    """Get age/gender adjusted reference ranges"""
    base_range = test_config.get("normal_range", (0, 100))
    
    # Check for age/gender adjustments
    adjustments = AGE_GENDER_ADJUSTMENTS.get(test_name, {})
    
    if gender in adjustments:
        return adjustments[gender].get("normal_range", base_range)
    elif age >= 65 and "elderly" in adjustments:
        return adjustments["elderly"].get("normal_range", base_range)
    elif age < 18 and "pediatric" in adjustments:
        return adjustments["pediatric"].get("normal_range", base_range)
    elif age >= 18 and "adult" in adjustments:
        return adjustments["adult"].get("normal_range", base_range)
    
    return base_range

def is_critical_value(value, test_config):
    """Determine if a lab value is critical"""
    critical_low = test_config.get("critical_low")
    critical_high = test_config.get("critical_high")
    
    if critical_low and value <= critical_low:
        return True
    if critical_high and value >= critical_high:
        return True
    
    return False

def is_normal_value(value, test_config, age, gender):
    """Determine if a lab value is within normal range"""
    normal_range = get_adjusted_normal_range(test_config["name"], age, gender, test_config)
    return normal_range[0] <= value <= normal_range[1]

def get_reference_range_string(test_config, age, gender):
    """Generate reference range string for display"""
    normal_range = get_adjusted_normal_range(test_config["name"], age, gender, test_config)
    units = test_config.get("units", "")
    return f"{normal_range[0]}-{normal_range[1]} {units}".strip()

def generate_routine_observations(patient, encounters, min_obs, max_obs):
    """Generate basic vital signs and measurements"""
    n = random.randint(min_obs, max_obs)
    observations = []
    
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

# PHASE 1: Clinically accurate death generation with ICD-10-CM coding
def generate_death(patient, conditions=None, family_history=None):
    """Generate clinically accurate death with proper ICD-10-CM coding and age stratification"""
    # Simulate a 10% chance of death for realism
    if random.random() < 0.1:
        age = patient.get("age", 0)
        gender = patient.get("gender", "")
        birth = datetime.strptime(patient["birthdate"], "%Y-%m-%d").date()
        
        # Calculate death date
        min_death_age = max(1, int(age * 0.5))
        death_age = random.randint(min_death_age, age) if age > 1 else 1
        death_date = birth + timedelta(days=death_age * 365)
        if death_date > datetime.now().date():
            death_date = datetime.now().date()
        
        # Determine age-appropriate death causes
        age_group = None
        for (min_age, max_age), causes in DEATH_CAUSES_BY_AGE.items():
            if min_age <= age <= max_age:
                age_group = (min_age, max_age)
                break
        
        if not age_group:
            # Default to elderly causes for very old patients
            age_group = (65, 120)
        
        age_appropriate_causes = DEATH_CAUSES_BY_AGE[age_group]
        
        # Check for condition-specific death risk
        death_risk_multiplier = 1.0
        likely_causes = []
        contributing_causes = []
        
        if conditions:
            for condition in conditions:
                risk_data = CONDITION_MORTALITY_RISK.get(condition["name"], {})
                death_risk_multiplier *= risk_data.get("relative_risk", 1.0)
                
                # Add condition-specific death causes
                condition_deaths = risk_data.get("likely_deaths", [])
                likely_causes.extend(condition_deaths)
                
                # Track contributing causes
                contributing_causes.append(condition["name"])
        
        # Select primary cause of death with proper weighting
        if likely_causes and random.random() < 0.7:  # 70% chance of condition-related death
            primary_cause = weighted_choice(likely_causes)
        else:
            primary_cause = weighted_choice(age_appropriate_causes)
        
        # Determine manner of death based on ICD-10 code
        manner_of_death = "Natural"
        if primary_cause["icd10"].startswith(("V", "W", "X", "Y")):
            if primary_cause["icd10"].startswith("X8"):  # Intentional self-harm
                manner_of_death = "Suicide"
            elif primary_cause["icd10"].startswith("X9") or primary_cause["icd10"].startswith("Y0"):  # Assault
                manner_of_death = "Homicide"
            else:
                manner_of_death = "Accident"
        
        return {
            "patient_id": patient["patient_id"],
            "death_date": death_date.isoformat(),
            "age_at_death": death_age,
            "primary_cause_code": primary_cause["icd10"],
            "primary_cause_description": primary_cause["description"],
            "contributing_causes": "; ".join(contributing_causes[:3]),  # Flatten list to string for CSV
            "manner_of_death": manner_of_death,
            "death_certificate_type": "Standard" if manner_of_death == "Natural" else "Coroner"
        }
    else:
        return None

def weighted_choice(choices):
    """Select an item from choices based on weight"""
    total = sum(choice["weight"] for choice in choices)
    r = random.uniform(0, total)
    upto = 0
    for choice in choices:
        if upto + choice["weight"] >= r:
            return choice
        upto += choice["weight"]
    return choices[-1]  # Fallback

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
    
    # Migration simulation arguments
    parser.add_argument("--simulate-migration", action="store_true", help="Enable migration simulation")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for migration simulation")
    parser.add_argument("--migration-strategy", type=str, default="staged", 
                       choices=["staged", "big_bang", "parallel"], help="Migration strategy")
    parser.add_argument("--migration-report", type=str, default=None, help="Output migration report file")
    
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
        """Generate patient with distribution constraints using PatientRecord class"""
        # Age bin
        age_bin_label = sample_from_dist(age_dist)
        a_min, a_max = map(int, age_bin_label.split("-"))
        age = random.randint(a_min, a_max)
        birthdate = datetime.now().date() - timedelta(days=age * 365)
        income = random.randint(0, 200000) if age >= 18 else 0
        gender = sample_from_dist(gender_dist)
        race = sample_from_dist(race_dist)
        smoking_status = sample_from_dist(smoking_dist)
        alcohol_use = sample_from_dist(alcohol_dist)
        education = sample_from_dist(education_dist) if age >= 18 else "None"
        employment_status = sample_from_dist(employment_dist) if age >= 16 else "Student"
        housing_status = sample_from_dist(housing_dist)
        
        patient = PatientRecord(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            middle_name=fake.first_name()[:1],  # Simple middle initial
            gender=gender,
            birthdate=birthdate.isoformat(),
            age=age,
            race=race,
            ethnicity=random.choice(ETHNICITIES),
            address=fake.street_address(),
            city=fake.city(),
            state=fake.state_abbr(),
            zip=fake.zipcode(),
            country="US",
            phone=fake.phone_number(),
            email=fake.email(),
            marital_status=random.choice(MARITAL_STATUSES),
            language=random.choice(LANGUAGES),
            insurance=random.choice(INSURANCES),
            ssn=fake.ssn(),
            # SDOH fields
            smoking_status=smoking_status,
            alcohol_use=alcohol_use,
            education=education,
            employment_status=employment_status,
            income=income,
            housing_status=housing_status,
        )
        
        # Generate healthcare IDs
        patient.generate_vista_id()
        patient.generate_mrn()
        
        return patient

    print(f"Generating {num_records} patients and related tables in parallel...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        patients = list(tqdm(
            executor.map(generate_patient_with_dist, range(num_records)), 
            total=num_records,
            desc="Generating patients",
            unit="patients"
        ))

    all_encounters = []
    all_conditions = []
    all_medications = []
    all_allergies = []
    all_procedures = []
    all_immunizations = []
    all_observations = []
    all_deaths = []
    all_family_history = []

    print("Generating related healthcare data...")
    for patient in tqdm(patients, desc="Generating healthcare data", unit="patients"):
        # Convert PatientRecord to dict for backward compatibility with existing functions
        patient_dict = patient.to_dict()
        
        conditions = generate_conditions(patient_dict, [], min_cond=1, max_cond=5)
        encounters = generate_encounters(patient_dict, conditions)
        all_encounters.extend(encounters)
        for cond in conditions:
            enc = random.choice(encounters) if encounters else None
            cond["encounter_id"] = enc["encounter_id"] if enc else None
            cond["onset_date"] = enc["date"] if enc else patient_dict["birthdate"]
        all_conditions.extend(conditions)
        all_medications.extend(generate_medications(patient_dict, encounters, conditions))
        all_allergies.extend(generate_allergies(patient_dict))
        all_procedures.extend(generate_procedures(patient_dict, encounters, conditions))
        all_immunizations.extend(generate_immunizations(patient_dict, encounters))
        all_observations.extend(generate_observations(patient_dict, encounters, conditions))
        death = generate_death(patient_dict, conditions)
        if death:
            all_deaths.append(death)
        all_family_history.extend(generate_family_history(patient_dict))

    def save(df, name):
        if output_csv:
            df.write_csv(os.path.join(output_dir, f"{name}.csv"))
        if output_parquet:
            df.write_parquet(os.path.join(output_dir, f"{name}.parquet"))
    
    def save_fhir_bundle(patients_list, conditions_list, filename="fhir_bundle.json"):
        """Save FHIR bundle with Patient and Condition resources"""
        import json
        
        fhir_formatter = FHIRFormatter()
        bundle_entries = []
        
        # Add Patient resources
        for patient in tqdm(patients_list, desc="Creating FHIR Patient resources", unit="patients"):
            patient_resource = fhir_formatter.create_patient_resource(patient)
            bundle_entries.append({"resource": patient_resource})
        
        # Add Condition resources
        for condition in tqdm(conditions_list, desc="Creating FHIR Condition resources", unit="conditions"):
            condition_resource = fhir_formatter.create_condition_resource(
                condition.get('patient_id'), condition
            )
            bundle_entries.append({"resource": condition_resource})
        
        # Create FHIR Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": datetime.now().isoformat(),
            "entry": bundle_entries
        }
        
        # Save to file
        with open(os.path.join(output_dir, filename), 'w') as f:
            json.dump(fhir_bundle, f, indent=2)
        
        print(f"FHIR Bundle saved: {filename} ({len(bundle_entries)} resources)")
    
    def save_hl7_messages(patients_list, encounters_list, observations_list, filename_prefix="hl7_messages"):
        """Save HL7 v2 messages (ADT and ORU)"""
        hl7_formatter = HL7v2Formatter()
        validator = HL7MessageValidator()
        
        adt_messages = []
        oru_messages = []
        validation_results = []
        
        # Create ADT messages for each patient
        for patient in tqdm(patients_list, desc="Creating HL7 ADT messages", unit="patients"):
            # Get encounters for this patient
            patient_encounters = [enc for enc in encounters_list if enc.get('patient_id') == patient.patient_id]
            
            if patient_encounters:
                # Create ADT message with first encounter
                encounter = patient_encounters[0]
                adt_message = hl7_formatter.create_adt_message(patient, encounter, "A04")
            else:
                # Create ADT message without encounter
                adt_message = hl7_formatter.create_adt_message(patient, None, "A04")
            
            adt_messages.append(adt_message)
            
            # Validate ADT message
            validation = validator.validate_message_structure(adt_message)
            validation_results.append({
                "patient_id": patient.patient_id,
                "message_type": "ADT",
                "valid": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            })
        
        # Create ORU messages for patients with observations
        patient_obs_map = {}
        for obs in observations_list:
            patient_id = obs.get('patient_id')
            if patient_id not in patient_obs_map:
                patient_obs_map[patient_id] = []
            patient_obs_map[patient_id].append(obs)
        
        for patient in tqdm(patients_list, desc="Creating HL7 ORU messages", unit="patients"):
            patient_observations = patient_obs_map.get(patient.patient_id, [])
            if patient_observations:
                oru_message = hl7_formatter.create_oru_message(patient, patient_observations)
                oru_messages.append(oru_message)
                
                # Validate ORU message
                validation = validator.validate_message_structure(oru_message)
                validation_results.append({
                    "patient_id": patient.patient_id,
                    "message_type": "ORU",
                    "valid": validation["valid"],
                    "errors": validation["errors"],
                    "warnings": validation["warnings"]
                })
        
        # Save ADT messages
        if adt_messages:
            with open(os.path.join(output_dir, f"{filename_prefix}_adt.hl7"), 'w') as f:
                f.write('\n'.join(adt_messages))
            print(f"HL7 ADT messages saved: {filename_prefix}_adt.hl7 ({len(adt_messages)} messages)")
        
        # Save ORU messages  
        if oru_messages:
            with open(os.path.join(output_dir, f"{filename_prefix}_oru.hl7"), 'w') as f:
                f.write('\n'.join(oru_messages))
            print(f"HL7 ORU messages saved: {filename_prefix}_oru.hl7 ({len(oru_messages)} messages)")
        
        # Save validation results
        if validation_results:
            import json
            with open(os.path.join(output_dir, f"{filename_prefix}_validation.json"), 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            # Print validation summary
            valid_count = sum(1 for r in validation_results if r["valid"])
            total_count = len(validation_results)
            print(f"HL7 Validation: {valid_count}/{total_count} messages valid")

    # Convert PatientRecord objects to dictionaries for DataFrame creation
    print("Converting patient records to dictionaries...")
    patients_dict = [patient.to_dict() for patient in tqdm(patients, desc="Converting patients", unit="patients")]
    
    print("Saving data files...")
    tables_to_save = [
        (pl.DataFrame(patients_dict), "patients"),
        (pl.DataFrame(all_encounters), "encounters"),
        (pl.DataFrame(all_conditions), "conditions"),
        (pl.DataFrame(all_medications), "medications"),
        (pl.DataFrame(all_allergies), "allergies"),
        (pl.DataFrame(all_procedures), "procedures"),
        (pl.DataFrame(all_immunizations), "immunizations"),
        (pl.DataFrame(all_observations), "observations")
    ]
    
    if all_deaths:
        tables_to_save.append((pl.DataFrame(all_deaths), "deaths"))
    if all_family_history:
        tables_to_save.append((pl.DataFrame(all_family_history), "family_history"))
    
    for df, name in tqdm(tables_to_save, desc="Saving tables", unit="tables"):
        save(df, name)

    print("\nExporting specialized formats...")
    
    # Export FHIR bundle (Phase 1: basic Patient and Condition resources)
    print("Creating FHIR bundle...")
    save_fhir_bundle(patients, all_conditions, "fhir_bundle.json")
    
    # Export HL7 v2 messages (Phase 2: ADT and ORU messages)
    print("Creating HL7 v2 messages...")
    save_hl7_messages(patients, all_encounters, all_observations, "hl7_messages")
    
    # Export VistA MUMPS globals (Phase 3: VA migration simulation)
    print("Creating VistA MUMPS globals...")
    vista_formatter = VistaFormatter()
    vista_output_file = os.path.join(output_dir, "vista_globals.mumps")
    vista_stats = vista_formatter.export_vista_globals(patients, all_encounters, all_conditions, vista_output_file)

    print(f"Done! Files written to {output_dir}: patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history (CSV and/or Parquet), FHIR bundle, HL7 messages, VistA MUMPS globals")

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
    
    # VistA MUMPS global statistics
    report_lines.append("")
    report_lines.append("VistA MUMPS Global Export Summary:")
    report_lines.append(f"  Total global nodes: {vista_stats['total_globals']}")
    report_lines.append(f"  Patient records (^DPT): {vista_stats['patient_records']}")
    report_lines.append(f"  Visit records (^AUPNVSIT): {vista_stats['visit_records']}")
    report_lines.append(f"  Problem records (^AUPNPROB): {vista_stats['problem_records']}")
    report_lines.append(f"  Cross-references: {vista_stats['cross_references']}")
    
    report = "\n".join(report_lines)
    print_and_save_report(report, get_config('report_file', None))
    
    # Phase 4: Migration Simulation
    if get_config('simulate_migration', False):
        print("\n" + "="*60)
        print("PHASE 4: MIGRATION SIMULATION")
        print("="*60)
        
        # Initialize migration simulator with configuration
        migration_config = MigrationConfig()
        
        # Override config from YAML if available
        if 'migration_settings' in config:
            migration_settings = config['migration_settings']
            if 'success_rates' in migration_settings:
                migration_config.stage_success_rates.update(migration_settings['success_rates'])
            if 'network_failure_rate' in migration_settings:
                migration_config.network_failure_rate = migration_settings['network_failure_rate']
            if 'system_overload_rate' in migration_settings:
                migration_config.system_overload_rate = migration_settings['system_overload_rate']
        
        simulator = MigrationSimulator(migration_config)
        
        # Get migration parameters
        batch_size = get_config('batch_size', 100)
        migration_strategy = get_config('migration_strategy', 'staged')
        migration_report_file = get_config('migration_report', None)
        
        print(f"Simulating migration for {len(patients)} patients...")
        print(f"Batch size: {batch_size}")
        print(f"Strategy: {migration_strategy}")
        print("")
        
        # Process patients in batches
        migration_results = []
        total_batches = (len(patients) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(patients))
            batch_patients = patients[start_idx:end_idx]
            
            batch_id = f"batch_{batch_num + 1:03d}"
            print(f"Processing {batch_id}: {len(batch_patients)} patients...")
            
            # Simulate migration for this batch
            batch_result = simulator.simulate_staged_migration(
                batch_patients, 
                batch_id=batch_id,
                migration_strategy=migration_strategy
            )
            migration_results.append(batch_result)
            
            # Print batch summary
            print(f"  - Overall Success Rate: {batch_result.overall_success_rate:.1%}")
            print(f"  - Average Quality Score: {batch_result.average_quality_score:.3f}")
            print(f"  - Failed Patients: {batch_result.total_errors}")
            
            # Show any failed stages
            failed_stages = [r for r in batch_result.stage_results if r.status == "partial_failure"]
            if failed_stages:
                print(f"  - Failures in stages: {', '.join(set(r.stage for r in failed_stages))}")
            print("")
        
        # Generate comprehensive analytics
        print("Generating migration analytics...")
        analytics = simulator.get_migration_analytics()
        
        # Print executive summary
        print("\nMIGRATION EXECUTIVE SUMMARY")
        print("-" * 40)
        summary = analytics["summary"]
        print(f"Total Batches: {summary['total_batches']}")
        print(f"Total Patients: {summary['total_patients']}")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.1%}")
        print(f"Average Data Quality: {summary['average_quality_score']:.3f}")
        print(f"Total Errors: {summary['total_errors']}")
        
        # Stage performance summary
        if "stage_performance" in analytics:
            print("\nSTAGE PERFORMANCE")
            print("-" * 40)
            for stage, stats in analytics["stage_performance"].items():
                print(f"{stage.upper()}: {stats['success_rate']:.1%} success, "
                      f"{stats['average_duration']:.1f}s avg duration")
        
        # Failure analysis summary
        if "failure_analysis" in analytics and analytics["failure_analysis"]["failure_types"]:
            print("\nTOP FAILURE TYPES")
            print("-" * 40)
            failure_types = analytics["failure_analysis"]["failure_types"]
            for failure_type, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"{failure_type}: {count} occurrences")
        
        # Recommendations
        if "recommendations" in analytics:
            print("\nRECOMMENDAYIONS")
            print("-" * 40)
            for i, rec in enumerate(analytics["recommendations"][:3], 1):
                print(f"{i}. {rec}")
        
        # Export detailed migration report if requested
        if migration_report_file:
            report_path = os.path.join(output_dir, migration_report_file)
            simulator.export_migration_report(report_path)
            print(f"\nDetailed migration report saved to: {report_path}")
        
        # Save migration data quality metrics to file
        migration_quality_file = os.path.join(output_dir, "migration_quality_report.json")
        import json
        quality_data = {
            "migration_summary": analytics["summary"],
            "stage_performance": analytics["stage_performance"],
            "quality_trends": analytics["quality_trends"],
            "patient_quality_scores": [
                {
                    "patient_id": p.patient_id,
                    "initial_quality": 1.0,
                    "final_quality": p.metadata["data_quality_score"],
                    "quality_degradation": 1.0 - p.metadata["data_quality_score"],
                    "migration_status": p.metadata["migration_status"]
                }
                for p in patients
            ]
        }
        
        with open(migration_quality_file, 'w') as f:
            json.dump(quality_data, f, indent=2)
        
        print(f"Migration quality metrics saved to: migration_quality_report.json")
        print("\nMigration simulation completed successfully!")
    
    else:
        print("\nSkipping migration simulation (use --simulate-migration to enable)")
    
    print(f"\nAll outputs saved to: {output_dir}")
    print("Generation completed successfully!")

if __name__ == "__main__":
    main() 