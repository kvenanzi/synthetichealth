"""Terminology catalogs for Phase 5 terminology normalization.

Each catalog entry includes authoritative code systems to enable
interoperable exports across CSV, FHIR, HL7 v2, and VistA artifacts.
"""

CONDITIONS = [
    {
        "display": "Hypertension",
        "icd10": "I10",
        "snomed": "38341003",
        "category": "cardiometabolic"
    },
    {
        "display": "Diabetes",
        "icd10": "E11.9",
        "snomed": "44054006",
        "category": "cardiometabolic"
    },
    {
        "display": "Heart Disease",
        "icd10": "I25.10",
        "snomed": "53741008",
        "category": "cardiology"
    },
    {
        "display": "Heart Failure",
        "icd10": "I50.9",
        "snomed": "84114007",
        "category": "cardiology"
    },
    {
        "display": "Obesity",
        "icd10": "E66.9",
        "snomed": "414916001",
        "category": "cardiometabolic"
    },
    {
        "display": "COPD",
        "icd10": "J44.1",
        "snomed": "13645005",
        "category": "pulmonology"
    },
    {
        "display": "Asthma",
        "icd10": "J45.909",
        "snomed": "195967001",
        "category": "pulmonology"
    },
    {
        "display": "Depression",
        "icd10": "F33.1",
        "snomed": "370143000",
        "category": "behavioral_health"
    },
    {
        "display": "Anxiety",
        "icd10": "F41.1",
        "snomed": "21897009",
        "category": "behavioral_health"
    },
    {
        "display": "Cancer",
        "icd10": "C50.911",
        "snomed": "254837009",
        "category": "oncology"
    },
    {
        "display": "Arthritis",
        "icd10": "M19.90",
        "snomed": "3723001",
        "category": "musculoskeletal"
    },
    {
        "display": "Flu",
        "icd10": "J10.1",
        "snomed": "6142004",
        "category": "infectious_disease"
    },
    {
        "display": "Allergy",
        "icd10": "T78.40XA",
        "snomed": "419199007",
        "category": "immunology"
    },
    {
        "display": "Migraine",
        "icd10": "G43.909",
        "snomed": "37796009",
        "category": "neurology"
    },
    {
        "display": "COVID-19",
        "icd10": "U07.1",
        "snomed": "840539006",
        "category": "infectious_disease"
    }
]

MEDICATIONS = [
    {
        "display": "Metformin",
        "rxnorm": "860975",
        "ndc": "00093-1048-01",
        "therapeutic_class": "antidiabetic"
    },
    {
        "display": "Lisinopril",
        "rxnorm": "617314",
        "ndc": "54868-5996-00",
        "therapeutic_class": "ace_inhibitor"
    },
    {
        "display": "Atorvastatin",
        "rxnorm": "83367",
        "ndc": "00006-0275-23",
        "therapeutic_class": "statin"
    },
    {
        "display": "Insulin",
        "rxnorm": "847232",
        "ndc": "00008-2219-05",
        "therapeutic_class": "basal_insulin"
    },
    {
        "display": "Osimertinib",
        "rxnorm": "1747429",
        "ndc": "00310-6790-30",
        "therapeutic_class": "tyrosine_kinase_inhibitor"
    },
    {
        "display": "Trastuzumab",
        "rxnorm": "1652395",
        "ndc": "50242-0135-68",
        "therapeutic_class": "monoclonal_antibody"
    },
    {
        "display": "Mepolizumab",
        "rxnorm": "1719334",
        "ndc": "00173-0881-01",
        "therapeutic_class": "biologic"
    },
    {
        "display": "Sertraline",
        "rxnorm": "312941",
        "ndc": "00049-4900-30",
        "therapeutic_class": "ssri"
    },
    {"display": "Hydrochlorothiazide", "rxnorm": "316047", "ndc": "00143-9886-90", "therapeutic_class": "diuretic"},
    {"display": "Metoprolol", "rxnorm": "866350", "ndc": "00069-0213-40", "therapeutic_class": "beta_blocker"},
    {"display": "Losartan", "rxnorm": "979664", "ndc": "65862-0051-90", "therapeutic_class": "arb"},
    {"display": "Indapamide", "rxnorm": "197256", "ndc": "51285-0117-02", "therapeutic_class": "diuretic"},
    {"display": "Glipizide", "rxnorm": "205910", "ndc": "00039-0051-10", "therapeutic_class": "sulfonylurea"},
    {"display": "Sitagliptin", "rxnorm": "861035", "ndc": "00006-0586-61", "therapeutic_class": "dpp4_inhibitor"},
    {"display": "Empagliflozin", "rxnorm": "1551306", "ndc": "00597-0194-80", "therapeutic_class": "sglt2_inhibitor"},
    {"display": "Insulin_glargine", "rxnorm": "847232", "ndc": "00008-2219-05", "therapeutic_class": "basal_insulin"},
    {"display": "Insulin_lispro", "rxnorm": "863678", "ndc": "00002-7501-01", "therapeutic_class": "rapid_insulin"},
    {"display": "Albuterol", "rxnorm": "435", "ndc": "00378-6501-93", "therapeutic_class": "bronchodilator"},
    {"display": "Fluticasone", "rxnorm": "865098", "ndc": "00591-2740-40", "therapeutic_class": "inhaled_steroid"},
    {"display": "Budesonide/Formoterol", "rxnorm": "859038", "ndc": "00186-0370-08", "therapeutic_class": "combination_inhaler"},
    {"display": "Aspirin", "rxnorm": "1191", "ndc": "00573-2675-01", "therapeutic_class": "antiplatelet"},
    {"display": "Clopidogrel", "rxnorm": "309362", "ndc": "63629-0948-01", "therapeutic_class": "antiplatelet"},
    {"display": "Ibuprofen", "rxnorm": "5640", "ndc": "00536-0029-10", "therapeutic_class": "nsaid"},
    {"display": "Naproxen", "rxnorm": "7771", "ndc": "00378-6130-01", "therapeutic_class": "nsaid"},
    {"display": "Celecoxib", "rxnorm": "549697", "ndc": "00037-0225-60", "therapeutic_class": "nsaid"},
    {"display": "Methotrexate", "rxnorm": "1037", "ndc": "00054-4582-25", "therapeutic_class": "dmard"},
    {"display": "Hydroxychloroquine", "rxnorm": "9790", "ndc": "00069-3060-66", "therapeutic_class": "dmard"},
    {"display": "Adalimumab", "rxnorm": "784791", "ndc": "00781-4002-20", "therapeutic_class": "biologic"},
    {"display": "Etanercept", "rxnorm": "180325", "ndc": "58406-0423-04", "therapeutic_class": "biologic"},
    {"display": "Loratadine", "rxnorm": "211789", "ndc": "41163-0312-45", "therapeutic_class": "antihistamine"},
    {"display": "Cetirizine", "rxnorm": "199222", "ndc": "50580-0727-10", "therapeutic_class": "antihistamine"},
    {"display": "Fexofenadine", "rxnorm": "966713", "ndc": "63629-0301-01", "therapeutic_class": "antihistamine"},
    {"display": "Fluticasone_nasal", "rxnorm": "1595587", "ndc": "60505-0837-0", "therapeutic_class": "nasal_steroid"},
    {"display": "Mometasone_nasal", "rxnorm": "1799150", "ndc": "00006-4095-63", "therapeutic_class": "nasal_steroid"},
    {"display": "Epinephrine", "rxnorm": "6367", "ndc": "00085-4325-01", "therapeutic_class": "emergency"},
    {"display": "Warfarin", "rxnorm": "855332", "ndc": "00591-0460-01", "therapeutic_class": "anticoagulant"},
    {"display": "Apixaban", "rxnorm": "1365001", "ndc": "00003-0894-21", "therapeutic_class": "anticoagulant"},
    {"display": "Rivaroxaban", "rxnorm": "1359036", "ndc": "50458-0570-90", "therapeutic_class": "anticoagulant"},
    {"display": "Sumatriptan", "rxnorm": "313782", "ndc": "00173-0470-00", "therapeutic_class": "triptan"},
    {"display": "Rizatriptan", "rxnorm": "312961", "ndc": "78206-1433-01", "therapeutic_class": "triptan"},
    {"display": "Propranolol", "rxnorm": "856874", "ndc": "00054-4737-63", "therapeutic_class": "beta_blocker"},
    {"display": "Topiramate", "rxnorm": "90039", "ndc": "00054-0086-25", "therapeutic_class": "antiepileptic"},
    {"display": "Amitriptyline", "rxnorm": "856838", "ndc": "54569-6170-00", "therapeutic_class": "antidepressant"},
    {"display": "Buspirone", "rxnorm": "20610", "ndc": "00527-1382-01", "therapeutic_class": "anxiolytic"},
    {"display": "Paroxetine", "rxnorm": "7987", "ndc": "00093-3131-56", "therapeutic_class": "ssri"},
    {"display": "Venlafaxine", "rxnorm": "1086784", "ndc": "00093-5410-56", "therapeutic_class": "snri"},
    {"display": "Duloxetine", "rxnorm": "724366", "ndc": "00054-4152-25", "therapeutic_class": "snri"},
    {"display": "Bupropion", "rxnorm": "42347", "ndc": "00172-5311-60", "therapeutic_class": "antidepressant"},
    {"display": "Mirtazapine", "rxnorm": "211190", "ndc": "00093-5263-05", "therapeutic_class": "antidepressant"},
    {"display": "Lorazepam", "rxnorm": "2839", "ndc": "00093-7737-01", "therapeutic_class": "benzodiazepine"},
    {"display": "Alprazolam", "rxnorm": "213702", "ndc": "00093-5330-01", "therapeutic_class": "benzodiazepine"},
    {"display": "Paclitaxel", "rxnorm": "197932", "ndc": "16729-0102-11", "therapeutic_class": "chemotherapy"},
    {"display": "Ondansetron", "rxnorm": "312615", "ndc": "00054-4729-25", "therapeutic_class": "antiemetic"},
    {"display": "Dexamethasone", "rxnorm": "197862", "ndc": "00009-0343-01", "therapeutic_class": "steroid"},
    {"display": "Filgrastim", "rxnorm": "111419", "ndc": "55513-0192-01", "therapeutic_class": "growth_factor"},
    {"display": "Paxlovid", "rxnorm": "2572862", "ndc": "00069-1085-30", "therapeutic_class": "antiviral"},
    {"display": "Remdesivir", "rxnorm": "2284718", "ndc": "61958-2901-01", "therapeutic_class": "antiviral"},
    {"display": "Acetaminophen", "rxnorm": "161", "ndc": "50580-4876-01", "therapeutic_class": "analgesic"},
    {"display": "Oseltamivir", "rxnorm": "362666", "ndc": "54868-6053-00", "therapeutic_class": "antiviral"},
    {"display": "Zanamivir", "rxnorm": "316268", "ndc": "00173-0777-01", "therapeutic_class": "antiviral"}
]

IMMUNIZATIONS = [
    {"display": "Hepatitis B Vaccine", "cvx": "08", "snomed": "78778007", "rxnorm": ""},
    {"display": "DTaP Vaccine", "cvx": "20", "snomed": "333347000", "rxnorm": ""},
    {"display": "Inactivated Polio Vaccine", "cvx": "10", "snomed": "333341005", "rxnorm": ""},
    {"display": "Haemophilus influenzae type b Vaccine", "cvx": "49", "snomed": "409568008", "rxnorm": ""},
    {"display": "MMR Vaccine", "cvx": "03", "snomed": "333349002", "rxnorm": ""},
    {"display": "Varicella Vaccine", "cvx": "21", "snomed": "333344008", "rxnorm": ""},
    {"display": "HPV Vaccine", "cvx": "62", "snomed": "333358004", "rxnorm": ""},
    {"display": "Tdap Vaccine", "cvx": "115", "snomed": "871751000000109", "rxnorm": ""},
    {"display": "Seasonal Influenza Vaccine", "cvx": "140", "snomed": "86198006", "rxnorm": ""},
    {"display": "Pneumococcal Conjugate Vaccine", "cvx": "133", "snomed": "333353000", "rxnorm": ""},
    {"display": "COVID-19 mRNA Vaccine", "cvx": "207", "snomed": "1119349007", "rxnorm": ""},
    {"display": "Zoster Vaccine", "cvx": "187", "snomed": "871895005", "rxnorm": ""}
]

ALLERGENS = [
    {
        "display": "Penicillin",
        "rxnorm": "7982",
        "unii": "Q42T66VW0C"
    },
    {
        "display": "Peanut",
        "rxnorm": "4025294",
        "unii": "R16CO5Y76E"
    },
    {
        "display": "Latex",
        "rxnorm": "25755",
        "unii": "7RLR5T8Y9N"
    },
    {
        "display": "Shellfish",
        "rxnorm": "3196",
        "unii": "4A6XE3A25R"
    }
]

PROCEDURES = [
    {
        "display": "Colonoscopy",
        "cpt": "45378",
        "snomed": "73761001"
    },
    {
        "display": "Echocardiogram",
        "cpt": "93306",
        "snomed": "40701008"
    },
    {
        "display": "Cardiac Catheterization",
        "cpt": "93458",
        "snomed": "419209006"
    },
    {
        "display": "Chemotherapy Administration",
        "cpt": "96413",
        "snomed": "14734007"
    },
    {
        "display": "Pulmonary Function Test",
        "cpt": "94060",
        "snomed": "230056003"
    }
]

LAB_CODES = {
    "Hemoglobin_A1c": {
        "loinc": "4548-4",
        "display": "Hemoglobin A1c/Hemoglobin.total in Blood"
    },
    "LDL_Cholesterol": {
        "loinc": "2089-1",
        "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma"
    },
    "Troponin_T_High_Sensitivity": {
        "loinc": "67151-1",
        "display": "Troponin T.cardiac [Mass/volume] in Serum or Plasma by High sensitivity method"
    },
    "BNP": {
        "loinc": "30934-4",
        "display": "B-type natriuretic peptide [Mass/volume] in Blood"
    },
    "CA_125": {
        "loinc": "10334-1",
        "display": "Cancer Ag 125 [Units/volume] in Serum or Plasma"
    },
    "PHQ9_Score": {
        "loinc": "44249-1",
        "display": "PHQ-9 quick depression assessment panel"
    }
}
