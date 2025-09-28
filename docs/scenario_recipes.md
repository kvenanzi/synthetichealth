# Scenario Recipe Backlog

The following clinically curated scenarios extend the current simulator catalog. Each recipe specifies demographics, social determinants, clinical focus, and required terminology so they can be implemented in future iterations.

## 1. Adult Primary Care Wellness
- **Population**: 25–55 years, balanced gender, diverse urban demographics; low-comorbidity baseline.
- **SDOH**: Moderate insurance coverage, variable preventive care adherence.
- **Clinical Focus**: Annual physicals, lipid profiles (LOINC 13457-7, 2093-3), screening mammography (ICD-10 Z12.31), colon cancer screening.
- **Medications**: Limited to short-term antibiotics (RxNorm 723), statins for elevated LDL (RxNorm 83367).
- **Terminology bundles**: ICD-10 Z00.00, E78.5; SNOMED 171207006 (preventive visit). VSAC OID 2.16.840.1.113762.1.4.1222.1628 (Adult preventive care set). UMLS CUI C0002895 (Annual physical).
- **Failures to watch**: Missing preventive service reminders, inconsistent BMI units.

## 2. Cardiometabolic Intensive Management
- **Population**: 55–80 years, higher male proportion, rural/low-income skew.
- **Clinical Focus**: Type 2 diabetes with hypertension and hyperlipidemia.
- **Key Codes**: ICD-10 E11.9, I10, E78.5; LOINC 2339-0 (HbA1c), 8480-6 (systolic BP), 13457-7 (non-HDL cholesterol).
- **Medications**: Metformin (RxNorm 860975), Lisinopril (617314), Atorvastatin (83367), GLP-1 agonist (237197). VSAC: Diabetes monitoring OID 2.16.840.1.113883.3.464.1003.104.12.1011.
- **Workflow**: Quarterly visits, retinal screening, nephropathy labs (LOINC 14958-3 microalbumin).
- **Risks**: Medication reconciliation mismatches, microalbumin unit conversions.

## 3. Pediatric Asthma & Immunization Cohort
- **Population**: 6–16 years, majority urban, higher exposure to environmental triggers.
- **Clinical Focus**: Persistent asthma with vaccination catch-up.
- **Terminology**: ICD-10 J45.40, SNOMED 195967001, LOINC 2019-8 (peak flow), 11557-6 (Influenza Ab). Immunizations via CVX 140 (Influenza) and 10 (IPV).
- **Medications**: Albuterol (RxNorm 435), Budesonide/Formoterol (859038), Leukotriene inhibitors (856641).
- **VSAC**: Asthma medication management OID 2.16.840.1.113762.1.4.1170.3.
- **Notes**: Include ED visits for exacerbations; track school absenteeism in SDOH metadata.

## 4. Maternal-Fetal Prenatal Care
- **Population**: Pregnant individuals 18–40 years, mix of commercial and Medicaid coverage.
- **Clinical Focus**: Prenatal risk stratification, gestational diabetes screening.
- **Codes**: ICD-10 Z34.03 (normal pregnancy), O24.419 (gestational diabetes). LOINC 14771-0 (prenatal panel), 48424-2 (fetal ultrasound).
- **Medications**: Prenatal vitamins (RxNorm 316048), insulin NPH (7052) for gestational diabetes.
- **VSAC**: Prenatal visit value set 2.16.840.1.113762.1.4.1096.53.
- **SDOH**: transportation access, WIC enrollment; include missed-appointment patterns.

## 5. Geriatric Polypharmacy & Fall Risk
- **Population**: >75 years, long-term care residents, high fall risk scores.
- **Clinical Focus**: Multimorbidity (CHF, CKD stage 3, osteoarthritis) with medication burden.
- **Codes**: ICD-10 I50.32, N18.30, M17.11; LOINC 718-7 (Hgb), 2160-0 (Creatinine), 10998-3 (Vitamin D).
- **Medications**: Loop diuretics (RxNorm 200371), beta blockers (856874), opioids (7052) flagged for deprescribing.
- **VSAC**: Potentially inappropriate medications OID 2.16.840.1.113762.1.4.1047.18.
- **UMLS**: C0018802 (Heart failure), semantic type T047.
- **Workflow**: Quarterly medication review, PT referrals, fall assessment observations.

## 6. Oncology Survivorship – Breast Cancer
- **Population**: Female 45–70, post-treatment surveillance.
- **Clinical Focus**: Stage II invasive ductal carcinoma follow-up with endocrine therapy.
- **Terminology**: ICD-10 C50.912, Z85.3; SNOMED 446097007. LOINC 33717-0 (CA 15-3), 24627-2 (bone density scan).
- **Medications**: Tamoxifen (RxNorm 4179), Aromatase inhibitors (RxNorm 310362).
- **VSAC**: Breast cancer surveillance 2.16.840.1.113883.3.526.3.1029.
- **Care Plan**: Annual mammography, semiannual oncology visits, lymphedema monitoring.

## 7. Mental Health Integrated Care
- **Population**: 18–65, mixed urban/suburban, higher unemployment.
- **Clinical Focus**: Major depressive disorder with comorbid generalized anxiety and substance use screening.
- **Codes**: ICD-10 F33.1, F41.1, Z13.89 (screening). LOINC 44261-6 (PHQ-9), 69730-0 (GAD-7).
- **Medications**: SSRIs (RxNorm 312961), SNRIs (724366), adjunctive therapy (RxNorm 211190).
- **VSAC**: Behavioral health assessment OID 2.16.840.1.113762.1.4.1222.180.
- **Integration**: Capture telehealth visits, collaborative care billing codes (CPT 99492).

## 8. Chronic Kidney Disease with Dialysis Planning
- **Population**: 45–75, high prevalence of diabetes and hypertension, underserved areas.
- **Clinical Focus**: CKD stage III–V with transition to dialysis.
- **Terminology**: ICD-10 N18.4, N18.6; SNOMED 431855005. LOINC 33914-3 (eGFR), 77145-4 (Dialysis adequacy panel).
- **Medications**: Erythropoiesis-stimulating agents (RxNorm 111419), Phosphate binders (RxNorm 310798), ACE inhibitors.
- **VSAC**: CKD management OID 2.16.840.1.113883.3.464.1003.118.12.1035.
- **Events**: vascular access placement procedures, transplant evaluation referrals.

## 9. COPD with Home Oxygen Therapy
- **Population**: 60–80, former smokers, rural and industrial backgrounds.
- **Clinical Focus**: Severe COPD with frequent exacerbations and home oxygen.
- **Codes**: ICD-10 J44.1, Z99.81; LOINC 19868-9 (Pulse oximetry), 8277-6 (Arterial blood gas).
- **Medications**: Inhaled corticosteroid/LABA combos (RxNorm 896443), anticholinergics (RxNorm 197361), rescue albuterol.
- **VSAC**: COPD exacerbation management 2.16.840.1.113883.3.117.1.7.1.276.
- **Workflow**: Pulmonary rehab sessions, home health visits, influenza/pneumococcal vaccines tracking.

## 10. Sepsis Survivorship & Readmission Prevention
- **Population**: 30–70, recent inpatient sepsis (ICD-10 A41.9) discharged within 30 days.
- **Clinical Focus**: Post-sepsis syndrome monitoring, organ dysfunction follow-up (LOINC 6690-2 WBC, 1975-2 Lactate).
- **Medications**: Broad-spectrum antibiotics (RxNorm 308135), beta blockers or ACE inhibitors for cardiac sequelae.
- **VSAC**: Sepsis early management 2.16.840.1.113762.1.4.1046.63.
- **SDOH**: Food insecurity, limited access to follow-up care; include care coordination notes and 7-day telehealth check-ins.

## 11. Pregnancy Loss & Mental Health Support
- **Population**: 20–40, recent miscarriage or stillbirth.
- **Clinical Focus**: Post-loss physical care (ICD-10 O03.9) and mental health screening (LOINC 44249-1 Edinburgh Postnatal Depression Scale).
- **Medications**: Short-term analgesics, SSRIs when indicated.
- **VSAC**: Postpartum depression screening OID 2.16.840.1.113883.3.526.3.1570.
- **Workflow**: Bereavement counseling referrals, partner support documentation, follow-up OB visit schedule.

## 12. HIV Chronic Management with PrEP Cohort
- **Population**: Two arms—individuals living with HIV and high-risk HIV-negative patients on PrEP.
- **Clinical Focus**: Viral load suppression and PrEP adherence tracking.
- **Terminology**: ICD-10 B20, Z20.6; LOINC 25836-8 (HIV RNA PCR), 56888-1 (CD4 count). PrEP medication RxNorm 213293 (Emtricitabine/Tenofovir).
- **VSAC**: HIV viral load monitoring 2.16.840.1.113883.3.464.1003.110.12.1078; PrEP follow-up 2.16.840.1.113883.3.464.1003.110.12.1079.
- **SDOH**: stigma indicators, housing instability, access to case management; incorporate quarterly labs and pharmacy refill adherence metrics.

---

**Implementation Notes**
- Each scenario should include YAML-ready distributions (`age_dist`, `gender_dist`, `race_dist`, SDOH factors) plus a `terminology` block referencing the listed codes/OIDs.
- When promoting to core code, update `src/core/lifecycle/scenarios.py`, add targeted tests, and ensure terminology assets exist in the normalized datasets.
