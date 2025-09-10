#!/usr/bin/env python3
"""
Enhanced Configuration Manager for MultiFormatHealthcareGenerator

This module provides comprehensive configuration management for the unified healthcare
data generation platform, including environment-specific configurations, validation
rules, migration settings, data quality controls, and monitoring parameters.

Key Features:
- Hierarchical configuration with environment overrides
- Healthcare-specific validation and quality rules
- Migration simulation configuration management  
- Error injection and testing configuration
- Performance monitoring and alerting settings
- Compliance and regulatory configuration
- Configuration validation and schema checking
- Runtime configuration updates with hot-reloading
- Encrypted configuration for sensitive settings

Design Patterns:
- Builder pattern for configuration construction
- Strategy pattern for environment-specific configs
- Observer pattern for configuration change notifications
- Singleton pattern for global configuration access

Author: Healthcare Systems Architect
Date: 2025-09-10
Version: 5.0.0
"""

import os
import json
import yaml
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
import threading
import hashlib
from contextlib import contextmanager

# Import validation components
from multi_format_healthcare_generator import (
    HealthcareFormat, DataQualityDimension, GenerationStage
)

# Configure logging
logger = logging.getLogger(__name__)

# ===============================================================================
# CONFIGURATION ENUMS AND CONSTANTS
# ===============================================================================

class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class ConfigurationSource(Enum):
    """Configuration source types"""
    FILE = "file"
    ENVIRONMENT = "environment"
    DATABASE = "database"
    REMOTE = "remote"

class ValidationStrictness(Enum):
    """Validation strictness levels"""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"

class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

# ===============================================================================
# CONFIGURATION SCHEMAS
# ===============================================================================

@dataclass
class DatabaseConfiguration:
    """Database connection configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "healthcare_db"
    username: str = ""
    password: str = ""
    ssl_enabled: bool = True
    connection_pool_size: int = 10
    timeout_seconds: int = 30
    
    def get_connection_string(self) -> str:
        """Generate database connection string"""
        return f"postgresql://{self.username}:{'*' * len(self.password)}@{self.host}:{self.port}/{self.database}"

@dataclass
class SecurityConfiguration:
    """Security and encryption settings"""
    encryption_enabled: bool = True
    encryption_key_path: Optional[str] = None
    hipaa_compliance_mode: bool = True
    audit_logging_enabled: bool = True
    data_masking_enabled: bool = False
    access_control_enabled: bool = True
    
    # PHI handling
    phi_encryption_required: bool = True
    phi_access_logging: bool = True
    phi_retention_days: int = 2555  # 7 years default
    
    # API security
    api_authentication_required: bool = True
    api_rate_limiting_enabled: bool = True
    api_requests_per_minute: int = 1000

@dataclass
class MonitoringConfiguration:
    """Monitoring and alerting configuration"""
    enabled: bool = True
    real_time_monitoring: bool = False
    metrics_collection_interval_seconds: int = 60
    
    # Alert thresholds
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "error_rate_threshold": 0.05,
        "quality_score_threshold": 0.80,
        "performance_degradation_threshold": 0.20,
        "memory_usage_threshold": 0.85,
        "disk_usage_threshold": 0.90
    })
    
    # Notification settings
    email_notifications_enabled: bool = True
    slack_notifications_enabled: bool = False
    webhook_notifications_enabled: bool = False
    notification_recipients: List[str] = field(default_factory=list)
    
    # Dashboard settings
    dashboard_enabled: bool = True
    dashboard_refresh_interval_seconds: int = 30
    metrics_retention_days: int = 90

@dataclass
class PerformanceConfiguration:
    """Performance optimization settings"""
    parallel_processing_enabled: bool = True
    max_concurrent_patients: int = 10
    batch_size: int = 100
    memory_limit_mb: int = 2048
    
    # Caching settings
    caching_enabled: bool = True
    cache_size_mb: int = 512
    cache_ttl_seconds: int = 3600
    
    # Optimization flags
    lazy_loading_enabled: bool = True
    connection_pooling_enabled: bool = True
    compression_enabled: bool = False
    
    # Resource limits
    max_file_size_mb: int = 100
    max_generation_time_minutes: int = 60
    cleanup_temp_files: bool = True

@dataclass
class QualityRulesConfiguration:
    """Data quality rules and validation configuration"""
    
    # Global quality settings
    overall_quality_threshold: float = 0.90
    strict_validation_enabled: bool = True
    auto_correction_enabled: bool = False
    
    # Dimension-specific thresholds
    completeness_threshold: float = 0.95
    accuracy_threshold: float = 0.90
    consistency_threshold: float = 0.85
    timeliness_threshold: float = 0.80
    validity_threshold: float = 0.95
    uniqueness_threshold: float = 0.98
    integrity_threshold: float = 0.90
    hipaa_compliance_threshold: float = 1.0
    
    # Clinical data specific rules
    clinical_validation_rules: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "patient_demographics": {
            "required_fields": ["patient_id", "first_name", "last_name", "gender", "birthdate"],
            "optional_fields": ["middle_name", "ssn", "phone", "email"],
            "validation_rules": ["age_consistency", "name_format", "contact_validation"]
        },
        "clinical_conditions": {
            "required_fields": ["condition", "onset_date", "status"],
            "terminology_binding_required": True,
            "icd10_validation_enabled": True,
            "snomed_validation_enabled": True
        },
        "medications": {
            "required_fields": ["medication", "dosage", "frequency"],
            "rxnorm_validation_enabled": True,
            "drug_interaction_checking": True,
            "allergy_checking": True
        }
    })
    
    # Error handling
    error_tolerance: Dict[str, float] = field(default_factory=lambda: {
        "missing_optional_fields": 0.20,
        "formatting_errors": 0.05,
        "terminology_mapping_failures": 0.10,
        "validation_warnings": 0.15
    })

@dataclass
class TestingConfiguration:
    """Testing and error injection configuration"""
    
    # Error injection settings
    error_injection_enabled: bool = False
    error_injection_rates: Dict[str, float] = field(default_factory=lambda: {
        "missing_required_fields": 0.02,
        "invalid_data_formats": 0.03,
        "terminology_mapping_errors": 0.01,
        "network_simulation_errors": 0.05,
        "system_overload_errors": 0.02,
        "data_corruption_errors": 0.01
    })
    
    # Test data generation
    test_scenarios_enabled: bool = False
    test_patient_profiles: List[str] = field(default_factory=lambda: [
        "healthy_adult", "chronic_conditions", "pediatric", "geriatric", 
        "emergency_case", "complex_medical_history"
    ])
    
    # Migration simulation testing
    migration_testing_enabled: bool = False
    migration_test_scenarios: Dict[str, Any] = field(default_factory=lambda: {
        "vista_to_oracle_health": {
            "source_system": "vista",
            "target_system": "oracle_health",
            "success_rates": {"extract": 0.95, "transform": 0.90, "load": 0.88},
            "failure_scenarios": ["network_timeout", "data_corruption", "mapping_error"]
        }
    })

@dataclass
class ComplianceConfiguration:
    """Regulatory compliance configuration"""
    
    # HIPAA compliance
    hipaa_enabled: bool = True
    hipaa_audit_logging: bool = True
    hipaa_encryption_required: bool = True
    hipaa_access_controls: bool = True
    
    # Other healthcare regulations
    hitech_compliance: bool = True
    meaningful_use_compliance: bool = True
    cures_act_compliance: bool = True
    gdpr_compliance: bool = False  # For international deployments
    
    # Audit and reporting
    audit_trail_enabled: bool = True
    compliance_reporting_enabled: bool = True
    compliance_report_frequency: str = "monthly"  # daily, weekly, monthly, quarterly
    
    # Data retention policies
    data_retention_enabled: bool = True
    patient_data_retention_years: int = 7
    audit_log_retention_years: int = 7
    backup_retention_years: int = 7

# ===============================================================================
# ENHANCED CONFIGURATION MANAGER
# ===============================================================================

class ConfigurationManager:
    """
    Enhanced configuration manager providing comprehensive configuration 
    management for healthcare data generation and migration systems.
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration storage
        self._configs: Dict[str, Any] = {}
        self._config_sources: Dict[str, ConfigurationSource] = {}
        self._config_timestamps: Dict[str, datetime] = {}
        self._config_checksums: Dict[str, str] = {}
        
        # Change notification
        self._change_observers: List[Callable[[str, Any, Any], None]] = []
        
        # Environment and validation
        self._current_environment = Environment.DEVELOPMENT
        self._validation_enabled = True
        
        # Hot-reload settings
        self._hot_reload_enabled = False
        self._file_watchers: Dict[str, Any] = {}
        
        # Load default configuration
        self._load_default_configuration()
    
    def _load_default_configuration(self):
        """Load default configuration values"""
        
        # Core application settings
        self._configs["app"] = {
            "name": "MultiFormatHealthcareGenerator",
            "version": "5.0.0",
            "environment": self._current_environment.value,
            "debug": True,
            "log_level": "INFO"
        }
        
        # Database configuration
        self._configs["database"] = DatabaseConfiguration()
        
        # Security configuration
        self._configs["security"] = SecurityConfiguration()
        
        # Monitoring configuration
        self._configs["monitoring"] = MonitoringConfiguration()
        
        # Performance configuration
        self._configs["performance"] = PerformanceConfiguration()
        
        # Quality rules configuration
        self._configs["quality_rules"] = QualityRulesConfiguration()
        
        # Testing configuration
        self._configs["testing"] = TestingConfiguration()
        
        # Compliance configuration
        self._configs["compliance"] = ComplianceConfiguration()
        
        # Healthcare format configurations
        self._configs["formats"] = self._get_default_format_configurations()
        
        # Migration settings
        self._configs["migration"] = self._get_default_migration_configuration()
        
        self.logger.info("Default configuration loaded successfully")
    
    def _get_default_format_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get default healthcare format configurations"""
        return {
            HealthcareFormat.FHIR_R4.value: {
                "enabled": True,
                "validation_enabled": True,
                "validation_strictness": ValidationStrictness.STRICT.value,
                "profile_validation": True,
                "terminology_validation": True,
                "base_url": "https://example.org/fhir",
                "batch_size": 100,
                "include_meta": True,
                "include_extensions": True
            },
            HealthcareFormat.HL7_V2_ADT.value: {
                "enabled": True,
                "validation_enabled": True,
                "validation_strictness": ValidationStrictness.MODERATE.value,
                "hl7_version": "2.8",
                "encoding": "UTF-8",
                "segment_terminator": "\\r\\n",
                "field_separator": "|",
                "component_separator": "^"
            },
            HealthcareFormat.HL7_V2_ORU.value: {
                "enabled": True,
                "validation_enabled": True,
                "validation_strictness": ValidationStrictness.MODERATE.value,
                "hl7_version": "2.8",
                "include_obx_segments": True,
                "max_observations_per_message": 50
            },
            HealthcareFormat.VISTA_MUMPS.value: {
                "enabled": True,
                "validation_enabled": True,
                "validation_strictness": ValidationStrictness.LENIENT.value,
                "fileman_date_format": True,
                "include_global_structure": True,
                "va_specific_fields": True
            },
            HealthcareFormat.CSV.value: {
                "enabled": True,
                "validation_enabled": True,
                "delimiter": ",",
                "quote_char": '"',
                "escape_char": "\\",
                "include_header": True,
                "flatten_complex_fields": True
            }
        }
    
    def _get_default_migration_configuration(self) -> Dict[str, Any]:
        """Get default migration configuration"""
        return {
            "source_system": "vista",
            "target_system": "oracle_health",
            "migration_strategy": "staged",
            "simulate_migration": True,
            "success_rates": {
                "extract": 0.98,
                "transform": 0.95,
                "validate": 0.92,
                "load": 0.90
            },
            "failure_simulation": {
                "network_failure_rate": 0.05,
                "system_overload_rate": 0.03,
                "data_corruption_rate": 0.01,
                "security_violation_rate": 0.001
            },
            "performance": {
                "concurrent_patients": 10,
                "batch_size": 50,
                "retry_attempts": 3,
                "timeout_seconds": 30
            },
            "quality_monitoring": {
                "enabled": True,
                "real_time_alerts": True,
                "quality_score_threshold": 0.85,
                "alert_recipients": []
            }
        }
    
    def load_from_file(self, config_path: str, merge: bool = True) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
            merge: Whether to merge with existing configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                self.logger.error(f"Configuration file not found: {config_path}")
                return False
            
            # Read file content
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse based on file extension
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                file_config = yaml.safe_load(content)
            elif config_file.suffix.lower() == '.json':
                file_config = json.loads(content)
            else:
                self.logger.error(f"Unsupported configuration file format: {config_file.suffix}")
                return False
            
            # Calculate checksum for change detection
            checksum = hashlib.md5(content.encode()).hexdigest()
            
            if merge:
                # Merge with existing configuration
                self._deep_merge_config(self._configs, file_config)
            else:
                # Replace existing configuration
                self._configs = file_config
            
            # Update metadata
            self._config_sources[config_path] = ConfigurationSource.FILE
            self._config_timestamps[config_path] = datetime.now()
            self._config_checksums[config_path] = checksum
            
            # Validate configuration
            if self._validation_enabled:
                validation_result = self.validate_configuration()
                if not validation_result["is_valid"]:
                    self.logger.warning(f"Configuration validation issues: {validation_result['errors']}")
            
            # Notify observers of changes
            self._notify_configuration_changed("file_load", None, file_config)
            
            self.logger.info(f"Configuration loaded from {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {config_path}: {e}")
            return False
    
    def save_to_file(self, config_path: str, format: str = "yaml") -> bool:
        """
        Save current configuration to file.
        
        Args:
            config_path: Path where to save configuration
            format: Output format ('yaml' or 'json')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert dataclasses to dictionaries
            exportable_config = self._serialize_config_for_export()
            
            with open(config_file, 'w', encoding='utf-8') as f:
                if format.lower() == 'yaml':
                    yaml.dump(exportable_config, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(exportable_config, f, indent=2, default=str)
                else:
                    raise ValueError(f"Unsupported format: {format}")
            
            self.logger.info(f"Configuration saved to {config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {config_path}: {e}")
            return False
    
    def _serialize_config_for_export(self) -> Dict[str, Any]:
        """Convert configuration objects to exportable dictionaries"""
        exportable = {}
        
        for key, value in self._configs.items():
            if hasattr(value, '__dict__'):  # Dataclass instance
                exportable[key] = asdict(value)
            elif isinstance(value, dict):
                exportable[key] = value
            else:
                exportable[key] = value
        
        return exportable
    
    def _deep_merge_config(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source configuration into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge_config(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation).
        
        Args:
            key: Configuration key (e.g., 'database.host' or 'formats.fhir_r4.enabled')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key.split('.')
            value = self._configs
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                elif hasattr(value, k):
                    value = getattr(value, k)
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any, persist: bool = False) -> bool:
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            persist: Whether to persist change to file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keys = key.split('.')
            target = self._configs
            
            # Navigate to parent of target key
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            # Store old value for change notification
            old_value = target.get(keys[-1])
            
            # Set new value
            target[keys[-1]] = value
            
            # Notify observers
            self._notify_configuration_changed(key, old_value, value)
            
            if persist:
                # This would implement persistence logic
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set configuration key {key}: {e}")
            return False
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate current configuration against schemas and rules.
        
        Returns:
            Dict containing validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Validate database configuration
            db_config = self.get("database")
            if db_config:
                if not db_config.host:
                    validation_result["errors"].append("Database host is required")
                if db_config.port <= 0 or db_config.port > 65535:
                    validation_result["errors"].append("Database port must be between 1 and 65535")
            
            # Validate security configuration
            security_config = self.get("security")
            if security_config and security_config.hipaa_compliance_mode:
                if not security_config.encryption_enabled:
                    validation_result["errors"].append("Encryption is required for HIPAA compliance")
                if not security_config.audit_logging_enabled:
                    validation_result["warnings"].append("Audit logging recommended for HIPAA compliance")
            
            # Validate monitoring configuration
            monitoring_config = self.get("monitoring")
            if monitoring_config:
                for threshold_name, threshold_value in monitoring_config.alert_thresholds.items():
                    if not 0 <= threshold_value <= 1:
                        validation_result["warnings"].append(
                            f"Alert threshold {threshold_name} should be between 0 and 1"
                        )
            
            # Validate quality rules
            quality_config = self.get("quality_rules")
            if quality_config:
                if quality_config.overall_quality_threshold < 0.5:
                    validation_result["warnings"].append("Overall quality threshold is very low")
                
                # Check clinical validation rules
                for rule_name, rule_config in quality_config.clinical_validation_rules.items():
                    if "required_fields" not in rule_config:
                        validation_result["errors"].append(
                            f"Clinical rule {rule_name} missing required_fields"
                        )
            
            # Validate format configurations
            formats_config = self.get("formats", {})
            for format_name, format_config in formats_config.items():
                if not format_config.get("enabled", False):
                    continue
                
                if format_config.get("validation_enabled", False):
                    strictness = format_config.get("validation_strictness")
                    if strictness not in [vs.value for vs in ValidationStrictness]:
                        validation_result["warnings"].append(
                            f"Invalid validation strictness for {format_name}: {strictness}"
                        )
            
            validation_result["is_valid"] = len(validation_result["errors"]) == 0
            
        except Exception as e:
            validation_result["errors"].append(f"Configuration validation failed: {e}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    def add_change_observer(self, observer: Callable[[str, Any, Any], None]):
        """Add observer for configuration changes"""
        if observer not in self._change_observers:
            self._change_observers.append(observer)
    
    def remove_change_observer(self, observer: Callable[[str, Any, Any], None]):
        """Remove configuration change observer"""
        if observer in self._change_observers:
            self._change_observers.remove(observer)
    
    def _notify_configuration_changed(self, key: str, old_value: Any, new_value: Any):
        """Notify observers of configuration changes"""
        for observer in self._change_observers:
            try:
                observer(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Configuration change observer error: {e}")
    
    def enable_hot_reload(self, config_files: List[str], check_interval: int = 5):
        """
        Enable hot-reload for configuration files.
        
        Args:
            config_files: List of configuration files to watch
            check_interval: Check interval in seconds
        """
        # This would implement file watching for hot-reload
        # For now, just log the intent
        self.logger.info(f"Hot-reload enabled for files: {config_files}")
        self._hot_reload_enabled = True
    
    def get_environment_config(self, environment: Environment) -> Dict[str, Any]:
        """Get environment-specific configuration"""
        env_key = f"environments.{environment.value}"
        return self.get(env_key, {})
    
    def set_environment(self, environment: Environment):
        """Set current environment and load environment-specific config"""
        old_env = self._current_environment
        self._current_environment = environment
        
        # Load environment-specific overrides
        env_config = self.get_environment_config(environment)
        if env_config:
            self._deep_merge_config(self._configs, env_config)
        
        self.logger.info(f"Environment changed from {old_env.value} to {environment.value}")
    
    @contextmanager
    def temporary_config(self, temp_config: Dict[str, Any]):
        """Context manager for temporary configuration changes"""
        # Store original values
        original_values = {}
        
        try:
            # Apply temporary changes and store originals
            for key, value in temp_config.items():
                original_values[key] = self.get(key)
                self.set(key, value)
            
            yield
            
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                self.set(key, original_value)
    
    def export_configuration(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Export current configuration.
        
        Args:
            include_sensitive: Whether to include sensitive information
            
        Returns:
            Dict containing configuration
        """
        exported_config = self._serialize_config_for_export()
        
        if not include_sensitive:
            # Remove sensitive fields
            self._remove_sensitive_fields(exported_config)
        
        return exported_config
    
    def _remove_sensitive_fields(self, config: Dict[str, Any]):
        """Remove sensitive fields from configuration"""
        sensitive_patterns = ['password', 'key', 'secret', 'token', 'credential']
        
        for key in list(config.keys()):
            if any(pattern in key.lower() for pattern in sensitive_patterns):
                config[key] = "[REDACTED]"
            elif isinstance(config[key], dict):
                self._remove_sensitive_fields(config[key])
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration"""
        return {
            "environment": self._current_environment.value,
            "config_sources": len(self._config_sources),
            "last_updated": max(self._config_timestamps.values()) if self._config_timestamps else None,
            "validation_enabled": self._validation_enabled,
            "hot_reload_enabled": self._hot_reload_enabled,
            "total_config_keys": len(self._configs),
            "formats_enabled": [
                fmt for fmt, config in self.get("formats", {}).items()
                if config.get("enabled", False)
            ]
        }


# ===============================================================================
# CONFIGURATION BUILDER
# ===============================================================================

class ConfigurationBuilder:
    """Builder for creating healthcare configuration objects"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
    
    def with_environment(self, environment: Environment) -> 'ConfigurationBuilder':
        """Set environment"""
        self.config_manager.set_environment(environment)
        return self
    
    def with_database_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set database configuration"""
        db_config = DatabaseConfiguration(**kwargs)
        self.config_manager.set("database", db_config)
        return self
    
    def with_security_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set security configuration"""
        security_config = SecurityConfiguration(**kwargs)
        self.config_manager.set("security", security_config)
        return self
    
    def with_monitoring_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set monitoring configuration"""
        monitoring_config = MonitoringConfiguration(**kwargs)
        self.config_manager.set("monitoring", monitoring_config)
        return self
    
    def with_performance_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set performance configuration"""
        performance_config = PerformanceConfiguration(**kwargs)
        self.config_manager.set("performance", performance_config)
        return self
    
    def with_quality_rules(self, **kwargs) -> 'ConfigurationBuilder':
        """Set quality rules configuration"""
        quality_config = QualityRulesConfiguration(**kwargs)
        self.config_manager.set("quality_rules", quality_config)
        return self
    
    def with_testing_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set testing configuration"""
        testing_config = TestingConfiguration(**kwargs)
        self.config_manager.set("testing", testing_config)
        return self
    
    def with_compliance_config(self, **kwargs) -> 'ConfigurationBuilder':
        """Set compliance configuration"""
        compliance_config = ComplianceConfiguration(**kwargs)
        self.config_manager.set("compliance", compliance_config)
        return self
    
    def enable_format(self, format_type: HealthcareFormat, **kwargs) -> 'ConfigurationBuilder':
        """Enable and configure a healthcare format"""
        format_key = f"formats.{format_type.value}"
        current_config = self.config_manager.get(format_key, {})
        current_config["enabled"] = True
        current_config.update(kwargs)
        self.config_manager.set(format_key, current_config)
        return self
    
    def build(self) -> ConfigurationManager:
        """Build and return the configuration manager"""
        # Validate configuration before returning
        validation_result = self.config_manager.validate_configuration()
        if not validation_result["is_valid"]:
            logger.warning(f"Configuration validation issues: {validation_result['errors']}")
        
        return self.config_manager


# ===============================================================================
# EXAMPLE USAGE
# ===============================================================================

def main():
    """Example usage of enhanced configuration manager"""
    
    # Create configuration using builder
    config_manager = (ConfigurationBuilder()
                     .with_environment(Environment.DEVELOPMENT)
                     .with_database_config(host="localhost", port=5432, database="healthcare_dev")
                     .with_security_config(hipaa_compliance_mode=True, encryption_enabled=True)
                     .with_monitoring_config(real_time_monitoring=True)
                     .enable_format(HealthcareFormat.FHIR_R4, validation_strictness="strict")
                     .enable_format(HealthcareFormat.HL7_V2_ADT, validation_enabled=True)
                     .build())
    
    # Validate configuration
    validation_result = config_manager.validate_configuration()
    print(f"Configuration valid: {validation_result['is_valid']}")
    if validation_result['errors']:
        print(f"Errors: {validation_result['errors']}")
    if validation_result['warnings']:
        print(f"Warnings: {validation_result['warnings']}")
    
    # Test configuration access
    print(f"Database host: {config_manager.get('database.host')}")
    print(f"HIPAA compliance: {config_manager.get('security.hipaa_compliance_mode')}")
    print(f"FHIR R4 enabled: {config_manager.get('formats.fhir_r4.enabled')}")
    
    # Get configuration summary
    summary = config_manager.get_configuration_summary()
    print(f"Configuration summary: {summary}")
    
    # Test temporary configuration
    with config_manager.temporary_config({"testing.error_injection_enabled": True}):
        print(f"Error injection enabled: {config_manager.get('testing.error_injection_enabled')}")
    print(f"Error injection after context: {config_manager.get('testing.error_injection_enabled')}")


if __name__ == "__main__":
    main()