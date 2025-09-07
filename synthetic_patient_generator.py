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
        for patient in patients:
            patient_globals = VistaFormatter.create_dpt_global(patient)
            all_globals.update(patient_globals)
        
        # Process encounters
        encounter_map = {}
        for encounter in encounters:
            patient_id = encounter.get('patient_id')
            if patient_id not in encounter_map:
                encounter_map[patient_id] = []
            encounter_map[patient_id].append(encounter)
        
        for patient in patients:
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
        
        for patient in patients:
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
        all_procedures.extend(generate_procedures(patient_dict, encounters))
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
        for patient in patients_list:
            patient_resource = fhir_formatter.create_patient_resource(patient)
            bundle_entries.append({"resource": patient_resource})
        
        # Add Condition resources
        for condition in conditions_list:
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
        for patient in patients_list:
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
        
        for patient in patients_list:
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
    patients_dict = [patient.to_dict() for patient in patients]
    
    save(pl.DataFrame(patients_dict), "patients")
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

    # Export FHIR bundle (Phase 1: basic Patient and Condition resources)
    save_fhir_bundle(patients, all_conditions, "fhir_bundle.json")
    
    # Export HL7 v2 messages (Phase 2: ADT and ORU messages)
    save_hl7_messages(patients, all_encounters, all_observations, "hl7_messages")
    
    # Export VistA MUMPS globals (Phase 3: VA migration simulation)
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

if __name__ == "__main__":
    main() 