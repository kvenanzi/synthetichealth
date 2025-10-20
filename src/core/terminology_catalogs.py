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
        "category": "cardiovascular"
    },
    {
        "display": "Heart Failure",
        "icd10": "I50.9",
        "snomed": "84114007",
        "category": "cardiovascular"
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
        "category": "respiratory"
    },
    {
        "display": "Asthma",
        "icd10": "J45.909",
        "snomed": "195967001",
        "category": "respiratory"
    },
    {
        "display": "Depression",
        "icd10": "F33.1",
        "snomed": "370143000",
        "category": "mental_health"
    },
    {
        "display": "Anxiety",
        "icd10": "F41.1",
        "snomed": "21897009",
        "category": "mental_health"
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
        "category": "factors_influencing"
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
    },
    {
        "display": "Chronic Kidney Disease",
        "icd10": "N18.9",
        "snomed": "709044004",
        "category": "renal"
    },
    {
        "display": "Hyperlipidemia",
        "icd10": "E78.5",
        "snomed": "55822004",
        "category": "cardiometabolic"
    },
    {
        "display": "Type 1 Diabetes Mellitus",
        "icd10": "E10.9",
        "snomed": "46635009",
        "category": "endocrine"
    },
    {
        "display": "Osteoarthritis of Knee",
        "icd10": "M17.10",
        "snomed": "239873007",
        "category": "musculoskeletal"
    },
    {
        "display": "Rheumatoid Arthritis",
        "icd10": "M06.9",
        "snomed": "69896004",
        "category": "musculoskeletal"
    },
    {
        "display": "Chronic Liver Disease",
        "icd10": "K76.9",
        "snomed": "328383001",
        "category": "gastroenterology"
    },
    {
        "display": "Hepatitis C",
        "icd10": "B18.2",
        "snomed": "233604007",
        "category": "infectious_disease"
    },
    {
        "display": "Chronic Pain Syndrome",
        "icd10": "G89.4",
        "snomed": "373621006",
        "category": "neurology"
    },
    {
        "display": "Bipolar Disorder",
        "icd10": "F31.9",
        "snomed": "13746004",
        "category": "mental_health"
    },
    {
        "display": "Schizophrenia",
        "icd10": "F20.9",
        "snomed": "58214004",
        "category": "mental_health"
    },
    {
        "display": "Substance Use Disorder",
        "icd10": "F19.20",
        "snomed": "66214007",
        "category": "mental_health"
    },
    {
        "display": "Obstructive Sleep Apnea",
        "icd10": "G47.33",
        "snomed": "1101000119105",
        "category": "respiratory"
    },
    {
        "display": "Psoriasis",
        "icd10": "L40.0",
        "snomed": "9014002",
        "category": "dermatology"
    },
    {
        "display": "Crohn Disease",
        "icd10": "K50.90",
        "snomed": "34000006",
        "category": "gastroenterology"
    },
    {
        "display": "Ulcerative Colitis",
        "icd10": "K51.90",
        "snomed": "64766004",
        "category": "gastroenterology"
    },
    {
        "display": "Gastroesophageal Reflux Disease",
        "icd10": "K21.9",
        "snomed": "235595009",
        "category": "gastroenterology"
    },
    {
        "display": "Chronic Migraine",
        "icd10": "G43.709",
        "snomed": "370530002",
        "category": "neurology"
    },
    {
        "display": "Hypothyroidism",
        "icd10": "E03.9",
        "snomed": "40930008",
        "category": "endocrine"
    },
    {
        "display": "Iron Deficiency Anemia",
        "icd10": "D50.9",
        "snomed": "87522002",
        "category": "hematologic"
    },
    {
        "display": "Chronic Kidney Disease Stage 3",
        "icd10": "N18.30",
        "snomed": "433144002",
        "category": "renal"
    },
    {
        "display": "Atrial Fibrillation",
        "icd10": "I48.91",
        "snomed": "49436004",
        "category": "cardiovascular"
    },
    {
        "display": "Peripheral Artery Disease",
        "icd10": "I73.9",
        "snomed": "399211009",
        "category": "cardiovascular"
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
    {"display": "Hepatitis B Vaccine", "cvx": "08", "snomed": "78778007", "rxnorm": "798428"},
    {"display": "DTaP Vaccine", "cvx": "20", "snomed": "333347000", "rxnorm": "1300310"},
    {"display": "Inactivated Polio Vaccine", "cvx": "10", "snomed": "333341005", "rxnorm": "763106"},
    {"display": "Haemophilus influenzae type b Vaccine", "cvx": "49", "snomed": "409568008", "rxnorm": "1300468"},
    {"display": "MMR Vaccine", "cvx": "03", "snomed": "333349002", "rxnorm": "804186"},
    {"display": "Varicella Vaccine", "cvx": "21", "snomed": "333344008", "rxnorm": "1292459"},
    {"display": "HPV Vaccine", "cvx": "62", "snomed": "333358004", "rxnorm": "1597099"},
    {"display": "Tdap Vaccine", "cvx": "115", "snomed": "871751000000109", "rxnorm": "1300370"},
    {"display": "Seasonal Influenza Vaccine", "cvx": "140", "snomed": "86198006", "rxnorm": "2605552"},
    {"display": "Pneumococcal Conjugate Vaccine", "cvx": "133", "snomed": "333353000", "rxnorm": "901644"},
    {"display": "COVID-19 mRNA Vaccine", "cvx": "207", "snomed": "1119349007", "rxnorm": "2468231"},
    {"display": "Zoster Vaccine", "cvx": "187", "snomed": "871895005", "rxnorm": "1986830"}
]

ALLERGENS = [
    {"display": "Penicillin", "category": "drug", "rxnorm": "7982", "unii": "Q42T66VW0C", "snomed": "373270004"},
    {"display": "Amoxicillin", "category": "drug", "rxnorm": "723", "unii": "", "snomed": ""},
    {"display": "Cephalexin", "category": "drug", "rxnorm": "197436", "unii": "", "snomed": ""},
    {"display": "Ceftriaxone", "category": "drug", "rxnorm": "130714", "unii": "", "snomed": ""},
    {"display": "Sulfamethoxazole", "category": "drug", "rxnorm": "9291", "unii": "", "snomed": ""},
    {"display": "Trimethoprim", "category": "drug", "rxnorm": "10831", "unii": "", "snomed": ""},
    {"display": "Vancomycin", "category": "drug", "rxnorm": "11124", "unii": "", "snomed": ""},
    {"display": "Ciprofloxacin", "category": "drug", "rxnorm": "2551", "unii": "", "snomed": ""},
    {"display": "Azithromycin", "category": "drug", "rxnorm": "18631", "unii": "", "snomed": ""},
    {"display": "Clindamycin", "category": "drug", "rxnorm": "2582", "unii": "", "snomed": ""},
    {"display": "Metronidazole", "category": "drug", "rxnorm": "6902", "unii": "", "snomed": ""},
    {"display": "Morphine", "category": "drug", "rxnorm": "7052", "unii": "", "snomed": ""},
    {"display": "Oxycodone", "category": "drug", "rxnorm": "7804", "unii": "", "snomed": ""},
    {"display": "Hydrocodone", "category": "drug", "rxnorm": "5489", "unii": "", "snomed": ""},
    {"display": "Ibuprofen", "category": "drug", "rxnorm": "5640", "unii": "", "snomed": ""},
    {"display": "Naproxen", "category": "drug", "rxnorm": "7771", "unii": "", "snomed": ""},
    {"display": "Aspirin", "category": "drug", "rxnorm": "1191", "unii": "", "snomed": ""},
    {"display": "Acetaminophen", "category": "drug", "rxnorm": "161", "unii": "", "snomed": ""},
    {"display": "Lisinopril", "category": "drug", "rxnorm": "617314", "unii": "", "snomed": ""},
    {"display": "Losartan", "category": "drug", "rxnorm": "979664", "unii": "", "snomed": ""},
    {"display": "Metformin", "category": "drug", "rxnorm": "860975", "unii": "", "snomed": ""},
    {"display": "Insulin", "category": "drug", "rxnorm": "847232", "unii": "", "snomed": ""},
    {"display": "Sertraline", "category": "drug", "rxnorm": "312941", "unii": "", "snomed": ""},
    {"display": "Hydrochlorothiazide", "category": "drug", "rxnorm": "316047", "unii": "", "snomed": ""},
    {"display": "Metoprolol", "category": "drug", "rxnorm": "866350", "unii": "", "snomed": ""},
    {"display": "Glipizide", "category": "drug", "rxnorm": "205910", "unii": "", "snomed": ""},
    {"display": "Sitagliptin", "category": "drug", "rxnorm": "861035", "unii": "", "snomed": ""},
    {"display": "Empagliflozin", "category": "drug", "rxnorm": "1551306", "unii": "", "snomed": ""},
    {"display": "Insulin Lispro", "category": "drug", "rxnorm": "863678", "unii": "", "snomed": ""},
    {"display": "Albuterol", "category": "drug", "rxnorm": "435", "unii": "", "snomed": ""},
    {"display": "Fluticasone", "category": "drug", "rxnorm": "865098", "unii": "", "snomed": ""},
    {"display": "Budesonide/Formoterol", "category": "drug", "rxnorm": "859038", "unii": "", "snomed": ""},
    {"display": "Cetirizine", "category": "drug", "rxnorm": "199222", "unii": "", "snomed": ""},
    {"display": "Loratadine", "category": "drug", "rxnorm": "211789", "unii": "", "snomed": ""},
    {"display": "Fexofenadine", "category": "drug", "rxnorm": "966713", "unii": "", "snomed": ""},
    {"display": "Fluticasone (Nasal)", "category": "drug", "rxnorm": "1595587", "unii": "", "snomed": ""},
    {"display": "Mometasone (Nasal)", "category": "drug", "rxnorm": "1799150", "unii": "", "snomed": ""},
    {"display": "Epinephrine", "category": "drug", "rxnorm": "6367", "unii": "", "snomed": ""},
    {"display": "Warfarin", "category": "drug", "rxnorm": "855332", "unii": "", "snomed": ""},
    {"display": "Apixaban", "category": "drug", "rxnorm": "1365001", "unii": "", "snomed": ""},
    {"display": "Rivaroxaban", "category": "drug", "rxnorm": "1359036", "unii": "", "snomed": ""},
    {"display": "Sumatriptan", "category": "drug", "rxnorm": "313782", "unii": "", "snomed": ""},
    {"display": "Rizatriptan", "category": "drug", "rxnorm": "312961", "unii": "", "snomed": ""},
    {"display": "Topiramate", "category": "drug", "rxnorm": "90039", "unii": "", "snomed": ""},
    {"display": "Amitriptyline", "category": "drug", "rxnorm": "856838", "unii": "", "snomed": ""},
    {"display": "Buspirone", "category": "drug", "rxnorm": "20610", "unii": "", "snomed": ""},
    {"display": "Paroxetine", "category": "drug", "rxnorm": "7987", "unii": "", "snomed": ""},
    {"display": "Venlafaxine", "category": "drug", "rxnorm": "1086784", "unii": "", "snomed": ""},
    {"display": "Duloxetine", "category": "drug", "rxnorm": "724366", "unii": "", "snomed": ""},
    {"display": "Bupropion", "category": "drug", "rxnorm": "42347", "unii": "", "snomed": ""},
    {"display": "Mirtazapine", "category": "drug", "rxnorm": "211190", "unii": "", "snomed": ""},
    {"display": "Lorazepam", "category": "drug", "rxnorm": "2839", "unii": "", "snomed": ""},
    {"display": "Alprazolam", "category": "drug", "rxnorm": "213702", "unii": "", "snomed": ""},
    {"display": "Paclitaxel", "category": "drug", "rxnorm": "197932", "unii": "", "snomed": ""},
    {"display": "Ondansetron", "category": "drug", "rxnorm": "312615", "unii": "", "snomed": ""},
    {"display": "Dexamethasone", "category": "drug", "rxnorm": "197862", "unii": "", "snomed": ""},
    {"display": "Filgrastim", "category": "drug", "rxnorm": "111419", "unii": "", "snomed": ""},
    {"display": "Paxlovid", "category": "drug", "rxnorm": "2572862", "unii": "", "snomed": ""},
    {"display": "Remdesivir", "category": "drug", "rxnorm": "2284718", "unii": "", "snomed": ""},
    {"display": "Oseltamivir", "category": "drug", "rxnorm": "362666", "unii": "", "snomed": ""},
    {"display": "Zanamivir", "category": "drug", "rxnorm": "316268", "unii": "", "snomed": ""},
    {"display": "Peanut", "category": "food", "rxnorm": "4025294", "unii": "R16CO5Y76E", "snomed": "256349002"},
    {"display": "Peanut Oil", "category": "food", "rxnorm": "", "unii": "", "snomed": ""},
    {"display": "Shellfish", "category": "food", "rxnorm": "", "unii": "", "snomed": ""},
    {"display": "Shrimp", "category": "food", "rxnorm": "", "unii": "", "snomed": "300913006"},
    {"display": "Crab", "category": "food", "rxnorm": "", "unii": "", "snomed": "300911008"},
    {"display": "Lobster", "category": "food", "rxnorm": "", "unii": "", "snomed": "300912001"},
    {"display": "Salmon", "category": "food", "rxnorm": "", "unii": "", "snomed": "300910009"},
    {"display": "Tuna", "category": "food", "rxnorm": "", "unii": "", "snomed": "300914000"},
    {"display": "Egg", "category": "food", "rxnorm": "", "unii": "", "snomed": "113089000"},
    {"display": "Cow's Milk", "category": "food", "rxnorm": "", "unii": "", "snomed": "91930004"},
    {"display": "Soy", "category": "food", "rxnorm": "", "unii": "", "snomed": "255620007"},
    {"display": "Wheat", "category": "food", "rxnorm": "", "unii": "", "snomed": "256349009"},
    {"display": "Sesame", "category": "food", "rxnorm": "", "unii": "", "snomed": "226222004"},
    {"display": "Tree Nuts", "category": "food", "rxnorm": "", "unii": "", "snomed": "226359003"},
    {"display": "Strawberry", "category": "food", "rxnorm": "", "unii": "", "snomed": "255016003"},
    {"display": "Banana", "category": "food", "rxnorm": "", "unii": "", "snomed": "256280008"},
    {"display": "Avocado", "category": "food", "rxnorm": "", "unii": "", "snomed": "256269009"},
    {"display": "Natural Rubber Latex", "category": "environment", "rxnorm": "25755", "unii": "7RLR5T8Y9N", "snomed": "1003754000"},
    {"display": "Cat Dander", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418689008"},
    {"display": "Dog Dander", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418594005"},
    {"display": "Dust Mite", "category": "environment", "rxnorm": "", "unii": "", "snomed": "419199007"},
    {"display": "Grass Pollen", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418689004"},
    {"display": "Ragweed Pollen", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418689006"},
    {"display": "Birch Pollen", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418689007"},
    {"display": "Mold Spores", "category": "environment", "rxnorm": "", "unii": "", "snomed": "418689010"},
    {"display": "Honey Bee Venom", "category": "insect", "rxnorm": "", "unii": "", "snomed": "248480008"},
    {"display": "Yellow Jacket Venom", "category": "insect", "rxnorm": "", "unii": "", "snomed": "248482000"},
    {"display": "Paper Wasp Venom", "category": "insect", "rxnorm": "", "unii": "", "snomed": "248483005"},
    {"display": "Fire Ant Venom", "category": "insect", "rxnorm": "", "unii": "", "snomed": "248481009"}
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
