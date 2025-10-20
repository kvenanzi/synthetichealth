#!/usr/bin/env python3
"""
Enhanced Healthcare Data Migration Status Tracking System

This module provides comprehensive migration status tracking capabilities for healthcare data migrations
with focus on patient-level granular tracking, data quality scoring, clinical validation, and HIPAA compliance.

Key Features:
- Granular patient-level migration tracking with clinical context
- Healthcare-specific data quality scoring frameworks
- Data quality degradation simulation with clinical scenarios
- Real-time quality monitoring and alerting
- HIPAA compliance tracking and audit trails
- Clinical data validation metrics and thresholds

Author: Healthcare Data Quality Engineer
Date: 2025-09-09
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Union
import uuid
from collections import defaultdict, deque
import threading
import time
import statistics
from abc import ABC, abstractmethod

# Configure logging for healthcare compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [AUDIT] %(message)s',
    handlers=[
        logging.FileHandler('migration_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationStageStatus(Enum):
    """Enhanced migration stage statuses with healthcare context"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"
    REQUIRES_INTERVENTION = "requires_intervention"
    HIPAA_VIOLATION_DETECTED = "hipaa_violation_detected"
    CLINICAL_VALIDATION_FAILED = "clinical_validation_failed"

class DataQualityDimension(Enum):
    """Healthcare-specific data quality dimensions"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    CLINICAL_RELEVANCE = "clinical_relevance"
    HIPAA_COMPLIANCE = "hipaa_compliance"

class ClinicalDataCriticality(Enum):
    """Clinical data criticality levels for quality scoring"""
    CRITICAL = "critical"          # Life-threatening data (allergies, vital signs, active medications)
    HIGH = "high"                  # Important clinical data (diagnoses, procedures, lab results)
    MEDIUM = "medium"              # Relevant clinical data (insurance, demographics)
    LOW = "low"                    # Administrative data (scheduling preferences)

class AlertSeverity(Enum):
    """Alert severity levels for migration monitoring"""
    CRITICAL = "critical"          # Immediate intervention required
    HIGH = "high"                  # Urgent attention needed
    MEDIUM = "medium"              # Should be addressed soon
    LOW = "low"                    # Informational

@dataclass
class PatientMigrationStatus:
    """Enhanced patient-level migration status tracking"""
    patient_id: str
    mrn: str
    patient_name: str
    migration_batch_id: str
    
    # Stage-level tracking
    current_stage: str = "extract"
    current_substage: str = "connect"
    stage_statuses: Dict[str, MigrationStageStatus] = field(default_factory=dict)
    stage_timestamps: Dict[str, datetime] = field(default_factory=dict)
    stage_durations: Dict[str, float] = field(default_factory=dict)
    stage_error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Data quality tracking
    initial_quality_score: float = 1.0
    current_quality_score: float = 1.0
    quality_by_dimension: Dict[str, float] = field(default_factory=dict)
    quality_degradation_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Clinical data validation
    clinical_data_elements: Dict[str, Any] = field(default_factory=dict)
    critical_data_intact: bool = True
    clinical_validation_errors: List[str] = field(default_factory=list)
    
    # HIPAA compliance tracking
    phi_elements_count: int = 0
    phi_protection_status: Dict[str, bool] = field(default_factory=dict)
    hipaa_compliance_score: float = 1.0
    compliance_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Audit trail
    migration_events: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log migration event with audit trail"""
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "details": details,
            "quality_score_at_time": self.current_quality_score
        }
        self.migration_events.append(event)
        self.last_updated = datetime.now()
        
        # Log to audit trail
        logger.info(f"Patient {self.patient_id} ({self.mrn}): {event_type} - {details}")

@dataclass
class DataQualityRule:
    """Healthcare-specific data quality validation rule"""
    rule_id: str
    name: str
    description: str
    dimension: DataQualityDimension
    criticality: ClinicalDataCriticality
    validation_function: callable
    weight: float = 1.0
    threshold: float = 0.8
    enabled: bool = True

@dataclass
class QualityAlert:
    """Data quality alert for migration monitoring"""
    alert_id: str
    patient_id: str
    mrn: str
    severity: AlertSeverity
    dimension: DataQualityDimension
    message: str
    threshold_value: float
    actual_value: float
    timestamp: datetime
    stage: str
    substage: str
    requires_intervention: bool = False
    resolved: bool = False
    resolution_notes: str = ""
    resolved_at: Optional[datetime] = None

class HealthcareDataQualityScorer:
    """Healthcare-specific data quality scoring framework"""
    
    def __init__(self):
        self.rules: Dict[str, DataQualityRule] = {}
        self.dimension_weights = {
            DataQualityDimension.COMPLETENESS: 0.25,
            DataQualityDimension.ACCURACY: 0.25,
            DataQualityDimension.CONSISTENCY: 0.15,
            DataQualityDimension.TIMELINESS: 0.10,
            DataQualityDimension.VALIDITY: 0.15,
            DataQualityDimension.CLINICAL_RELEVANCE: 0.05,
            DataQualityDimension.HIPAA_COMPLIANCE: 0.05
        }
        self.criticality_multipliers = {
            ClinicalDataCriticality.CRITICAL: 4.0,
            ClinicalDataCriticality.HIGH: 2.0,
            ClinicalDataCriticality.MEDIUM: 1.0,
            ClinicalDataCriticality.LOW: 0.5
        }
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize healthcare-specific quality rules"""
        
        # Completeness rules
        self.add_rule(DataQualityRule(
            rule_id="COMP001",
            name="Critical Demographics Completeness",
            description="Patient name, DOB, and MRN must be complete",
            dimension=DataQualityDimension.COMPLETENESS,
            criticality=ClinicalDataCriticality.CRITICAL,
            validation_function=self._validate_critical_demographics,
            threshold=1.0
        ))
        
        self.add_rule(DataQualityRule(
            rule_id="COMP002", 
            name="Allergy Information Completeness",
            description="Known allergies must be documented",
            dimension=DataQualityDimension.COMPLETENESS,
            criticality=ClinicalDataCriticality.CRITICAL,
            validation_function=self._validate_allergy_completeness,
            threshold=0.95
        ))
        
        # Accuracy rules
        self.add_rule(DataQualityRule(
            rule_id="ACC001",
            name="Medical Record Number Accuracy",
            description="MRN must follow institutional format and check digit validation",
            dimension=DataQualityDimension.ACCURACY,
            criticality=ClinicalDataCriticality.CRITICAL,
            validation_function=self._validate_mrn_accuracy,
            threshold=1.0
        ))
        
        self.add_rule(DataQualityRule(
            rule_id="ACC002",
            name="Medication Dosage Accuracy",
            description="Medication dosages must be within clinical ranges",
            dimension=DataQualityDimension.ACCURACY,
            criticality=ClinicalDataCriticality.HIGH,
            validation_function=self._validate_medication_dosages,
            threshold=0.98
        ))
        
        # Consistency rules
        self.add_rule(DataQualityRule(
            rule_id="CONS001",
            name="Date Consistency",
            description="Encounter dates must be consistent with patient timeline",
            dimension=DataQualityDimension.CONSISTENCY,
            criticality=ClinicalDataCriticality.HIGH,
            validation_function=self._validate_date_consistency,
            threshold=0.95
        ))
        
        # HIPAA compliance rules
        self.add_rule(DataQualityRule(
            rule_id="HIPAA001",
            name="PHI Protection Status",
            description="All PHI elements must maintain protection status during migration",
            dimension=DataQualityDimension.HIPAA_COMPLIANCE,
            criticality=ClinicalDataCriticality.CRITICAL,
            validation_function=self._validate_phi_protection,
            threshold=1.0
        ))
    
    def add_rule(self, rule: DataQualityRule):
        """Add a quality validation rule"""
        self.rules[rule.rule_id] = rule
    
    def calculate_patient_quality_score(self, patient_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Calculate comprehensive quality score for a patient"""
        dimension_scores = {}
        
        for dimension in DataQualityDimension:
            dimension_rules = [rule for rule in self.rules.values() 
                             if rule.dimension == dimension and rule.enabled]
            
            if not dimension_rules:
                dimension_scores[dimension.value] = 1.0
                continue
                
            rule_scores = []
            for rule in dimension_rules:
                try:
                    rule_score = rule.validation_function(patient_data)
                    # Apply criticality multiplier
                    weighted_score = rule_score * self.criticality_multipliers[rule.criticality]
                    rule_scores.append(weighted_score)
                except Exception as e:
                    logger.warning(f"Rule {rule.rule_id} failed: {e}")
                    rule_scores.append(0.0)
            
            dimension_scores[dimension.value] = min(1.0, statistics.mean(rule_scores)) if rule_scores else 1.0
        
        # Calculate weighted overall score
        overall_score = sum(
            dimension_scores[dimension.value] * self.dimension_weights[dimension]
            for dimension in DataQualityDimension
        )
        
        return overall_score, dimension_scores
    
    # Validation functions for quality rules
    def _validate_critical_demographics(self, patient_data: Dict[str, Any]) -> float:
        """Validate critical demographic completeness"""
        required_fields = ['first_name', 'last_name', 'birthdate', 'mrn']
        present_fields = sum(1 for field in required_fields 
                           if patient_data.get(field) and str(patient_data[field]).strip())
        return present_fields / len(required_fields)
    
    def _validate_allergy_completeness(self, patient_data: Dict[str, Any]) -> float:
        """Validate allergy information completeness"""
        allergies = patient_data.get('allergies', [])
        if not allergies:
            # Check if explicitly documented as "No Known Allergies"
            return 1.0 if patient_data.get('no_known_allergies', False) else 0.0
        
        # Check completeness of allergy records
        complete_allergies = 0
        for allergy in allergies:
            if (allergy.get('substance') and allergy.get('reaction') and 
                allergy.get('severity')):
                complete_allergies += 1
        
        return complete_allergies / len(allergies) if allergies else 0.0
    
    def _validate_mrn_accuracy(self, patient_data: Dict[str, Any]) -> float:
        """Validate MRN format and check digit"""
        mrn = patient_data.get('mrn', '')
        if not mrn:
            return 0.0
        
        # Basic format validation (example: 8 digits)
        if len(mrn) != 8 or not mrn.isdigit():
            return 0.0
        
        # Simple check digit validation (Luhn algorithm example)
        try:
            digits = [int(d) for d in mrn]
            checksum = sum(digits[::2]) + sum(sum(divmod(d*2, 10)) for d in digits[1::2])
            return 1.0 if checksum % 10 == 0 else 0.8
        except:
            return 0.0
    
    def _validate_medication_dosages(self, patient_data: Dict[str, Any]) -> float:
        """Validate medication dosage ranges"""
        medications = patient_data.get('medications', [])
        if not medications:
            return 1.0  # No medications is valid
        
        valid_dosages = 0
        for med in medications:
            dosage = med.get('dosage', '')
            medication_name = med.get('medication', '')
            
            # Simple dosage validation logic
            if dosage and self._is_valid_dosage_range(medication_name, dosage):
                valid_dosages += 1
        
        return valid_dosages / len(medications) if medications else 1.0
    
    def _validate_date_consistency(self, patient_data: Dict[str, Any]) -> float:
        """Validate date consistency across records"""
        birthdate = patient_data.get('birthdate')
        encounters = patient_data.get('encounters', [])
        
        if not birthdate or not encounters:
            return 1.0
        
        try:
            birth_date = datetime.fromisoformat(birthdate).date()
            consistent_dates = 0
            
            for encounter in encounters:
                encounter_date = encounter.get('date')
                if encounter_date:
                    enc_date = datetime.fromisoformat(encounter_date).date()
                    if enc_date >= birth_date:
                        consistent_dates += 1
            
            return consistent_dates / len(encounters) if encounters else 1.0
        except:
            return 0.0
    
    def _validate_phi_protection(self, patient_data: Dict[str, Any]) -> float:
        """Validate PHI protection status"""
        phi_fields = ['ssn', 'phone', 'email', 'address']
        protected_fields = 0
        
        for field in phi_fields:
            value = patient_data.get(field, '')
            # Check if field appears to be properly encrypted/protected
            if not value or self._is_protected_phi(str(value)):
                protected_fields += 1
        
        return protected_fields / len(phi_fields)
    
    def _is_valid_dosage_range(self, medication: str, dosage: str) -> bool:
        """Check if dosage is within expected range for medication"""
        # Simplified dosage validation
        dosage_ranges = {
            'Metformin': (500, 2000),  # mg
            'Lisinopril': (5, 40),     # mg
            'Atorvastatin': (10, 80)   # mg
        }
        
        try:
            # Extract numeric value from dosage string
            numeric_dose = float(''.join(filter(str.isdigit, dosage.split()[0])))
            if medication in dosage_ranges:
                min_dose, max_dose = dosage_ranges[medication]
                return min_dose <= numeric_dose <= max_dose
            return True  # Unknown medication, assume valid
        except:
            return False
    
    def _is_protected_phi(self, value: str) -> bool:
        """Check if PHI value appears to be encrypted/masked"""
        # Simple heuristic: check for patterns indicating encryption/masking
        if len(value) < 5:
            return False
        
        # Look for common masking patterns
        if '*' in value or 'X' in value or value.startswith('ENCRYPTED_'):
            return True
        
        # Check for hex patterns (encrypted data)
        try:
            int(value, 16)
            return len(value) > 10  # Likely encrypted if long hex string
        except ValueError:
            pass
        
        return False

class ClinicalDataDegradationSimulator:
    """Simulates realistic healthcare data quality degradation scenarios"""
    
    def __init__(self):
        self.degradation_scenarios = self._initialize_scenarios()
    
    def _initialize_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """Initialize healthcare-specific degradation scenarios"""
        return {
            "medication_dosage_corruption": {
                "description": "Medication dosages get corrupted during transformation",
                "probability": 0.05,
                "impact_severity": 0.8,
                "affected_fields": ["medications.dosage", "medications.frequency"],
                "degradation_type": "corruption"
            },
            "allergy_information_loss": {
                "description": "Critical allergy information is lost during migration",
                "probability": 0.02,
                "impact_severity": 0.9,
                "affected_fields": ["allergies"],
                "degradation_type": "data_loss"
            },
            "demographic_field_truncation": {
                "description": "Patient names and addresses get truncated",
                "probability": 0.08,
                "impact_severity": 0.3,
                "affected_fields": ["first_name", "last_name", "address"],
                "degradation_type": "truncation"
            },
            "date_format_inconsistency": {
                "description": "Date formats become inconsistent across records",
                "probability": 0.12,
                "impact_severity": 0.4,
                "affected_fields": ["birthdate", "encounters.date", "conditions.onset_date"],
                "degradation_type": "format_error"
            },
            "coding_system_mapping_error": {
                "description": "Medical codes get incorrectly mapped between systems",
                "probability": 0.06,
                "impact_severity": 0.6,
                "affected_fields": ["conditions.icd10_code", "procedures.cpt_code"],
                "degradation_type": "mapping_error"
            },
            "phi_exposure_incident": {
                "description": "PHI protection is compromised during migration",
                "probability": 0.01,
                "impact_severity": 1.0,
                "affected_fields": ["ssn", "phone", "email"],
                "degradation_type": "security_breach"
            },
            "vital_signs_precision_loss": {
                "description": "Vital signs lose precision during numeric conversion",
                "probability": 0.10,
                "impact_severity": 0.3,
                "affected_fields": ["observations.value"],
                "degradation_type": "precision_loss"
            }
        }
    
    def simulate_degradation(self, patient_data: Dict[str, Any], 
                           failure_context: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """Simulate data degradation based on failure context"""
        degradation_events = []
        modified_data = patient_data.copy()
        
        # Determine which scenarios to apply based on failure context
        failure_type = failure_context.get('failure_type', 'unknown')
        stage = failure_context.get('stage', 'unknown')
        severity = failure_context.get('severity', 0.5)
        
        for scenario_name, scenario in self.degradation_scenarios.items():
            # Adjust probability based on failure context
            adjusted_probability = scenario['probability'] * (1 + severity)
            
            if self._should_apply_scenario(scenario_name, failure_type, stage, adjusted_probability):
                modified_data, event_description = self._apply_degradation_scenario(
                    modified_data, scenario_name, scenario
                )
                degradation_events.append(event_description)
        
        return modified_data, degradation_events
    
    def _should_apply_scenario(self, scenario_name: str, failure_type: str, 
                              stage: str, probability: float) -> bool:
        """Determine if degradation scenario should be applied"""
        import random
        
        # Stage-specific scenario likelihood
        stage_multipliers = {
            "extract": {"phi_exposure_incident": 0.5, "data_loss": 1.5},
            "transform": {"format_error": 2.0, "mapping_error": 2.0, "truncation": 1.5},
            "validate": {"coding_system_mapping_error": 1.5},
            "load": {"precision_loss": 1.2, "corruption": 1.3}
        }
        
        multiplier = stage_multipliers.get(stage, {}).get(
            self.degradation_scenarios[scenario_name]["degradation_type"], 1.0
        )
        
        adjusted_probability = min(1.0, probability * multiplier)
        return random.random() < adjusted_probability
    
    def _apply_degradation_scenario(self, patient_data: Dict[str, Any], 
                                   scenario_name: str, scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Apply specific degradation scenario to patient data"""
        
        if scenario_name == "medication_dosage_corruption":
            return self._corrupt_medication_dosages(patient_data, scenario)
        elif scenario_name == "allergy_information_loss":
            return self._lose_allergy_information(patient_data, scenario)
        elif scenario_name == "demographic_field_truncation":
            return self._truncate_demographic_fields(patient_data, scenario)
        elif scenario_name == "date_format_inconsistency":
            return self._create_date_inconsistency(patient_data, scenario)
        elif scenario_name == "coding_system_mapping_error":
            return self._create_coding_errors(patient_data, scenario)
        elif scenario_name == "phi_exposure_incident":
            return self._expose_phi_data(patient_data, scenario)
        elif scenario_name == "vital_signs_precision_loss":
            return self._reduce_vital_signs_precision(patient_data, scenario)
        
        return patient_data, f"Unknown degradation scenario: {scenario_name}"
    
    def _corrupt_medication_dosages(self, patient_data: Dict[str, Any], 
                                   scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Corrupt medication dosage information"""
        import random
        medications = patient_data.get('medications', [])
        corrupted_count = 0
        
        for med in medications:
            if 'dosage' in med and random.random() < 0.3:  # 30% of medications affected
                original_dosage = med['dosage']
                # Introduce realistic corruption
                corrupted_dosage = self._corrupt_dosage_string(original_dosage)
                med['dosage'] = corrupted_dosage
                corrupted_count += 1
        
        return patient_data, f"Corrupted dosages for {corrupted_count} medications"
    
    def _lose_allergy_information(self, patient_data: Dict[str, Any], 
                                 scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Simulate loss of allergy information"""
        if 'allergies' in patient_data:
            original_count = len(patient_data['allergies'])
            # Randomly remove some allergies
            import random
            patient_data['allergies'] = [
                allergy for allergy in patient_data['allergies']
                if random.random() > 0.4  # 40% loss rate
            ]
            lost_count = original_count - len(patient_data['allergies'])
            return patient_data, f"Lost {lost_count} allergy records"
        
        return patient_data, "No allergy information to lose"
    
    def _truncate_demographic_fields(self, patient_data: Dict[str, Any], 
                                    scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Truncate demographic field values"""
        truncated_fields = []
        
        for field in ['first_name', 'last_name', 'address']:
            if field in patient_data and len(str(patient_data[field])) > 10:
                original_length = len(str(patient_data[field]))
                patient_data[field] = str(patient_data[field])[:10] + "..."
                truncated_fields.append(f"{field} ({original_length} -> 13 chars)")
        
        return patient_data, f"Truncated fields: {', '.join(truncated_fields)}"
    
    def _create_date_inconsistency(self, patient_data: Dict[str, Any], 
                                  scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Create date format inconsistencies"""
        import random
        
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y%m%d']
        modified_dates = []
        
        # Modify birthdate format
        if 'birthdate' in patient_data:
            try:
                original_date = datetime.fromisoformat(patient_data['birthdate'])
                new_format = random.choice(date_formats[1:])  # Avoid ISO format
                patient_data['birthdate'] = original_date.strftime(new_format)
                modified_dates.append('birthdate')
            except:
                pass
        
        return patient_data, f"Changed date formats for: {', '.join(modified_dates)}"
    
    def _create_coding_errors(self, patient_data: Dict[str, Any], 
                             scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Create medical coding mapping errors"""
        import random
        
        # Corrupt some ICD-10 codes
        conditions = patient_data.get('conditions', [])
        corrupted_codes = 0
        
        for condition in conditions:
            if 'icd10_code' in condition and random.random() < 0.2:
                original_code = condition['icd10_code']
                # Introduce typical mapping errors
                corrupted_code = self._corrupt_medical_code(original_code)
                condition['icd10_code'] = corrupted_code
                corrupted_codes += 1
        
        return patient_data, f"Corrupted {corrupted_codes} medical codes"
    
    def _expose_phi_data(self, patient_data: Dict[str, Any], 
                        scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Simulate PHI exposure incident"""
        exposed_fields = []
        
        for field in ['ssn', 'phone', 'email']:
            if field in patient_data:
                # Remove protection (simulate exposure)
                if str(patient_data[field]).startswith('ENCRYPTED_'):
                    patient_data[field] = patient_data[field].replace('ENCRYPTED_', '')
                    exposed_fields.append(field)
        
        return patient_data, f"PHI exposure in fields: {', '.join(exposed_fields)}"
    
    def _reduce_vital_signs_precision(self, patient_data: Dict[str, Any], 
                                     scenario: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Reduce precision of vital signs measurements"""
        observations = patient_data.get('observations', [])
        modified_count = 0
        
        for obs in observations:
            if 'value' in obs and isinstance(obs['value'], (int, float)):
                # Reduce precision by rounding
                original_value = obs['value']
                obs['value'] = round(original_value)
                if original_value != obs['value']:
                    modified_count += 1
        
        return patient_data, f"Reduced precision for {modified_count} vital sign measurements"
    
    def _corrupt_dosage_string(self, dosage: str) -> str:
        """Introduce realistic dosage corruption"""
        import random
        
        corruptions = [
            lambda x: x.replace('mg', 'g'),  # Unit error
            lambda x: x.replace(' ', ''),    # Spacing error
            lambda x: x + 'X',               # Extra character
            lambda x: x[:-1] if len(x) > 1 else x,  # Truncation
        ]
        
        return random.choice(corruptions)(dosage)
    
    def _corrupt_medical_code(self, code: str) -> str:
        """Introduce realistic medical code corruption"""
        import random
        
        if len(code) > 2:
            # Common errors: transposed digits, wrong decimal placement
            corruptions = [
                code[:-1] + str(random.randint(0, 9)),  # Last digit error
                code.replace('.', '') if '.' in code else code[:3] + '.' + code[3:],  # Decimal error
                code[1] + code[0] + code[2:],  # First two chars swapped
            ]
            return random.choice(corruptions)
        
        return code

class MigrationQualityMonitor:
    """Real-time quality monitoring and alerting system"""
    
    def __init__(self, quality_scorer: HealthcareDataQualityScorer):
        self.quality_scorer = quality_scorer
        self.active_alerts: Dict[str, QualityAlert] = {}
        self.alert_thresholds = {
            DataQualityDimension.COMPLETENESS: 0.85,
            DataQualityDimension.ACCURACY: 0.90,
            DataQualityDimension.CONSISTENCY: 0.80,
            DataQualityDimension.TIMELINESS: 0.75,
            DataQualityDimension.VALIDITY: 0.85,
            DataQualityDimension.CLINICAL_RELEVANCE: 0.70,
            DataQualityDimension.HIPAA_COMPLIANCE: 0.95
        }
        self.alert_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
    
    def monitor_patient_quality(self, patient_status: PatientMigrationStatus, 
                               patient_data: Dict[str, Any]) -> List[QualityAlert]:
        """Monitor patient data quality and generate alerts"""
        alerts = []
        
        # Calculate current quality scores
        overall_score, dimension_scores = self.quality_scorer.calculate_patient_quality_score(patient_data)
        
        # Update patient status
        patient_status.current_quality_score = overall_score
        patient_status.quality_by_dimension = dimension_scores
        
        # Check for quality threshold violations
        for dimension_str, score in dimension_scores.items():
            dimension = DataQualityDimension(dimension_str)
            threshold = self.alert_thresholds.get(dimension, 0.8)
            
            if score < threshold:
                alert = self._create_quality_alert(
                    patient_status, dimension, score, threshold
                )
                alerts.append(alert)
        
        # Check for critical data integrity issues
        if overall_score < 0.7:
            alert = self._create_critical_quality_alert(patient_status, overall_score)
            alerts.append(alert)
        
        # Store alerts
        with self._lock:
            for alert in alerts:
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
        
        return alerts
    
    def _create_quality_alert(self, patient_status: PatientMigrationStatus,
                             dimension: DataQualityDimension, score: float,
                             threshold: float) -> QualityAlert:
        """Create quality threshold violation alert"""
        severity = self._determine_alert_severity(dimension, score, threshold)
        
        alert = QualityAlert(
            alert_id=str(uuid.uuid4()),
            patient_id=patient_status.patient_id,
            mrn=patient_status.mrn,
            severity=severity,
            dimension=dimension,
            message=f"{dimension.value.title()} score ({score:.3f}) below threshold ({threshold:.3f})",
            threshold_value=threshold,
            actual_value=score,
            timestamp=datetime.now(),
            stage=patient_status.current_stage,
            substage=patient_status.current_substage,
            requires_intervention=(severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH])
        )
        
        return alert
    
    def _create_critical_quality_alert(self, patient_status: PatientMigrationStatus,
                                      overall_score: float) -> QualityAlert:
        """Create critical overall quality alert"""
        return QualityAlert(
            alert_id=str(uuid.uuid4()),
            patient_id=patient_status.patient_id,
            mrn=patient_status.mrn,
            severity=AlertSeverity.CRITICAL,
            dimension=DataQualityDimension.ACCURACY,  # Representative
            message=f"Critical quality degradation detected (score: {overall_score:.3f})",
            threshold_value=0.7,
            actual_value=overall_score,
            timestamp=datetime.now(),
            stage=patient_status.current_stage,
            substage=patient_status.current_substage,
            requires_intervention=True
        )
    
    def _determine_alert_severity(self, dimension: DataQualityDimension,
                                 score: float, threshold: float) -> AlertSeverity:
        """Determine alert severity based on dimension and score"""
        deficit = threshold - score
        
        # HIPAA compliance is always critical
        if dimension == DataQualityDimension.HIPAA_COMPLIANCE:
            return AlertSeverity.CRITICAL if deficit > 0.05 else AlertSeverity.HIGH
        
        # General severity mapping
        if deficit > 0.3:
            return AlertSeverity.CRITICAL
        elif deficit > 0.2:
            return AlertSeverity.HIGH
        elif deficit > 0.1:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[QualityAlert]:
        """Get active alerts, optionally filtered by severity"""
        with self._lock:
            alerts = list(self.active_alerts.values())
            if severity_filter:
                alerts = [alert for alert in alerts if alert.severity == severity_filter]
            return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Mark alert as resolved"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].resolved = True
                logger.info(f"Alert {alert_id} resolved: {resolution_notes}")
                return True
            return False
    
    def get_quality_dashboard_data(self) -> Dict[str, Any]:
        """Generate dashboard data for quality monitoring"""
        with self._lock:
            active_alerts = list(self.active_alerts.values())
            
            # Alert summary by severity
            alert_counts = {severity.value: 0 for severity in AlertSeverity}
            for alert in active_alerts:
                if not alert.resolved:
                    alert_counts[alert.severity.value] += 1
            
            # Alert trends (last 24 hours)
            now = datetime.now()
            recent_alerts = [
                alert for alert in self.alert_history
                if (now - alert.timestamp).total_seconds() < 86400
            ]
            
            # Quality dimension breakdown
            dimension_alerts = defaultdict(int)
            for alert in active_alerts:
                if not alert.resolved:
                    dimension_alerts[alert.dimension.value] += 1
            
            return {
                "timestamp": now,
                "alert_summary": alert_counts,
                "total_active_alerts": sum(alert_counts.values()),
                "alerts_requiring_intervention": sum(
                    1 for alert in active_alerts 
                    if alert.requires_intervention and not alert.resolved
                ),
                "recent_alert_trend": len(recent_alerts),
                "dimension_breakdown": dict(dimension_alerts),
                "system_status": self._determine_system_status(alert_counts)
            }
    
    def _determine_system_status(self, alert_counts: Dict[str, int]) -> str:
        """Determine overall system status based on alerts"""
        if alert_counts[AlertSeverity.CRITICAL.value] > 0:
            return "CRITICAL"
        elif alert_counts[AlertSeverity.HIGH.value] > 5:
            return "DEGRADED"
        elif alert_counts[AlertSeverity.HIGH.value] > 0 or alert_counts[AlertSeverity.MEDIUM.value] > 10:
            return "WARNING"
        else:
            return "HEALTHY"

# Export key classes for use in the main migration system
__all__ = [
    'PatientMigrationStatus',
    'HealthcareDataQualityScorer', 
    'ClinicalDataDegradationSimulator',
    'MigrationQualityMonitor',
    'DataQualityDimension',
    'ClinicalDataCriticality',
    'AlertSeverity',
    'QualityAlert',
    'MigrationStageStatus'
]
