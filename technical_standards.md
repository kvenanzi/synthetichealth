# Technical Implementation: Multi-Standard Healthcare Data Generator

## Overview
This document outlines the technical implementation to extend the synthetic patient data generator to support VistA MUMPS, HL7 v2, and FHIR R4 formats for healthcare migration simulation.

## Current Architecture Analysis

### Existing Structure
```python
# Current flow:
generate_patient() → generate_encounters() → generate_conditions() 
→ generate_medications() → save as CSV/Parquet
```

### Current Data Model
- Simple dictionary-based records
- Polars DataFrames for output
- Basic medical relationships
- Limited to tabular formats

## Enhanced Architecture Design

### 1. Core Data Model Extensions

#### Base Patient Record (Enhanced)
```python
class PatientRecord:
    def __init__(self):
        self.patient_id = str(uuid.uuid4())
        self.vista_id = None  # VistA patient IEN
        self.mrn = None       # Medical Record Number
        self.ssn = None
        self.demographics = {}
        self.encounters = []
        self.conditions = []
        self.medications = []
        # ... other clinical data
        self.metadata = {
            'source_system': 'synthetic',
            'migration_status': 'pending',
            'data_quality_score': 1.0
        }
```

#### Medical Coding Systems
```python
TERMINOLOGY_MAPPINGS = {
    'conditions': {
        'Diabetes': {
            'icd9': '250.00',
            'icd10': 'E11.9', 
            'snomed': '44054006',
            'vista_local': '7100001'
        },
        'Hypertension': {
            'icd9': '401.9',
            'icd10': 'I10',
            'snomed': '38341003', 
            'vista_local': '7100002'
        }
        # ... expanded for all conditions
    },
    'medications': {
        'Metformin': {
            'rxnorm': '6809',
            'ndc': '00093-1087-01',
            'vista_local': 'MET500TAB'
        }
        # ... expanded for all medications
    }
}
```

### 2. Output Format Implementations

#### A. VistA MUMPS Global Format
```python
class VistaFormatter:
    def format_patient(self, patient):
        """Generate VistA-style MUMPS global structures"""
        globals_data = {}
        
        # Patient Demographics Global ^DPT
        dpt_record = {
            f"^DPT({patient.vista_id},0)": f"{patient.last_name},{patient.first_name}",
            f"^DPT({patient.vista_id},.03)": patient.birthdate,
            f"^DPT({patient.vista_id},.02)": self.gender_code(patient.gender),
            f"^DPT({patient.vista_id},.09)": patient.ssn,
            f"^DPT({patient.vista_id},.1)": patient.race_code(),
        }
        
        # Admission/Discharge/Transfer Global ^DGPM  
        for i, encounter in enumerate(patient.encounters):
            dgpm_record = {
                f"^DGPM({encounter.vista_id},0)": f"{patient.vista_id}^{encounter.admission_date}^{encounter.type_code}",
                f"^DGPM({encounter.vista_id},.01)": patient.vista_id,
                f"^DGPM({encounter.vista_id},.02)": encounter.admission_date,
                f"^DGPM({encounter.vista_id},.06)": encounter.ward_code
            }
            globals_data.update(dgpm_record)
            
        return globals_data
    
    def export_to_mumps_extract(self, patients, filename):
        """Export to VistA-compatible MUMPS extract format"""
        with open(filename, 'w') as f:
            for patient in patients:
                globals_data = self.format_patient(patient)
                for global_ref, value in globals_data.items():
                    f.write(f"{global_ref}={value}\n")
```

#### B. HL7 v2 Message Format
```python
class HL7v2Formatter:
    def create_adt_message(self, patient, encounter, message_type="A04"):
        """Generate HL7 v2 ADT message"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        message_control_id = str(uuid.uuid4())[:10]
        
        segments = []
        
        # MSH - Message Header
        msh = f"MSH|^~\\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|{timestamp}||ADT^{message_type}|{message_control_id}|P|2.5"
        segments.append(msh)
        
        # PID - Patient Identification  
        pid = (f"PID|1||{patient.mrn}^^^VA^MR~{patient.ssn}^^^USA^SS||"
               f"{patient.last_name}^{patient.first_name}^{patient.middle_name}||"
               f"{patient.birthdate}|{patient.gender}|||"
               f"{patient.address}^^{patient.city}^{patient.state}^{patient.zip}|"
               f"|{patient.phone}||{patient.language}|{patient.marital_status}|"
               f"|{patient.account_number}|||{patient.race}^{patient.ethnicity}")
        segments.append(pid)
        
        # PV1 - Patient Visit
        if encounter:
            pv1 = (f"PV1|1|{encounter.patient_class}|{encounter.assigned_location}||"
                   f"{encounter.admission_type}|||{encounter.attending_doctor}|"
                   f"{encounter.referring_doctor}||||{encounter.hospital_service}||"
                   f"{encounter.admission_source}|{encounter.admission_date}")
            segments.append(pv1)
            
        return "\r".join(segments)
    
    def create_oru_message(self, patient, observations):
        """Generate HL7 v2 ORU (lab results) message"""
        # Implementation for lab results messages
        pass
```

#### C. FHIR R4 Resource Format
```python
class FHIRFormatter:
    def create_patient_resource(self, patient):
        """Generate FHIR R4 Patient resource"""
        return {
            "resourceType": "Patient",
            "id": f"va-patient-{patient.patient_id}",
            "meta": {
                "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
            },
            "identifier": [
                {
                    "use": "usual",
                    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]},
                    "system": "https://va.gov/patient-id",
                    "value": patient.mrn
                },
                {
                    "use": "official", 
                    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]},
                    "system": "http://hl7.org/fhir/sid/us-ssn",
                    "value": patient.ssn
                }
            ],
            "name": [{
                "use": "official",
                "family": patient.last_name,
                "given": [patient.first_name, patient.middle_name]
            }],
            "gender": patient.gender,
            "birthDate": patient.birthdate,
            "address": [{
                "use": "home",
                "line": [patient.address],
                "city": patient.city,
                "state": patient.state,
                "postalCode": patient.zip,
                "country": "US"
            }],
            "extension": self._create_patient_extensions(patient)
        }
    
    def create_condition_resource(self, patient, condition):
        """Generate FHIR R4 Condition resource"""
        condition_coding = TERMINOLOGY_MAPPINGS['conditions'][condition.name]
        return {
            "resourceType": "Condition", 
            "id": f"condition-{condition.condition_id}",
            "subject": {"reference": f"Patient/va-patient-{patient.patient_id}"},
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": condition_coding['snomed'],
                        "display": condition.name
                    },
                    {
                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": condition_coding['icd10'], 
                        "display": condition.name
                    }
                ]
            },
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": condition.status}]
            },
            "onsetDateTime": condition.onset_date
        }
        
    def create_bundle(self, patient_resources):
        """Create FHIR Bundle containing all patient resources"""
        return {
            "resourceType": "Bundle",
            "type": "collection", 
            "timestamp": datetime.now().isoformat(),
            "entry": [{"resource": resource} for resource in patient_resources]
        }
```

### 3. Enhanced Generator Architecture

#### Main Generator Class Restructure
```python
class MultiFormatHealthcareGenerator:
    def __init__(self, config):
        self.config = config
        self.vista_formatter = VistaFormatter()
        self.hl7_formatter = HL7v2Formatter() 
        self.fhir_formatter = FHIRFormatter()
        self.terminology = TERMINOLOGY_MAPPINGS
        
    def generate_enhanced_patient(self, patient_id=None):
        """Generate patient with all required IDs and metadata"""
        patient = PatientRecord()
        patient.patient_id = patient_id or str(uuid.uuid4())
        patient.vista_id = self._generate_vista_ien()
        patient.mrn = self._generate_mrn()
        
        # Enhanced demographic generation with coding
        patient.demographics = self._generate_coded_demographics()
        patient.encounters = self._generate_coded_encounters(patient)
        patient.conditions = self._generate_coded_conditions(patient)
        patient.medications = self._generate_coded_medications(patient)
        
        return patient
        
    def export_multi_format(self, patients, output_dir):
        """Export patients in all supported formats"""
        formats = self.config.get('output_formats', ['csv', 'fhir', 'hl7', 'vista'])
        
        for fmt in formats:
            if fmt == 'vista':
                self.vista_formatter.export_to_mumps_extract(
                    patients, f"{output_dir}/vista_extract.txt"
                )
            elif fmt == 'hl7':
                self._export_hl7_messages(patients, output_dir)
            elif fmt == 'fhir':
                self._export_fhir_bundles(patients, output_dir)
            elif fmt == 'csv':
                self._export_csv_tables(patients, output_dir)
```

### 4. Migration Simulation Features

#### Migration Status Tracking
```python
class MigrationSimulator:
    def simulate_staged_migration(self, patients, stages=['extract', 'transform', 'load']):
        """Simulate phased migration with realistic delays and failures"""
        migration_log = []
        
        for stage in stages:
            for patient in patients:
                success_rate = self.config['migration_success_rates'][stage]
                if random.random() < success_rate:
                    patient.metadata['migration_status'] = f"{stage}_complete"
                    patient.metadata['data_quality_score'] *= 0.95  # Slight degradation
                else:
                    patient.metadata['migration_status'] = f"{stage}_failed"
                    patient.metadata['data_quality_score'] *= 0.8   # More degradation
                    
                migration_log.append({
                    'patient_id': patient.patient_id,
                    'stage': stage,
                    'status': patient.metadata['migration_status'],
                    'timestamp': datetime.now(),
                    'quality_score': patient.metadata['data_quality_score']
                })
                
        return migration_log
```

### 5. Dependencies & Libraries

#### New Requirements
```txt
# Add to requirements.txt
fhir.resources==6.5.0      # FHIR R4 resource models
hl7apy==1.3.3              # HL7 v2 message parsing
python-dateutil==2.8.2    # Enhanced date handling
jsonschema==4.17.3        # FHIR validation
lxml==4.9.2                # XML processing for CDA
```

### 6. Configuration Extensions

#### Enhanced config.yaml
```yaml
# Migration simulation settings
migration_settings:
  source_system: "vista"
  target_system: "oracle_health"
  migration_stages:
    - extract
    - transform 
    - validate
    - load
  success_rates:
    extract: 0.98
    transform: 0.95
    validate: 0.92
    load: 0.90

# Output format configuration  
output_formats:
  - csv          # Existing tabular format
  - fhir         # FHIR R4 JSON bundles
  - hl7          # HL7 v2 messages
  - vista        # MUMPS global extract
  - cda          # HL7 CDA documents

# Terminology settings
terminology:
  condition_coding_systems: ["icd9", "icd10", "snomed", "vista_local"]
  medication_coding_systems: ["rxnorm", "ndc", "vista_local"]
  validate_codes: true
  
# Data quality simulation
data_quality:
  introduce_errors: true
  error_rate: 0.05
  error_types: ["missing_data", "format_errors", "coding_errors"]
```

### 7. Implementation Phases

#### Phase 1: Core Extensions (Week 1-2)
- Enhance PatientRecord class with multiple IDs
- Add terminology mappings
- Implement basic FHIR formatter

#### Phase 2: HL7 v2 Support (Week 3)  
- Implement HL7 message creation
- Add message validation
- Create message export functionality

#### Phase 3: VistA MUMPS Format (Week 4)
- Research VistA global structure
- Implement MUMPS export format
- Add VistA-specific field mappings

#### Phase 4: Migration Simulation (Week 5)
- Add staged migration logic  
- Implement data quality degradation
- Create migration analytics

#### Phase 5: Integration & Testing (Week 6)
- End-to-end testing
- Performance optimization
- Documentation completion

### 8. Validation & Quality Assurance

#### FHIR Validation
```python
def validate_fhir_resources(self, resources):
    """Validate FHIR resources against R4 schemas"""
    from fhir.resources import construct_fhir_element
    
    validation_results = []
    for resource in resources:
        try:
            construct_fhir_element(resource['resourceType'], resource)
            validation_results.append({'valid': True, 'errors': []})
        except Exception as e:
            validation_results.append({'valid': False, 'errors': [str(e)]})
            
    return validation_results
```

#### HL7 v2 Validation  
```python
def validate_hl7_message(self, message):
    """Validate HL7 v2 message structure"""
    from hl7apy.parser import parse_message
    
    try:
        parsed = parse_message(message)
        return {'valid': True, 'structure': parsed.to_dict()}
    except Exception as e:
        return {'valid': False, 'error': str(e)}
```

This technical implementation provides a comprehensive roadmap for transforming the synthetic patient generator into a multi-standard healthcare data migration simulation platform.