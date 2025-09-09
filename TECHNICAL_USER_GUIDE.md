# Synthetic Healthcare Data Generator - Technical User Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [Data Formats and Standards](#data-formats-and-standards)
5. [Technical Implementation Details](#technical-implementation-details)
6. [Usage Guide](#usage-guide)
7. [Configuration Options](#configuration-options)
8. [Output Files Reference](#output-files-reference)
9. [Troubleshooting](#troubleshooting)
10. [Development and Extension](#development-and-extension)

---

## Overview

The Synthetic Healthcare Data Generator is a comprehensive tool designed to create realistic, multi-format healthcare data for research, development, and migration testing. It specifically targets VistA-to-Oracle Health migration scenarios while supporting multiple healthcare interoperability standards.

### Key Features
- **Multi-Format Output**: CSV/Parquet, FHIR R4, HL7 v2.x, VistA MUMPS globals
- **Clinical Accuracy**: Evidence-based condition prevalence and realistic medical relationships
- **VA-Specific**: Supports VistA identifiers, stop codes, and VA-specific healthcare patterns
- **Standards Compliant**: FHIR R4 US Core, HL7 v2.5, VistA FileMan structures
- **Scalable**: Parallel processing with configurable patient populations

---

## Quick Start

### Prerequisites
```bash
# Ensure Python 3.8+ is installed
python3 --version

# Navigate to project directory
cd /home/kevin/Projects/synthetichealth
```

### Installation
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage
```bash
# Generate 100 patients with all formats
python3 synthetic_patient_generator.py --num-records 100

# Generate with specific configuration
python3 synthetic_patient_generator.py --config config.yaml --num-records 1000

# CSV only output
python3 synthetic_patient_generator.py --csv --num-records 50
```

---

## Architecture Overview

### System Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────────┐
│                    Synthetic Healthcare Data Generator               │
├─────────────────────────────────────────────────────────────────────┤
│  Input Layer                                                        │
│  ├── CLI Arguments (--num-records, --config, --output-dir)         │
│  ├── YAML Configuration (config.yaml)                              │
│  └── Distribution Parameters (age, gender, race, SDOH)             │
├─────────────────────────────────────────────────────────────────────┤
│  Core Data Generation Engine                                        │
│  ├── PatientRecord Class (Enhanced dataclass with multiple IDs)    │
│  ├── Clinical Logic Engine (Condition prevalence, relationships)   │
│  ├── Healthcare Identifiers (VistA ID, MRN, SSN, Patient ID)      │
│  └── SDOH Integration (Smoking, alcohol, education, housing)       │
├─────────────────────────────────────────────────────────────────────┤
│  Multi-Format Export Layer                                         │
│  ├── FHIR R4 Formatter (US Core Patient/Condition resources)      │
│  ├── HL7 v2 Formatter (ADT^A04, ORU^R01 messages)                │
│  ├── VistA MUMPS Formatter (^DPT, ^AUPNVSIT, ^AUPNPROB globals)  │
│  └── CSV/Parquet Exporter (Normalized relational tables)          │
├─────────────────────────────────────────────────────────────────────┤
│  Validation & Quality Assurance                                    │
│  ├── FHIR Resource Validation                                      │
│  ├── HL7 Message Structure Validation                              │
│  ├── Clinical Logic Validation                                     │
│  └── Data Quality Reporting                                        │
├─────────────────────────────────────────────────────────────────────┤
│  Output Layer                                                      │
│  ├── File Writers (JSON, CSV, Parquet, MUMPS)                     │
│  ├── Statistics Generator                                          │
│  └── Report Generation                                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. PatientRecord Class
```python
@dataclass
class PatientRecord:
    # Healthcare Identifiers
    patient_id: str        # UUID4 primary identifier
    vista_id: str          # VistA internal patient number (IEN)
    mrn: str              # Medical Record Number (MRN123456)
    ssn: str              # Social Security Number
    
    # Demographics
    first_name: str
    last_name: str
    middle_name: str
    gender: str           # male, female, other
    birthdate: str        # ISO format YYYY-MM-DD
    age: int             # Calculated from birthdate
    race: str            # White, Black, Asian, Hispanic, Native American, Other
    ethnicity: str       # Hispanic or Latino, Not Hispanic or Latino
    
    # Clinical Data Containers
    encounters: List[Dict]     # Healthcare visits
    conditions: List[Dict]     # Medical diagnoses
    medications: List[Dict]    # Prescriptions
    allergies: List[Dict]      # Allergic reactions
    procedures: List[Dict]     # Medical procedures
    immunizations: List[Dict]  # Vaccinations
    observations: List[Dict]   # Vital signs and lab results
    
    # Migration Metadata
    metadata: Dict[str, Any]   # Source system, quality scores, timestamps
```

#### 2. Multi-Format Exporters

**FHIR R4 Formatter**
- Creates US Core compliant Patient and Condition resources
- Proper identifier systems and coding
- Bundle generation with timestamp and entry references
- Validation against FHIR R4 schemas

**HL7 v2 Formatter**
- ADT^A04 messages for patient admission/registration
- ORU^R01 messages for observation/lab results
- Proper segment structure (MSH, EVN, PID, PV1, OBR, OBX)
- LOINC coding for observations
- Message validation and error reporting

**VistA MUMPS Formatter**
- Production-accurate global structures (^DPT, ^AUPNVSIT, ^AUPNPROB)
- FileMan field mappings and data types
- Cross-reference generation (B indexes, date indexes, ICD indexes)
- VistA internal date format conversion
- Proper MUMPS SET command syntax

---

## Data Formats and Standards

### 1. FHIR R4 (Fast Healthcare Interoperability Resources)

#### US Core Patient Resource Structure
```json
{
  "resourceType": "Patient",
  "id": "patient-uuid",
  "meta": {
    "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
  },
  "identifier": [
    {
      "use": "usual",
      "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
      "value": "MRN123456"
    },
    {
      "use": "official",
      "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]},
      "system": "http://hl7.org/fhir/sid/us-ssn",
      "value": "123-45-6789"
    }
  ],
  "active": true,
  "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
  "gender": "male",
  "birthDate": "1980-01-01",
  "address": [{"use": "home", "line": ["123 Main St"], "city": "Anytown", "state": "ST", "postalCode": "12345"}]
}
```

#### Condition Resource with Medical Coding
```json
{
  "resourceType": "Condition",
  "id": "condition-uuid",
  "subject": {"reference": "Patient/patient-uuid"},
  "code": {
    "coding": [
      {
        "system": "http://hl7.org/fhir/sid/icd-10-cm",
        "code": "E11.9",
        "display": "Type 2 diabetes mellitus without complications"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "44054006",
        "display": "Diabetes mellitus type 2"
      }
    ]
  },
  "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
  "onsetDateTime": "2020-01-15"
}
```

### 2. HL7 v2.5 Messages

#### ADT^A04 (Patient Registration) Message Structure
```
MSH|^~\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|20250906120000||ADT^A04|MSG123456|P|2.5
EVN|A04|20250906120000|||
PID|1||MRN123456^^^VA^MR~123456789^^^USA^SS||DOE^JOHN^M||19800101|M||2106-3^White^HL70005|123 MAIN ST^^ANYTOWN^ST^12345||555-123-4567||en^English^ISO639|M^Married^HL70002||PATIENT-UUID^^^VA^AN|123456789|||2186-5^Not Hispanic or Latino^HL70189
PV1|1|O|CLINIC1^^^VA^CLINIC||||DOE^JANE^A^^^DR|||GIM||||||||||||||||||||||||20250906||||||||
```

**Segment Breakdown:**
- **MSH**: Message header with sending/receiving applications
- **EVN**: Event type and timestamp
- **PID**: Patient identification with demographics and identifiers
- **PV1**: Patient visit information (optional, when encounter present)

#### ORU^R01 (Lab Results) Message Structure
```
MSH|^~\&|VistA|VA_FACILITY|LAB|LAB_FACILITY|20250906120000||ORU^R01|LAB123456|P|2.5
PID|1||MRN123456^^^VA^MR~123456789^^^USA^SS||DOE^JOHN^M||19800101|M|||123 MAIN ST^^ANYTOWN^ST^12345
OBR|1|ORDER123|RESULT456|CBC^Complete Blood Count^L|||20250906120000||||||||||DOE^JANE^A
OBX|1|NM|8867-4^Heart Rate^LN||72|bpm||||F|||20250906120000
OBX|2|NM|29463-7^Weight^LN||70.5|kg||||F|||20250906120000
OBX|3|ST|85354-9^Blood Pressure^LN||120/80|mmHg||||F|||20250906120000
```

**Key Features:**
- **LOINC Codes**: Standardized observation identifiers (8867-4 for Heart Rate)
- **Data Types**: NM (Numeric), ST (String Text)
- **Units**: Standard UCUM units (bpm, kg, mmHg)
- **Observation Status**: F (Final results)

### 3. VistA MUMPS Global Structures

#### Patient File (#2) - ^DPT Global
```mumps
; Patient demographic data
S ^DPT(123456,0)="DOE,JOHN M^M^19800101^123456789^"
S ^DPT(123456,.02)="M"                    ; Sex
S ^DPT(123456,.03)=2880101               ; Date of Birth (VistA internal format)
S ^DPT(123456,.09)="123456789"           ; SSN
S ^DPT(123456,.111)="123 MAIN ST"        ; Street Address Line 1
S ^DPT(123456,.114)="ANYTOWN"            ; City
S ^DPT(123456,.115)=42                   ; State pointer (to State file #5)
S ^DPT(123456,.116)="12345"              ; Zip Code

; Cross-references for efficient lookup
S ^DPT("B","DOE,JOHN M",123456)=""       ; Name index
S ^DPT("SSN","123456789",123456)=""      ; SSN index  
S ^DPT("DOB",2880101,123456)=""          ; Date of Birth index
```

#### Visit File (#9000010) - ^AUPNVSIT Global
```mumps
; Visit tracking data
S ^AUPNVSIT(789012,0)="123456^3250906.120000^O^323^DOE^JANE^A"
S ^AUPNVSIT(789012,.01)=123456           ; Patient pointer to ^DPT
S ^AUPNVSIT(789012,.02)="CLINIC1"        ; Location
S ^AUPNVSIT(789012,.03)=3250906.120000   ; Visit date/time (VistA format)
S ^AUPNVSIT(789012,.05)="A"              ; Service category (Ambulatory)
S ^AUPNVSIT(789012,.06)=323              ; Stop code (Primary Care)
S ^AUPNVSIT(789012,.07)=123              ; Provider pointer

; Cross-references
S ^AUPNVSIT("B",123456,3250906.120000,789012)=""  ; Patient/Date index
S ^AUPNVSIT("D",3250906.120000,789012)=""          ; Date index
```

#### Problem List (#9000011) - ^AUPNPROB Global  
```mumps
; Medical problem/condition tracking
S ^AUPNPROB(345678,0)="123456^Diabetes^A^3250101^E11.9"
S ^AUPNPROB(345678,.01)=123456           ; Patient pointer
S ^AUPNPROB(345678,.03)=80              ; Diagnosis pointer (to ICD file #80)
S ^AUPNPROB(345678,.05)="Diabetes"       ; Problem description
S ^AUPNPROB(345678,.08)="A"              ; Problem status (Active)
S ^AUPNPROB(345678,.09)="P"              ; Condition (Permanent)
S ^AUPNPROB(345678,.12)=3250101          ; Date entered

; Cross-references  
S ^AUPNPROB("B",123456,345678)=""        ; Patient index
S ^AUPNPROB("ICD","E11.9",123456,345678)="" ; ICD code index
S ^AUPNPROB("S","A",123456,345678)=""    ; Status index
```

**VistA Date Format Notes:**
- Internal dates: Days since January 1, 1841
- Example: 3250906 = September 6, 2025 (184 years * 365.25 days + day offset)
- Time format: YYMMDD.HHMMSS (3250906.120000 = Sept 6, 2025 at 12:00:00)

---

## Technical Implementation Details

### 1. Data Generation Pipeline

#### Step 1: Patient Generation
```python
def generate_patient(_):
    """Generate enhanced patient using PatientRecord class"""
    # Generate realistic demographics
    birthdate = fake.date_of_birth(minimum_age=0, maximum_age=100)
    age = (datetime.now().date() - birthdate).days // 365
    
    # Create PatientRecord instance
    patient = PatientRecord(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        middle_name=fake.first_name()[:1],
        gender=random.choice(GENDERS),
        birthdate=birthdate.isoformat(),
        age=age,
        race=random.choice(RACES),
        ethnicity=random.choice(ETHNICITIES),
        # ... additional fields
    )
    
    # Generate healthcare identifiers
    patient.generate_vista_id()  # VistA IEN (1-9999999)
    patient.generate_mrn()       # MRN123456 format
    
    return patient
```

#### Step 2: Clinical Data Generation
```python
def generate_conditions(patient, encounters, min_cond=1, max_cond=5):
    """Generate medical conditions with clinical logic"""
    # Use evidence-based prevalence by age/gender/race
    assigned = assign_conditions(patient)
    conditions = []
    
    for cond in assigned:
        enc = random.choice(encounters) if encounters else None
        onset_date = enc["date"] if enc else patient.birthdate
        
        conditions.append({
            "condition_id": str(uuid.uuid4()),
            "patient_id": patient.patient_id,
            "encounter_id": enc["encounter_id"] if enc else None,
            "name": cond,
            "status": random.choice(CONDITION_STATUSES),
            "onset_date": onset_date,
        })
    
    return conditions
```

#### Step 3: Format-Specific Export

**FHIR Bundle Generation**
```python
def save_fhir_bundle(patients_list, conditions_list, filename="fhir_bundle.json"):
    """Generate FHIR R4 Bundle with Patient and Condition resources"""
    fhir_formatter = FHIRFormatter()
    bundle_entries = []
    
    # Generate Patient resources
    for patient in patients_list:
        patient_resource = fhir_formatter.create_patient_resource(patient)
        bundle_entries.append({"resource": patient_resource})
    
    # Generate Condition resources with proper coding
    for condition in conditions_list:
        condition_resource = fhir_formatter.create_condition_resource(
            condition.get('patient_id'), condition
        )
        bundle_entries.append({"resource": condition_resource})
    
    # Create Bundle wrapper
    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": datetime.now().isoformat(),
        "entry": bundle_entries
    }
    
    # Write to JSON file
    with open(filename, 'w') as f:
        json.dump(fhir_bundle, f, indent=2)
```

**HL7 Message Generation**
```python
def create_adt_message(patient_record, encounter=None, message_type="A04"):
    """Create HL7 v2 ADT message with proper segments"""
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
    
    # PID - Patient Identification with all demographic fields
    pid_segments = [
        "PID", "1", "",  # Segment ID, Set ID, External ID
        f"{patient_record.mrn}^^^VA^MR~{patient_record.ssn}^^^USA^SS",  # Patient ID list
        "",  # Alternate Patient ID
        f"{patient_record.last_name}^{patient_record.first_name}^{patient_record.middle_name}",  # Patient Name
        "",  # Mother's Maiden Name
        patient_record.birthdate.replace('-', ''),  # Date of Birth
        patient_record.gender.upper()[0],  # Administrative Sex
        "",  # Patient Alias
        HL7v2Formatter._get_hl7_race_code(patient_record.race),  # Race
        f"{patient_record.address}^^{patient_record.city}^{patient_record.state}^{patient_record.zip}",  # Patient Address
        # ... additional PID fields
    ]
    
    pid = "|".join(pid_segments)
    segments.append(pid)
    
    # PV1 - Patient Visit (if encounter provided)
    if encounter:
        pv1_segments = [
            "PV1", "1",  # Segment ID, Set ID
            encounter.get('type', 'O'),  # Patient Class
            "CLINIC1^^^VA^CLINIC",  # Assigned Patient Location
            # ... additional PV1 fields
        ]
        pv1 = "|".join(pv1_segments)
        segments.append(pv1)
    
    return "\r".join(segments)
```

**VistA MUMPS Global Export**
```python
def export_vista_globals(patients, encounters, conditions, filename="vista_globals.mumps"):
    """Generate production-quality VistA MUMPS globals"""
    with open(filename, 'w') as f:
        # File header
        f.write(f";; VistA MUMPS Global Export for Synthetic Patient Data\n")
        f.write(f";; Generated on {datetime.now().isoformat()}\n")
        
        # Generate patient globals (^DPT)
        for patient in patients:
            vista_id = patient.vista_id
            
            # Main patient record
            f.write(f'S ^DPT({vista_id},0)="{patient.last_name},{patient.first_name} {patient.middle_name}^{patient.gender}^{_convert_to_vista_date(patient.birthdate)}^{patient.ssn}"\n')
            f.write(f'S ^DPT({vista_id},.02)="{patient.gender.upper()[0]}"\n')
            f.write(f'S ^DPT({vista_id},.03)={_convert_to_vista_date(patient.birthdate)}\n')
            f.write(f'S ^DPT({vista_id},.09)="{patient.ssn}"\n')
            
            # Generate cross-references
            name_key = f"{patient.last_name},{patient.first_name} {patient.middle_name}".upper()
            f.write(f'S ^DPT("B","{name_key}",{vista_id})=""\n')
            f.write(f'S ^DPT("SSN","{patient.ssn}",{vista_id})=""\n')
            f.write(f'S ^DPT("DOB",{_convert_to_vista_date(patient.birthdate)},{vista_id})=""\n')
        
        # Generate visit globals (^AUPNVSIT)
        for encounter in encounters:
            visit_id = random.randint(100000, 999999)
            patient_id = encounter['patient_id']
            # Find patient VistA ID
            patient_vista_id = next((p.vista_id for p in patients if p.patient_id == patient_id), None)
            
            if patient_vista_id:
                visit_date = _convert_to_vista_datetime(encounter['date'])
                stop_code = _get_vista_stop_code(encounter['type'])
                
                f.write(f'S ^AUPNVSIT({visit_id},0)="{patient_vista_id}^{visit_date}^O^{stop_code}"\n')
                f.write(f'S ^AUPNVSIT({visit_id},.01)={patient_vista_id}\n')
                f.write(f'S ^AUPNVSIT({visit_id},.03)={visit_date}\n')
                
                # Cross-references
                f.write(f'S ^AUPNVSIT("B",{patient_vista_id},{visit_date},{visit_id})=""\n')
                f.write(f'S ^AUPNVSIT("D",{visit_date},{visit_id})=""\n')
        
        # Generate problem list globals (^AUPNPROB)
        for condition in conditions:
            problem_id = random.randint(100000, 999999)
            patient_id = condition['patient_id']
            patient_vista_id = next((p.vista_id for p in patients if p.patient_id == patient_id), None)
            
            if patient_vista_id:
                icd_code = TERMINOLOGY_MAPPINGS['conditions'].get(condition['name'], {}).get('icd10', '')
                onset_date = _convert_to_vista_date(condition['onset_date'])
                
                f.write(f'S ^AUPNPROB({problem_id},.05)="{condition["name"]}"\n')
                f.write(f'S ^AUPNPROB({problem_id},0)="{patient_vista_id}^{condition["name"]}^{condition["status"].upper()[0]}^{onset_date}^{icd_code}"\n')
                
                # Cross-references
                f.write(f'S ^AUPNPROB("B",{patient_vista_id},{problem_id})=""\n')
                if icd_code:
                    f.write(f'S ^AUPNPROB("ICD","{icd_code}",{patient_vista_id},{problem_id})=""\n')
                f.write(f'S ^AUPNPROB("S","{condition["status"].upper()[0]}",{patient_vista_id},{problem_id})=""\n')

def _convert_to_vista_date(iso_date_str):
    """Convert ISO date to VistA internal format (days since 1841-01-01)"""
    date_obj = datetime.strptime(iso_date_str, "%Y-%m-%d").date()
    vista_epoch = datetime(1841, 1, 1).date()
    delta = date_obj - vista_epoch
    return delta.days

def _convert_to_vista_datetime(iso_date_str):
    """Convert to VistA datetime format YYYMMDD.HHMMSS"""
    # Simplified for date-only input, adds default time
    vista_date = _convert_to_vista_date(iso_date_str)
    return f"{vista_date}.120000"  # Default to 12:00:00

def _get_vista_stop_code(encounter_type):
    """Map encounter type to VistA stop code"""
    stop_codes = {
        "Wellness Visit": "323",     # Primary Care
        "Emergency": "130",          # Emergency Department
        "Follow-up": "323",          # Primary Care
        "Specialist": "301",         # Specialty Care
        "Lab": "301",               # Laboratory
        "Surgery": "162"            # Surgical Service
    }
    return stop_codes.get(encounter_type, "323")
```

### 2. Validation Systems

#### FHIR Resource Validation
```python
def validate_fhir_bundle(bundle):
    """Validate FHIR bundle against R4 schemas"""
    validation_results = []
    
    # Validate bundle structure
    required_fields = ["resourceType", "type", "entry"]
    for field in required_fields:
        if field not in bundle:
            validation_results.append(f"Missing required field: {field}")
    
    # Validate each resource
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")
        
        if resource_type == "Patient":
            validation_results.extend(_validate_patient_resource(resource))
        elif resource_type == "Condition":
            validation_results.extend(_validate_condition_resource(resource))
    
    return {
        "valid": len(validation_results) == 0,
        "errors": validation_results
    }

def _validate_patient_resource(resource):
    """Validate Patient resource against US Core profile"""
    errors = []
    
    # Required fields per US Core
    required_fields = ["id", "identifier", "name", "gender"]
    for field in required_fields:
        if field not in resource or not resource[field]:
            errors.append(f"Patient resource missing required field: {field}")
    
    # Validate identifier structure
    identifiers = resource.get("identifier", [])
    if not any(id.get("type", {}).get("coding", [{}])[0].get("code") == "MR" for id in identifiers):
        errors.append("Patient resource missing Medical Record Number identifier")
    
    # Validate name structure
    names = resource.get("name", [])
    if names and not names[0].get("family"):
        errors.append("Patient resource missing family name")
    
    return errors
```

#### HL7 Message Validation
```python
def validate_hl7_message(message):
    """Validate HL7 v2 message structure"""
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "segments_found": []
    }
    
    segments = message.split('\r')
    
    # Must start with MSH
    if not segments or not segments[0].startswith('MSH'):
        validation_result["valid"] = False
        validation_result["errors"].append("Missing or invalid MSH segment")
        return validation_result
    
    # Validate each segment
    for segment in segments:
        if not segment:
            continue
            
        segment_type = segment[:3]
        validation_result["segments_found"].append(segment_type)
        fields = segment.split('|')
        
        # Segment-specific validation
        if segment_type == "MSH" and len(fields) < 10:
            validation_result["errors"].append(f"MSH segment insufficient fields: {len(fields)}")
        elif segment_type == "PID" and len(fields) < 5:
            validation_result["errors"].append(f"PID segment insufficient fields: {len(fields)}")
        elif segment_type == "OBX":
            # Validate observation value format
            if len(fields) > 5 and fields[2]:  # Observation ID exists
                obs_id = fields[2].split('^')[0]
                if not obs_id:
                    validation_result["warnings"].append("OBX segment missing observation identifier")
    
    # Check message type requirements
    if "PID" not in validation_result["segments_found"]:
        validation_result["warnings"].append("No PID segment found")
    
    if validation_result["errors"]:
        validation_result["valid"] = False
    
    return validation_result
```

### 3. Performance Optimizations

#### Parallel Processing
```python
# Use ThreadPoolExecutor for I/O-bound patient generation
with concurrent.futures.ThreadPoolExecutor() as executor:
    patients = list(executor.map(generate_patient_with_dist, range(num_records)))

# Memory-efficient batch processing for large datasets
def process_patients_in_batches(patients, batch_size=1000):
    """Process patients in batches to manage memory usage"""
    for i in range(0, len(patients), batch_size):
        batch = patients[i:i + batch_size]
        yield process_patient_batch(batch)
```

#### Data Structure Optimizations
```python
# Use Polars for efficient DataFrame operations
import polars as pl

# Convert to DataFrame only when needed for export
patients_dict = [patient.to_dict() for patient in patients]
df = pl.DataFrame(patients_dict)

# Write with compression for large datasets
df.write_parquet("patients.parquet", compression="snappy")
```

---

## Usage Guide

### Command Line Interface

#### Basic Usage
```bash
# Generate 1000 patients (default configuration)
python3 synthetic_patient_generator.py --num-records 1000

# Specify output directory
python3 synthetic_patient_generator.py --num-records 500 --output-dir /path/to/output

# Set random seed for reproducible results
python3 synthetic_patient_generator.py --num-records 100 --seed 42

# Generate specific output formats
python3 synthetic_patient_generator.py --csv --num-records 200        # CSV only
python3 synthetic_patient_generator.py --parquet --num-records 200    # Parquet only
python3 synthetic_patient_generator.py --both --num-records 200       # Both CSV and Parquet
```

#### Configuration File Usage
```bash
# Use YAML configuration file
python3 synthetic_patient_generator.py --config config.yaml

# Configuration with report generation
python3 synthetic_patient_generator.py --config config.yaml --report-file summary_report.txt
```

### Configuration Options

#### config.yaml Structure
```yaml
# Basic generation parameters
num_records: 10000
output_dir: "./output"
seed: 12345
output_format: "both"  # csv, parquet, both

# Demographic distribution controls
age_dist: "0-18:0.2,19-40:0.3,41-65:0.35,66-120:0.15"
gender_dist: "male:0.48,female:0.48,other:0.04"
race_dist: "White:0.6,Black:0.2,Hispanic:0.12,Asian:0.05,Native American:0.02,Other:0.01"
ethnicity_dist: "Not Hispanic or Latino:0.84,Hispanic or Latino:0.16"

# SDOH (Social Determinants of Health) distributions
smoking_dist: "Never:0.6,Former:0.25,Current:0.15"
alcohol_dist: "Never:0.3,Occasional:0.4,Regular:0.2,Heavy:0.1"
education_dist: "None:0.05,Primary:0.05,Secondary:0.15,High School:0.3,Associate:0.15,Bachelor:0.2,Master:0.08,Doctorate:0.02"
employment_dist: "Employed:0.6,Unemployed:0.1,Student:0.15,Retired:0.1,Disabled:0.05"
housing_dist: "Stable:0.75,Temporary:0.15,Homeless:0.08,Assisted Living:0.02"

# Output file naming (optional)
report_file: "generation_report.txt"
```

#### Advanced Distribution Configuration
```yaml
# Age-specific configuration with detailed bins
age_dist:
  "0-5": 0.06     # Pediatric
  "6-17": 0.12    # School age
  "18-34": 0.25   # Young adults
  "35-54": 0.28   # Middle age
  "55-64": 0.14   # Pre-retirement
  "65-84": 0.12   # Senior
  "85-120": 0.03  # Elderly

# Race distribution reflecting VA population
race_dist:
  "White": 0.73
  "Black": 0.17
  "Hispanic": 0.08
  "Asian": 0.015
  "Native American": 0.005
  "Other": 0.00
```

### Programming Interface

#### Python API Usage
```python
from synthetic_patient_generator import PatientRecord, generate_patient, FHIRFormatter

# Generate single patient
patient = generate_patient(None)
print(f"Generated patient: {patient.first_name} {patient.last_name}")
print(f"VistA ID: {patient.vista_id}, MRN: {patient.mrn}")

# Generate multiple patients programmatically
patients = []
for i in range(100):
    patient = generate_patient(i)
    patients.append(patient)

# Export to FHIR
fhir_formatter = FHIRFormatter()
fhir_bundle = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [{"resource": fhir_formatter.create_patient_resource(p)} for p in patients]
}

# Save FHIR bundle
import json
with open("custom_fhir_bundle.json", "w") as f:
    json.dump(fhir_bundle, f, indent=2)
```

#### Custom Data Processing
```python
import polars as pl
from synthetic_patient_generator import generate_patient

# Generate and analyze data
patients = [generate_patient(i) for i in range(1000)]
patients_dict = [p.to_dict() for p in patients]
df = pl.DataFrame(patients_dict)

# Analyze age distribution
age_stats = df.group_by("age").agg([
    pl.count().alias("count"),
    pl.col("gender").n_unique().alias("unique_genders")
]).sort("age")

print(age_stats)

# Filter and export subset
elderly_patients = df.filter(pl.col("age") >= 65)
elderly_patients.write_csv("elderly_patients.csv")
```

---

## Output Files Reference

### Generated File Structure
```
output_directory/
├── patients.csv                    # Patient demographics and identifiers
├── patients.parquet               # Same data in Parquet format
├── encounters.csv                 # Healthcare visits/encounters
├── encounters.parquet             # Same data in Parquet format
├── conditions.csv                 # Medical diagnoses/problems
├── conditions.parquet             # Same data in Parquet format
├── medications.csv                # Prescribed medications
├── medications.parquet            # Same data in Parquet format
├── allergies.csv                  # Patient allergies
├── allergies.parquet              # Same data in Parquet format
├── procedures.csv                 # Medical procedures
├── procedures.parquet             # Same data in Parquet format
├── immunizations.csv              # Vaccination records
├── immunizations.parquet          # Same data in Parquet format
├── observations.csv               # Vital signs and lab results
├── observations.parquet           # Same data in Parquet format
├── deaths.csv                     # Death records (subset of patients)
├── deaths.parquet                 # Same data in Parquet format
├── family_history.csv             # Family medical history
├── family_history.parquet         # Same data in Parquet format
├── fhir_bundle.json              # FHIR R4 Bundle with Patient/Condition resources
├── hl7_messages_adt.hl7          # HL7 v2 ADT^A04 messages
├── hl7_messages_oru.hl7          # HL7 v2 ORU^R01 messages
├── hl7_messages_validation.json  # HL7 message validation results
└── vista_globals.mumps           # VistA MUMPS global export
```

### CSV Schema Reference

#### patients.csv
```csv
patient_id,vista_id,mrn,first_name,last_name,middle_name,gender,birthdate,age,race,ethnicity,address,city,state,zip,country,phone,email,marital_status,language,insurance,ssn,smoking_status,alcohol_use,education,employment_status,income,housing_status
uuid4,vista_ien,mrn_number,first,last,middle_initial,gender,yyyy-mm-dd,age_int,race_value,ethnicity_value,street_address,city_name,state_code,zip_code,country_code,phone_number,email_address,marital_status,language,insurance_type,ssn,smoking_status,alcohol_use,education_level,employment_status,annual_income,housing_status
```

#### encounters.csv
```csv
encounter_id,patient_id,date,type,reason,provider,location
uuid4,patient_uuid,yyyy-mm-dd,encounter_type,visit_reason,provider_name,facility_name
```

#### conditions.csv
```csv
condition_id,patient_id,encounter_id,name,status,onset_date
uuid4,patient_uuid,encounter_uuid,condition_name,status_value,yyyy-mm-dd
```

#### medications.csv
```csv
medication_id,patient_id,encounter_id,name,start_date,end_date
uuid4,patient_uuid,encounter_uuid,medication_name,yyyy-mm-dd,yyyy-mm-dd_or_null
```

#### observations.csv
```csv
observation_id,patient_id,encounter_id,type,value,date
uuid4,patient_uuid,encounter_uuid,observation_type,measurement_value,yyyy-mm-dd
```

### FHIR Bundle Structure
```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "timestamp": "2025-09-06T21:09:50.897924",
  "entry": [
    {
      "resource": {
        "resourceType": "Patient",
        "id": "patient-uuid",
        "identifier": [...],
        "name": [...],
        "gender": "...",
        "birthDate": "...",
        "address": [...]
      }
    },
    {
      "resource": {
        "resourceType": "Condition",
        "id": "condition-uuid",
        "subject": {"reference": "Patient/patient-uuid"},
        "code": {"coding": [...]},
        "clinicalStatus": {...},
        "onsetDateTime": "..."
      }
    }
  ]
}
```

### HL7 Message Formats

#### ADT^A04 Message (Patient Registration)
```
MSH|^~\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|20250906210950||ADT^A04|MSG698958|P|2.5
EVN|A04|20250906210950|||
PID|1||MRN376034^^^VA^MR~815-76-4975^^^USA^SS||Adams^Keith^H||20030912|O||2106-3^White^HL70005|2356 Maria Rest^^North Sarah^MA^89810||446-391-5300||de^German^ISO639|A^Separated^HL70002||c2917ed2-44e8-4d5b-a125-519edf96ff99^^^VA^AN|815-76-4975|||2186-5^Not Hispanic or Latino^HL70189
PV1|1|Lab|CLINIC1^^^VA^CLINIC||||DOE^JOHN^A^^^DR|||GIM||||||||||||||||||||||||||||||||||20250515
```

#### ORU^R01 Message (Lab Results)
```
MSH|^~\&|VistA|VA_FACILITY|LAB|LAB_FACILITY|20250906210950||ORU^R01|LAB975686|P|2.5
PID|1||MRN376034^^^VA^MR~815-76-4975^^^USA^SS||Adams^Keith^H||20030912|O|||2356 Maria Rest^^North Sarah^MA^89810
OBR|1|267347|747927|CBC^Complete Blood Count^L|||20250906210950||||||||||DOE^JOHN^A
OBX|1|NM|29463-7^Weight^LN||148.5|kg||||F|||20250906210950
OBX|2|NM|2093-3^Cholesterol^LN||276|mg/dL||||F|||20250906210950
OBX|3|ST|85354-9^Blood Pressure^LN||176/98|mmHg||||F|||20250906210950
```

### VistA MUMPS Global Format
```mumps
;; VistA MUMPS Global Export for Synthetic Patient Data
;; Generated on 2025-09-06T21:09:50.901491

; Patient Demographics (^DPT)
S ^DPT("B","ADAMS,KEITH H",5211849)=""
S ^DPT("DOB",59423,5211849)=""
S ^DPT("SSN","815-76-4975",5211849)=""
S ^DPT(5211849,0)="ADAMS,KEITH H^M^59423^815-76-4975"
S ^DPT(5211849,.02)="M"
S ^DPT(5211849,.03)=59423

; Visit Records (^AUPNVSIT)  
S ^AUPNVSIT("B",5211849,3250515.120000,94206)=""
S ^AUPNVSIT("D",3250515.120000,94206)=""
S ^AUPNVSIT(94206,0)="5211849^3250515.120000^O^301"
S ^AUPNVSIT(94206,.01)=5211849
S ^AUPNVSIT(94206,.03)=3250515.120000

; Problem List (^AUPNPROB)
S ^AUPNPROB("B",5211849,725004)=""
S ^AUPNPROB("ICD","M25.50",5211849,725004)=""
S ^AUPNPROB("S","A",5211849,725004)=""
S ^AUPNPROB(725004,0)="5211849^Arthritis^A^59120^M25.50"
S ^AUPNPROB(725004,.05)="Arthritis"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Installation Problems

**Error: `ModuleNotFoundError: No module named 'polars'`**
```bash
# Solution: Install requirements in virtual environment
source .venv/bin/activate
pip install -r requirements.txt

# Verify installation
python3 -c "import polars; print(polars.__version__)"
```

**Error: `permission denied` when writing files**
```bash
# Solution: Check output directory permissions
ls -la output_directory/
chmod 755 output_directory/

# Or specify different output directory
python3 synthetic_patient_generator.py --output-dir ~/healthcare_data
```

#### 2. Data Generation Issues

**Low Data Quality or Unrealistic Patients**
```bash
# Check configuration settings
python3 synthetic_patient_generator.py --config config.yaml --num-records 10

# Review generated data
head -5 patients.csv
```

**Memory Issues with Large Datasets**
```python
# Use batch processing for large datasets
# Modify main() function to process in batches
def process_large_dataset(num_records, batch_size=10000):
    for batch_start in range(0, num_records, batch_size):
        batch_end = min(batch_start + batch_size, num_records)
        batch_patients = generate_patient_batch(batch_end - batch_start)
        save_patient_batch(batch_patients, batch_start)
```

#### 3. Format-Specific Issues

**FHIR Validation Errors**
```python
# Check FHIR bundle structure
import json
with open("fhir_bundle.json", "r") as f:
    bundle = json.load(f)
    
# Validate required fields
for entry in bundle["entry"]:
    resource = entry["resource"]
    if resource["resourceType"] == "Patient":
        if "identifier" not in resource:
            print(f"Patient {resource['id']} missing identifiers")
```

**HL7 Message Format Issues**
```bash
# Check message structure
head -1 hl7_messages_adt.hl7 | tr '|' '\n' | nl

# Validate segment count
grep -o '|' hl7_messages_adt.hl7 | wc -l
```

**VistA MUMPS Syntax Errors**
```bash
# Check for proper MUMPS syntax
grep -n "^S \^" vista_globals.mumps | head -5

# Verify global structure
grep "^DPT" vista_globals.mumps | head -3
```

#### 4. Performance Issues

**Slow Generation for Large Datasets**
```python
# Enable parallel processing optimization
import concurrent.futures

# Increase thread pool size for I/O bound operations
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    patients = list(executor.map(generate_patient_with_dist, range(num_records)))
```

**High Memory Usage**
```python
# Process patients in smaller batches
def generate_patients_streaming(num_records, batch_size=1000):
    for batch_start in range(0, num_records, batch_size):
        batch_size_actual = min(batch_size, num_records - batch_start)
        yield [generate_patient(i) for i in range(batch_size_actual)]

# Use streaming processing
for patient_batch in generate_patients_streaming(100000, 1000):
    process_patient_batch(patient_batch)
    # Clear memory after each batch
    del patient_batch
```

#### 5. Data Quality Issues

**Inconsistent Medical Relationships**
```python
# Debug condition-medication relationships
def validate_clinical_relationships(patients):
    for patient in patients:
        patient_dict = patient.to_dict()
        conditions = generate_conditions(patient_dict, [])
        medications = generate_medications(patient_dict, [], conditions)
        
        # Check for appropriate medication mappings
        for med in medications:
            med_name = med['name']
            # Verify medication is appropriate for patient conditions
            print(f"Patient {patient.patient_id}: {med_name} for conditions: {[c['name'] for c in conditions]}")
```

**Missing Cross-References in VistA Output**
```python
# Validate VistA cross-reference completeness
def validate_vista_cross_references(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # Count main records vs cross-references
    main_records = content.count('S ^DPT(') - content.count('S ^DPT("')
    cross_refs = content.count('S ^DPT("')
    
    print(f"Main records: {main_records}, Cross-references: {cross_refs}")
    print(f"Ratio: {cross_refs / main_records:.2f} cross-refs per record")
```

### Debugging Tips

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug prints to generation functions
def generate_patient_debug(index):
    patient = generate_patient(index)
    logging.debug(f"Generated patient {patient.patient_id}: {patient.first_name} {patient.last_name}")
    logging.debug(f"  VistA ID: {patient.vista_id}, MRN: {patient.mrn}")
    return patient
```

#### Validate Output Files
```bash
# Check file sizes and record counts
wc -l *.csv
ls -lah *.json *.hl7 *.mumps

# Validate CSV structure
head -1 patients.csv | tr ',' '\n' | nl

# Check for empty files
find . -name "*.csv" -size 0
```

#### Performance Profiling
```python
import time
import psutil
import os

def profile_generation():
    start_time = time.time()
    start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
    
    # Run generation
    patients = [generate_patient(i) for i in range(1000)]
    
    end_time = time.time()
    end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024  # MB
    
    print(f"Generation time: {end_time - start_time:.2f} seconds")
    print(f"Memory usage: {end_memory - start_memory:.2f} MB")
    print(f"Patients per second: {1000 / (end_time - start_time):.2f}")

profile_generation()
```

---

## Development and Extension

### Adding New Data Formats

#### Custom Format Export Template
```python
class CustomFormatter:
    """Template for adding new healthcare data formats"""
    
    def __init__(self):
        self.format_name = "Custom Format"
        self.file_extension = ".custom"
    
    def format_patient(self, patient_record: PatientRecord) -> str:
        """Convert patient record to custom format"""
        # Implement format-specific conversion logic
        formatted_data = {
            "patient_identifier": patient_record.patient_id,
            "demographics": {
                "name": f"{patient_record.first_name} {patient_record.last_name}",
                "birth_date": patient_record.birthdate,
                "gender": patient_record.gender
            },
            "healthcare_ids": {
                "mrn": patient_record.mrn,
                "vista_id": patient_record.vista_id,
                "ssn": patient_record.ssn
            }
        }
        
        return self._serialize_to_custom_format(formatted_data)
    
    def _serialize_to_custom_format(self, data: dict) -> str:
        """Implement custom serialization logic"""
        # Example: Convert to custom XML, proprietary format, etc.
        pass
    
    def export_patients(self, patients: List[PatientRecord], filename: str):
        """Export multiple patients to custom format file"""
        with open(filename, 'w') as f:
            for patient in patients:
                formatted_patient = self.format_patient(patient)
                f.write(formatted_patient + "\n")
```

#### Integration with Main Generator
```python
# Add to main() function in synthetic_patient_generator.py
def save_custom_format(patients_list, filename="custom_export.custom"):
    """Save patients in custom format"""
    custom_formatter = CustomFormatter()
    custom_formatter.export_patients(patients_list, filename)
    print(f"Custom format export saved: {filename} ({len(patients_list)} patients)")

# Add call in main export section
save_custom_format(patients, "custom_healthcare_data.custom")
```

### Adding New Clinical Logic

#### Custom Condition Prevalence
```python
# Add to synthetic_patient_generator.py
CUSTOM_CONDITION_PREVALENCE = {
    "Custom_Disease": {
        "age_groups": {
            (0, 17): {"male": 0.05, "female": 0.03},
            (18, 64): {"male": 0.12, "female": 0.08},
            (65, 120): {"male": 0.25, "female": 0.18}
        },
        "race_modifiers": {
            "White": 1.0, "Black": 1.3, "Hispanic": 1.1, "Asian": 0.7
        },
        "sdoh_modifiers": {
            "smoking": {"Current": 1.5, "Former": 1.2, "Never": 1.0},
            "education": {"None": 1.4, "High School": 1.0, "Bachelor": 0.8, "Doctorate": 0.6}
        },
        "comorbidity_risks": ["Hypertension", "Diabetes"]
    }
}

# Merge with existing conditions
CONDITION_PREVALENCE.update(CUSTOM_CONDITION_PREVALENCE)
```

#### Custom Medication Mappings
```python
# Add custom medication relationships
CUSTOM_CONDITION_MEDICATIONS = {
    "Custom_Disease": {
        "Primary_Treatment": [
            {"name": "Custom_Drug_A", "rxnorm": "123456", "strength": "10mg", "frequency": "daily", "weight": 0.6},
            {"name": "Custom_Drug_B", "rxnorm": "789012", "strength": "5mg", "frequency": "twice_daily", "weight": 0.4}
        ],
        "Adjunct_Therapy": [
            {"name": "Support_Drug", "rxnorm": "345678", "strength": "20mg", "frequency": "weekly", "weight": 0.3}
        ]
    }
}

# Update medication generation logic
def generate_custom_medications(patient, conditions):
    """Enhanced medication generation with custom drugs"""
    medications = []
    
    for condition in conditions:
        condition_name = condition["name"]
        if condition_name in CUSTOM_CONDITION_MEDICATIONS:
            drug_categories = CUSTOM_CONDITION_MEDICATIONS[condition_name]
            
            for category, drugs in drug_categories.items():
                # Select drug based on weights
                total_weight = sum(drug["weight"] for drug in drugs)
                random_value = random.random() * total_weight
                
                current_weight = 0
                for drug in drugs:
                    current_weight += drug["weight"]
                    if random_value <= current_weight:
                        medications.append({
                            "medication_id": str(uuid.uuid4()),
                            "patient_id": patient["patient_id"],
                            "name": drug["name"],
                            "rxnorm_code": drug["rxnorm"],
                            "strength": drug["strength"],
                            "frequency": drug["frequency"],
                            "category": category
                        })
                        break
    
    return medications
```

### Adding New Healthcare Standards

#### CDA Document Support
```python
class CDAFormatter:
    """HL7 Clinical Document Architecture formatter"""
    
    def create_ccd_document(self, patient_record: PatientRecord) -> str:
        """Generate Continuity of Care Document (CCD)"""
        cda_template = """<?xml version="1.0" encoding="UTF-8"?>
<ClinicalDocument xmlns="urn:hl7-org:v3">
  <realmCode code="US"/>
  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>
  <templateId root="2.16.840.1.113883.10.20.22.1.2"/>
  <id root="{document_id}"/>
  <code code="34133-9" codeSystem="2.16.840.1.113883.6.1" 
        displayName="Summarization of Episode Note"/>
  <title>Continuity of Care Document</title>
  <effectiveTime value="{timestamp}"/>
  <confidentialityCode code="N" codeSystem="2.16.840.1.113883.5.25"/>
  
  <recordTarget>
    <patientRole>
      <id root="2.16.840.1.113883.3.933" extension="{patient_mrn}"/>
      <patient>
        <name>
          <given>{first_name}</given>
          <family>{last_name}</family>
        </name>
        <administrativeGenderCode code="{gender_code}" 
                                 codeSystem="2.16.840.1.113883.5.1"/>
        <birthTime value="{birth_date}"/>
      </patient>
    </patientRole>
  </recordTarget>
  
  <component>
    <structuredBody>
      <component>
        <section>
          <templateId root="2.16.840.1.113883.10.20.22.2.5.1"/>
          <code code="11450-4" codeSystem="2.16.840.1.113883.6.1" 
                displayName="Problem List"/>
          <title>Problems</title>
          <text>
            <table>
              <thead>
                <tr><th>Problem</th><th>Status</th><th>Date</th></tr>
              </thead>
              <tbody>
                {problem_rows}
              </tbody>
            </table>
          </text>
        </section>
      </component>
    </structuredBody>
  </component>
</ClinicalDocument>"""
        
        # Format template with patient data
        return cda_template.format(
            document_id=str(uuid.uuid4()),
            timestamp=datetime.now().strftime("%Y%m%d%H%M%S"),
            patient_mrn=patient_record.mrn,
            first_name=patient_record.first_name,
            last_name=patient_record.last_name,
            gender_code=patient_record.gender.upper()[0],
            birth_date=patient_record.birthdate.replace('-', ''),
            problem_rows=self._format_problems_table(patient_record.conditions)
        )
    
    def _format_problems_table(self, conditions: List[Dict]) -> str:
        """Format conditions as CDA table rows"""
        rows = []
        for condition in conditions:
            row = f"""<tr>
              <td>{condition['name']}</td>
              <td>{condition['status']}</td>
              <td>{condition['onset_date']}</td>
            </tr>"""
            rows.append(row)
        return "\n".join(rows)
```

### Custom Validation Rules

#### Enhanced Clinical Validation
```python
class ClinicalValidator:
    """Enhanced clinical logic validation"""
    
    def __init__(self):
        self.validation_rules = {
            "age_appropriate_conditions": self._validate_age_conditions,
            "medication_contraindications": self._validate_medication_safety,
            "temporal_consistency": self._validate_temporal_logic
        }
    
    def validate_patient_data(self, patient: PatientRecord) -> Dict[str, Any]:
        """Run comprehensive clinical validation"""
        validation_results = {
            "patient_id": patient.patient_id,
            "overall_valid": True,
            "errors": [],
            "warnings": [],
            "rule_results": {}
        }
        
        for rule_name, rule_function in self.validation_rules.items():
            try:
                rule_result = rule_function(patient)
                validation_results["rule_results"][rule_name] = rule_result
                
                if not rule_result["valid"]:
                    validation_results["overall_valid"] = False
                    validation_results["errors"].extend(rule_result.get("errors", []))
                    validation_results["warnings"].extend(rule_result.get("warnings", []))
                    
            except Exception as e:
                validation_results["errors"].append(f"Validation rule {rule_name} failed: {str(e)}")
                validation_results["overall_valid"] = False
        
        return validation_results
    
    def _validate_age_conditions(self, patient: PatientRecord) -> Dict[str, Any]:
        """Validate conditions are age-appropriate"""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Age-inappropriate conditions
        age_rules = {
            "Alzheimer's": 50,  # Rarely occurs before age 50
            "Arthritis": 30,    # Joint problems typically after 30
            "Cancer": 5         # Very rare in early childhood
        }
        
        for condition in patient.conditions:
            condition_name = condition.get("name")
            if condition_name in age_rules:
                min_age = age_rules[condition_name]
                if patient.age < min_age:
                    result["warnings"].append(
                        f"Patient age {patient.age} may be too young for {condition_name} (typical min age: {min_age})"
                    )
        
        return result
    
    def _validate_medication_safety(self, patient: PatientRecord) -> Dict[str, Any]:
        """Check for medication contraindications and interactions"""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Check for dangerous combinations
        medication_names = [med.get("name") for med in patient.medications]
        
        # Example contraindication: Warfarin + Aspirin = bleeding risk
        if "Warfarin" in medication_names and "Aspirin" in medication_names:
            result["errors"].append("Dangerous combination: Warfarin and Aspirin (bleeding risk)")
            result["valid"] = False
        
        # Age-based contraindications
        if patient.age < 18:
            adult_only_meds = ["Atorvastatin", "Lisinopril"]
            for med in adult_only_meds:
                if med in medication_names:
                    result["errors"].append(f"Medication {med} not appropriate for pediatric patient (age {patient.age})")
                    result["valid"] = False
        
        return result
    
    def _validate_temporal_logic(self, patient: PatientRecord) -> Dict[str, Any]:
        """Validate temporal relationships in medical data"""
        result = {"valid": True, "errors": [], "warnings": []}
        
        birth_date = datetime.strptime(patient.birthdate, "%Y-%m-%d").date()
        
        # Check encounter dates
        for encounter in patient.encounters:
            encounter_date = datetime.strptime(encounter.get("date", "1900-01-01"), "%Y-%m-%d").date()
            if encounter_date < birth_date:
                result["errors"].append(f"Encounter date {encounter_date} before birth date {birth_date}")
                result["valid"] = False
        
        # Check condition onset dates
        for condition in patient.conditions:
            onset_date = datetime.strptime(condition.get("onset_date", "1900-01-01"), "%Y-%m-%d").date()
            if onset_date < birth_date:
                result["errors"].append(f"Condition onset {onset_date} before birth date {birth_date}")
                result["valid"] = False
        
        return result
```

### Performance Optimization Extensions

#### Memory-Efficient Large Dataset Processing
```python
class LargeDatasetProcessor:
    """Memory-efficient processing for million+ patient datasets"""
    
    def __init__(self, batch_size=10000, output_dir="./output"):
        self.batch_size = batch_size
        self.output_dir = output_dir
        self.total_processed = 0
    
    def generate_large_dataset(self, total_patients: int):
        """Generate large dataset with memory management"""
        batches = (total_patients + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(batches):
            batch_start = batch_num * self.batch_size
            batch_end = min(batch_start + self.batch_size, total_patients)
            batch_size_actual = batch_end - batch_start
            
            print(f"Processing batch {batch_num + 1}/{batches} ({batch_size_actual} patients)")
            
            # Generate batch
            batch_patients = self._generate_patient_batch(batch_size_actual, batch_start)
            
            # Process and save batch
            self._process_patient_batch(batch_patients, batch_num)
            
            # Clear memory
            del batch_patients
            self.total_processed += batch_size_actual
            
            # Report progress
            progress = (self.total_processed / total_patients) * 100
            print(f"Progress: {progress:.1f}% ({self.total_processed}/{total_patients} patients)")
    
    def _generate_patient_batch(self, batch_size: int, offset: int) -> List[PatientRecord]:
        """Generate a batch of patients with parallel processing"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            batch_patients = list(executor.map(
                generate_patient, 
                range(offset, offset + batch_size)
            ))
        return batch_patients
    
    def _process_patient_batch(self, patients: List[PatientRecord], batch_num: int):
        """Process and save a batch of patients"""
        # Convert to dictionaries for DataFrame operations
        patients_dict = [patient.to_dict() for patient in patients]
        
        # Create batch DataFrame
        df = pl.DataFrame(patients_dict)
        
        # Save batch file
        batch_filename = os.path.join(self.output_dir, f"patients_batch_{batch_num:04d}.parquet")
        df.write_parquet(batch_filename, compression="snappy")
        
        # Generate clinical data for batch
        self._generate_clinical_data_batch(patients, batch_num)
    
    def _generate_clinical_data_batch(self, patients: List[PatientRecord], batch_num: int):
        """Generate and save clinical data for patient batch"""
        all_encounters = []
        all_conditions = []
        all_medications = []
        
        for patient in patients:
            patient_dict = patient.to_dict()
            
            # Generate clinical data
            conditions = generate_conditions(patient_dict, [], min_cond=1, max_cond=5)
            encounters = generate_encounters(patient_dict, conditions)
            medications = generate_medications(patient_dict, encounters, conditions)
            
            all_encounters.extend(encounters)
            all_conditions.extend(conditions)
            all_medications.extend(medications)
        
        # Save clinical data batches
        if all_encounters:
            encounters_df = pl.DataFrame(all_encounters)
            encounters_df.write_parquet(
                os.path.join(self.output_dir, f"encounters_batch_{batch_num:04d}.parquet"),
                compression="snappy"
            )
        
        if all_conditions:
            conditions_df = pl.DataFrame(all_conditions)
            conditions_df.write_parquet(
                os.path.join(self.output_dir, f"conditions_batch_{batch_num:04d}.parquet"),
                compression="snappy"
            )
        
        if all_medications:
            medications_df = pl.DataFrame(all_medications)
            medications_df.write_parquet(
                os.path.join(self.output_dir, f"medications_batch_{batch_num:04d}.parquet"),
                compression="snappy"
            )
    
    def consolidate_batches(self):
        """Consolidate batch files into final datasets"""
        print("Consolidating batch files...")
        
        # Consolidate patients
        patient_files = glob.glob(os.path.join(self.output_dir, "patients_batch_*.parquet"))
        if patient_files:
            consolidated_df = pl.concat([pl.read_parquet(f) for f in patient_files])
            consolidated_df.write_parquet(os.path.join(self.output_dir, "patients.parquet"))
            consolidated_df.write_csv(os.path.join(self.output_dir, "patients.csv"))
            
            # Clean up batch files
            for f in patient_files:
                os.remove(f)
        
        # Repeat for other data types...
        self._consolidate_data_type("encounters")
        self._consolidate_data_type("conditions") 
        self._consolidate_data_type("medications")
        
        print(f"Consolidation complete. Total patients processed: {self.total_processed}")
    
    def _consolidate_data_type(self, data_type: str):
        """Consolidate batch files for specific data type"""
        batch_files = glob.glob(os.path.join(self.output_dir, f"{data_type}_batch_*.parquet"))
        if batch_files:
            consolidated_df = pl.concat([pl.read_parquet(f) for f in batch_files])
            consolidated_df.write_parquet(os.path.join(self.output_dir, f"{data_type}.parquet"))
            consolidated_df.write_csv(os.path.join(self.output_dir, f"{data_type}.csv"))
            
            # Clean up batch files
            for f in batch_files:
                os.remove(f)

# Usage for large datasets
def generate_million_patients():
    """Generate 1 million patients efficiently"""
    processor = LargeDatasetProcessor(batch_size=50000, output_dir="./large_dataset")
    processor.generate_large_dataset(1000000)
    processor.consolidate_batches()
```

---

This technical user guide provides comprehensive coverage of the Synthetic Healthcare Data Generator's architecture, implementation, usage, and extension capabilities. It serves as both a user manual and developer reference for healthcare data interoperability testing and VA migration simulation scenarios.