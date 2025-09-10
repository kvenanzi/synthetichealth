#!/usr/bin/env python3
"""
Healthcare Migration Configuration

This module provides comprehensive configuration management for healthcare data migrations
including quality thresholds, HIPAA compliance requirements, clinical validation rules,
and monitoring parameters optimized for healthcare environments.

Key Configuration Areas:
- Clinical data quality thresholds by criticality level
- HIPAA compliance requirements and monitoring
- Healthcare-specific validation rules and weights  
- Alert thresholds and escalation policies
- Migration stage configurations for healthcare workflows
- Regulatory compliance tracking parameters

Author: Healthcare Data Quality Engineer
Date: 2025-09-09
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import os

class HealthcareStandard(Enum):
    """Healthcare interoperability standards"""
    HL7_FHIR = "hl7_fhir"
    HL7_V2 = "hl7_v2"
    CDA = "cda"
    DICOM = "dicom"
    X12 = "x12"

class ClinicalDataType(Enum):
    """Clinical data types with different validation requirements"""
    DEMOGRAPHICS = "demographics"
    ALLERGIES = "allergies"
    MEDICATIONS = "medications"
    CONDITIONS = "conditions"
    PROCEDURES = "procedures"
    OBSERVATIONS = "observations"
    ENCOUNTERS = "encounters"
    IMMUNIZATIONS = "immunizations"
    FAMILY_HISTORY = "family_history"
    SOCIAL_HISTORY = "social_history"

@dataclass
class ClinicalValidationRule:
    """Configuration for clinical data validation rules"""
    data_type: ClinicalDataType
    rule_name: str
    description: str
    criticality_level: str  # critical, high, medium, low
    validation_logic: str   # Description of validation logic
    required_fields: List[str]
    optional_fields: List[str] = field(default_factory=list)
    business_rules: List[str] = field(default_factory=list)
    error_tolerance: float = 0.0  # Acceptable error rate (0.0 = no errors allowed)
    weight: float = 1.0  # Weight in overall quality calculation

@dataclass
class QualityThresholds:
    """Quality score thresholds by data criticality and dimension"""
    
    # Critical data thresholds (life-threatening impact)
    critical_completeness: float = 1.0      # 100% - No missing critical data allowed
    critical_accuracy: float = 0.98         # 98% - Minimal tolerance for inaccuracy
    critical_consistency: float = 0.95      # 95% - High consistency required
    critical_hipaa_compliance: float = 1.0  # 100% - Full HIPAA compliance required
    
    # High priority data thresholds (significant clinical impact)
    high_completeness: float = 0.95         # 95% - Minimal missing data allowed
    high_accuracy: float = 0.92            # 92% - Some tolerance for minor errors
    high_consistency: float = 0.90         # 90% - Good consistency required
    high_hipaa_compliance: float = 0.98    # 98% - Near-perfect HIPAA compliance
    
    # Medium priority data thresholds (moderate clinical impact)
    medium_completeness: float = 0.85       # 85% - Moderate missing data tolerance
    medium_accuracy: float = 0.85          # 85% - Moderate accuracy tolerance
    medium_consistency: float = 0.80       # 80% - Reasonable consistency
    medium_hipaa_compliance: float = 0.95  # 95% - Strong HIPAA compliance
    
    # Low priority data thresholds (minimal clinical impact)
    low_completeness: float = 0.75          # 75% - Higher missing data tolerance
    low_accuracy: float = 0.80             # 80% - Basic accuracy requirements
    low_consistency: float = 0.70          # 70% - Basic consistency requirements
    low_hipaa_compliance: float = 0.90     # 90% - Good HIPAA compliance

@dataclass
class AlertConfiguration:
    """Configuration for quality monitoring alerts"""
    
    # Alert thresholds by severity
    critical_quality_threshold: float = 0.70   # Below this triggers critical alert
    high_quality_threshold: float = 0.80       # Below this triggers high alert
    medium_quality_threshold: float = 0.85     # Below this triggers medium alert
    
    # HIPAA-specific alert thresholds
    hipaa_critical_threshold: float = 0.95     # Below this triggers critical HIPAA alert
    phi_exposure_tolerance: int = 0            # Number of PHI exposures allowed (0 = none)
    
    # Alert escalation timing (minutes)
    critical_alert_escalation: int = 5         # Escalate critical alerts after 5 minutes
    high_alert_escalation: int = 15            # Escalate high alerts after 15 minutes
    medium_alert_escalation: int = 60          # Escalate medium alerts after 1 hour
    
    # Alert frequency limits (per hour)
    max_critical_alerts_per_hour: int = 10
    max_high_alerts_per_hour: int = 25
    max_medium_alerts_per_hour: int = 50
    
    # Automatic resolution settings
    auto_resolve_after_hours: int = 24         # Auto-resolve alerts after 24 hours
    require_manual_critical_resolution: bool = True  # Critical alerts need manual resolution

@dataclass
class MigrationStageConfiguration:
    """Healthcare-specific configuration for migration stages"""
    
    # Stage success rate targets
    extract_success_target: float = 0.99       # 99% success rate for data extraction
    transform_success_target: float = 0.95     # 95% success rate for data transformation
    validate_success_target: float = 0.92      # 92% success rate for validation
    load_success_target: float = 0.90          # 90% success rate for data loading
    
    # Timeout configurations (seconds)
    extract_timeout: int = 300                 # 5 minutes for extraction
    transform_timeout: int = 600               # 10 minutes for transformation
    validate_timeout: int = 480                # 8 minutes for validation
    load_timeout: int = 720                    # 12 minutes for loading
    
    # Retry configurations
    max_retries_per_stage: int = 3
    retry_backoff_seconds: int = 30
    
    # Batch size recommendations
    small_batch_size: int = 50                 # For high-risk migrations
    medium_batch_size: int = 200               # For standard migrations
    large_batch_size: int = 500                # For low-risk migrations

@dataclass
class HIPAAComplianceConfiguration:
    """HIPAA compliance monitoring configuration"""
    
    # PHI detection patterns
    phi_patterns: Dict[str, str] = field(default_factory=lambda: {
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "phone": r"\(\d{3}\) \d{3}-\d{4}",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "mrn": r"\d{8,12}",
        "account_number": r"ACC\d{8,}"
    })
    
    # Required PHI protection measures
    required_encryption: bool = True
    require_access_logging: bool = True
    minimum_necessary_principle: bool = True
    
    # Audit trail requirements
    audit_log_retention_days: int = 2555       # 7 years (HIPAA requirement)
    require_user_authentication: bool = True
    log_all_phi_access: bool = True
    
    # Breach notification thresholds
    breach_notification_threshold: int = 500   # Report breaches affecting 500+ individuals
    minor_incident_threshold: int = 1          # Log all incidents affecting any individuals
    
    # Compliance scoring weights
    encryption_weight: float = 0.3
    access_control_weight: float = 0.25
    audit_trail_weight: float = 0.25
    minimum_necessary_weight: float = 0.2

class HealthcareMigrationConfig:
    """Comprehensive healthcare migration configuration management"""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration from file or defaults"""
        self.quality_thresholds = QualityThresholds()
        self.alert_config = AlertConfiguration()
        self.stage_config = MigrationStageConfiguration()
        self.hipaa_config = HIPAAComplianceConfiguration()
        self.clinical_validation_rules = self._initialize_clinical_rules()
        self.terminology_mappings = self._initialize_terminology_mappings()
        
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def _initialize_clinical_rules(self) -> List[ClinicalValidationRule]:
        """Initialize comprehensive clinical data validation rules"""
        rules = []
        
        # Demographics validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.DEMOGRAPHICS,
            rule_name="required_demographics",
            description="Patient must have complete demographic information",
            criticality_level="critical",
            validation_logic="First name, last name, DOB, gender, and MRN must be present and non-empty",
            required_fields=["first_name", "last_name", "birthdate", "gender", "mrn"],
            optional_fields=["middle_name", "suffix", "preferred_name"],
            business_rules=[
                "Birthdate must be in valid date format",
                "MRN must follow institutional format (8 digits with check digit)",
                "Gender must be from approved value set"
            ],
            error_tolerance=0.0,
            weight=2.0
        ))
        
        # Allergy validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.ALLERGIES,
            rule_name="allergy_completeness",
            description="Allergy information must be complete and accurate",
            criticality_level="critical",
            validation_logic="All allergies must have substance, reaction, and severity documented",
            required_fields=["substance", "reaction", "severity"],
            optional_fields=["onset_date", "notes"],
            business_rules=[
                "Substance must be from standardized allergy database",
                "Severity must be: mild, moderate, or severe",
                "Reaction must be clinically valid"
            ],
            error_tolerance=0.02,  # 2% tolerance for minor allergy data issues
            weight=3.0  # Higher weight due to patient safety impact
        ))
        
        # Medication validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.MEDICATIONS,
            rule_name="medication_accuracy",
            description="Medication information must be complete and clinically accurate",
            criticality_level="critical",
            validation_logic="All medications must have drug name, dosage, frequency, and route",
            required_fields=["medication", "dosage", "frequency", "route"],
            optional_fields=["prescriber", "start_date", "end_date", "indication"],
            business_rules=[
                "Medication must be from approved formulary",
                "Dosage must be within therapeutic range",
                "Route must be valid for the medication",
                "Frequency must use standardized format"
            ],
            error_tolerance=0.01,  # 1% tolerance for medication errors
            weight=3.0
        ))
        
        # Condition validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.CONDITIONS,
            rule_name="condition_coding_accuracy",
            description="Medical conditions must have accurate ICD-10 coding",
            criticality_level="high",
            validation_logic="All conditions must have valid ICD-10 codes and clinical status",
            required_fields=["condition", "icd10_code", "status"],
            optional_fields=["onset_date", "resolved_date", "severity"],
            business_rules=[
                "ICD-10 code must be valid and current",
                "Status must be: active, resolved, or remission",
                "Onset date must precede resolved date if both present"
            ],
            error_tolerance=0.05,  # 5% tolerance for coding errors
            weight=2.0
        ))
        
        # Vital signs validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.OBSERVATIONS,
            rule_name="vital_signs_validity",
            description="Vital signs must be within physiologically plausible ranges",
            criticality_level="high",
            validation_logic="Vital signs must be within human physiological limits",
            required_fields=["type", "value", "unit"],
            optional_fields=["date", "time", "performer"],
            business_rules=[
                "Blood pressure: systolic 60-250, diastolic 30-150 mmHg",
                "Heart rate: 30-200 bpm",
                "Temperature: 90-110°F",
                "Weight: 5-500 lbs",
                "Height: 10-100 inches"
            ],
            error_tolerance=0.03,  # 3% tolerance for measurement errors
            weight=2.0
        ))
        
        # Encounter validation rules
        rules.append(ClinicalValidationRule(
            data_type=ClinicalDataType.ENCOUNTERS,
            rule_name="encounter_data_integrity",
            description="Encounter records must have consistent dates and providers",
            criticality_level="medium",
            validation_logic="Encounters must have valid dates, types, and provider information",
            required_fields=["date", "type", "provider"],
            optional_fields=["location", "reason", "disposition"],
            business_rules=[
                "Encounter date must not be in the future",
                "Encounter type must be from approved value set",
                "Provider must be valid healthcare professional"
            ],
            error_tolerance=0.08,  # 8% tolerance for administrative data
            weight=1.0
        ))
        
        return rules
    
    def _initialize_terminology_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize healthcare terminology mappings and standards"""
        return {
            "icd10_validation": {
                "pattern": r"^[A-Z]\d{2}\.?\d*$",
                "description": "ICD-10 code format validation",
                "examples": ["I10", "E11.9", "J45.909"]
            },
            "cpt_validation": {
                "pattern": r"^\d{5}$",
                "description": "CPT code format validation", 
                "examples": ["99213", "80053", "36415"]
            },
            "rxnorm_validation": {
                "pattern": r"^\d{1,8}$",
                "description": "RxNorm concept ID validation",
                "examples": ["6809", "29046", "83367"]
            },
            "snomed_validation": {
                "pattern": r"^\d{6,18}$",
                "description": "SNOMED CT concept ID validation",
                "examples": ["44054006", "38341003", "195967001"]
            },
            "loinc_validation": {
                "pattern": r"^\d{1,5}-\d$",
                "description": "LOINC code format validation",
                "examples": ["33747-0", "2093-3", "8302-2"]
            }
        }
    
    def get_quality_threshold(self, criticality: str, dimension: str) -> float:
        """Get quality threshold for specific criticality level and dimension"""
        threshold_map = {
            "critical": {
                "completeness": self.quality_thresholds.critical_completeness,
                "accuracy": self.quality_thresholds.critical_accuracy,
                "consistency": self.quality_thresholds.critical_consistency,
                "hipaa_compliance": self.quality_thresholds.critical_hipaa_compliance
            },
            "high": {
                "completeness": self.quality_thresholds.high_completeness,
                "accuracy": self.quality_thresholds.high_accuracy,
                "consistency": self.quality_thresholds.high_consistency,
                "hipaa_compliance": self.quality_thresholds.high_hipaa_compliance
            },
            "medium": {
                "completeness": self.quality_thresholds.medium_completeness,
                "accuracy": self.quality_thresholds.medium_accuracy,
                "consistency": self.quality_thresholds.medium_consistency,
                "hipaa_compliance": self.quality_thresholds.medium_hipaa_compliance
            },
            "low": {
                "completeness": self.quality_thresholds.low_completeness,
                "accuracy": self.quality_thresholds.low_accuracy,
                "consistency": self.quality_thresholds.low_consistency,
                "hipaa_compliance": self.quality_thresholds.low_hipaa_compliance
            }
        }
        
        return threshold_map.get(criticality, {}).get(dimension, 0.8)  # Default 80%
    
    def get_clinical_rules_by_type(self, data_type: ClinicalDataType) -> List[ClinicalValidationRule]:
        """Get clinical validation rules for specific data type"""
        return [rule for rule in self.clinical_validation_rules if rule.data_type == data_type]
    
    def get_critical_data_types(self) -> List[ClinicalDataType]:
        """Get list of data types considered critical for patient safety"""
        critical_rules = [rule for rule in self.clinical_validation_rules 
                         if rule.criticality_level == "critical"]
        return list(set(rule.data_type for rule in critical_rules))
    
    def validate_terminology_code(self, code_type: str, code_value: str) -> Tuple[bool, str]:
        """Validate terminology code against standard patterns"""
        if code_type not in self.terminology_mappings:
            return False, f"Unknown code type: {code_type}"
        
        mapping = self.terminology_mappings[code_type]
        pattern = mapping.get("pattern", "")
        
        import re
        if re.match(pattern, code_value):
            return True, "Valid code format"
        else:
            return False, f"Invalid {code_type} format. Expected pattern: {pattern}"
    
    def get_recommended_batch_size(self, risk_level: str) -> int:
        """Get recommended batch size based on migration risk level"""
        risk_batch_map = {
            "high": self.stage_config.small_batch_size,
            "medium": self.stage_config.medium_batch_size,
            "low": self.stage_config.large_batch_size
        }
        return risk_batch_map.get(risk_level, self.stage_config.medium_batch_size)
    
    def should_trigger_alert(self, quality_score: float, criticality: str) -> Tuple[bool, str]:
        """Determine if quality score should trigger an alert"""
        if criticality == "critical" and quality_score < self.alert_config.critical_quality_threshold:
            return True, "critical"
        elif criticality == "high" and quality_score < self.alert_config.high_quality_threshold:
            return True, "high"
        elif quality_score < self.alert_config.medium_quality_threshold:
            return True, "medium"
        else:
            return False, "none"
    
    def get_hipaa_compliance_requirements(self) -> Dict[str, Any]:
        """Get HIPAA compliance requirements and thresholds"""
        return {
            "encryption_required": self.hipaa_config.required_encryption,
            "access_logging_required": self.hipaa_config.require_access_logging,
            "minimum_necessary": self.hipaa_config.minimum_necessary_principle,
            "audit_retention_days": self.hipaa_config.audit_log_retention_days,
            "breach_threshold": self.hipaa_config.breach_notification_threshold,
            "compliance_weights": {
                "encryption": self.hipaa_config.encryption_weight,
                "access_control": self.hipaa_config.access_control_weight,
                "audit_trail": self.hipaa_config.audit_trail_weight,
                "minimum_necessary": self.hipaa_config.minimum_necessary_weight
            }
        }
    
    def export_config(self, filename: str) -> None:
        """Export configuration to JSON file"""
        config_dict = {
            "quality_thresholds": self.quality_thresholds.__dict__,
            "alert_config": self.alert_config.__dict__,
            "stage_config": self.stage_config.__dict__,
            "hipaa_config": {
                k: v for k, v in self.hipaa_config.__dict__.items() 
                if k != "phi_patterns"  # Skip regex patterns for JSON
            },
            "clinical_validation_rules": [
                {
                    "data_type": rule.data_type.value,
                    "rule_name": rule.rule_name,
                    "description": rule.description,
                    "criticality_level": rule.criticality_level,
                    "validation_logic": rule.validation_logic,
                    "required_fields": rule.required_fields,
                    "optional_fields": rule.optional_fields,
                    "business_rules": rule.business_rules,
                    "error_tolerance": rule.error_tolerance,
                    "weight": rule.weight
                }
                for rule in self.clinical_validation_rules
            ],
            "terminology_mappings": self.terminology_mappings
        }
        
        with open(filename, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def load_from_file(self, filename: str) -> None:
        """Load configuration from JSON file"""
        try:
            with open(filename, 'r') as f:
                config_dict = json.load(f)
            
            # Update quality thresholds
            if "quality_thresholds" in config_dict:
                for key, value in config_dict["quality_thresholds"].items():
                    if hasattr(self.quality_thresholds, key):
                        setattr(self.quality_thresholds, key, value)
            
            # Update alert config
            if "alert_config" in config_dict:
                for key, value in config_dict["alert_config"].items():
                    if hasattr(self.alert_config, key):
                        setattr(self.alert_config, key, value)
            
            # Update stage config
            if "stage_config" in config_dict:
                for key, value in config_dict["stage_config"].items():
                    if hasattr(self.stage_config, key):
                        setattr(self.stage_config, key, value)
            
            # Update clinical validation rules
            if "clinical_validation_rules" in config_dict:
                self.clinical_validation_rules = []
                for rule_dict in config_dict["clinical_validation_rules"]:
                    rule = ClinicalValidationRule(
                        data_type=ClinicalDataType(rule_dict["data_type"]),
                        rule_name=rule_dict["rule_name"],
                        description=rule_dict["description"],
                        criticality_level=rule_dict["criticality_level"],
                        validation_logic=rule_dict["validation_logic"],
                        required_fields=rule_dict["required_fields"],
                        optional_fields=rule_dict.get("optional_fields", []),
                        business_rules=rule_dict.get("business_rules", []),
                        error_tolerance=rule_dict.get("error_tolerance", 0.0),
                        weight=rule_dict.get("weight", 1.0)
                    )
                    self.clinical_validation_rules.append(rule)
            
            print(f"Configuration loaded successfully from {filename}")
            
        except Exception as e:
            print(f"Error loading configuration from {filename}: {e}")
            print("Using default configuration values")

# Create default configuration instance
default_healthcare_config = HealthcareMigrationConfig()

# Export for easy import
__all__ = [
    'HealthcareMigrationConfig',
    'ClinicalValidationRule', 
    'QualityThresholds',
    'AlertConfiguration',
    'MigrationStageConfiguration',
    'HIPAAComplianceConfiguration',
    'ClinicalDataType',
    'HealthcareStandard',
    'default_healthcare_config'
]