#!/usr/bin/env python3
"""
Error Injection and Testing Framework for Healthcare Data Generation

This module provides comprehensive error injection and testing capabilities for 
healthcare data generation and migration systems. It enables controlled simulation
of various error conditions, system failures, and data quality issues to ensure
robust system behavior and proper error handling.

Key Features:
- Configurable error injection across multiple failure modes
- Healthcare-specific error scenarios and edge cases
- Migration simulation with realistic failure patterns
- Performance testing under adverse conditions
- Data quality degradation simulation
- Network and system failure simulation
- End-to-end testing orchestration
- Test scenario management and execution
- Comprehensive test reporting and analytics

Error Injection Categories:
- Data corruption and format errors
- Network timeouts and connectivity issues
- System overload and resource exhaustion
- Security violations and access control failures
- Terminology mapping failures
- Validation errors and constraint violations
- Clinical business rule violations
- Compliance and regulatory violations

Author: Healthcare Systems Architect
Date: 2025-09-10
Version: 5.0.0
"""

import json
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
import threading
import concurrent.futures
from pathlib import Path
import copy

# Import core components
from ..generators.multi_format_healthcare_generator import (
    MultiFormatHealthcareGenerator, HealthcareFormat, GenerationStage,
    DataQualityDimension, UnifiedConfiguration
)
from ..config.enhanced_configuration_manager import ConfigurationManager, TestingConfiguration
from ..validation.comprehensive_validation_framework import (
    ValidationOrchestrator, ValidationLevel, ValidationScope,
    ComprehensiveValidationResult, ValidationIssue, ValidationSeverity
)

# Configure logging
logger = logging.getLogger(__name__)

# ===============================================================================
# ERROR INJECTION ENUMS AND CONSTANTS
# ===============================================================================

class ErrorInjectionMode(Enum):
    """Error injection modes"""
    DISABLED = "disabled"
    CONTROLLED = "controlled"    # Specific controlled errors
    RANDOM = "random"           # Random error injection
    SCENARIO_BASED = "scenario_based"  # Based on test scenarios
    STRESS_TEST = "stress_test" # Maximum error injection for stress testing

class FailureType(Enum):
    """Types of failures to inject"""
    DATA_CORRUPTION = "data_corruption"
    MISSING_FIELDS = "missing_fields"
    INVALID_FORMATS = "invalid_formats"
    NETWORK_TIMEOUT = "network_timeout"
    SYSTEM_OVERLOAD = "system_overload"
    SECURITY_VIOLATION = "security_violation"
    TERMINOLOGY_FAILURE = "terminology_failure"
    VALIDATION_FAILURE = "validation_failure"
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"

class TestScenarioType(Enum):
    """Types of test scenarios"""
    BASIC_FUNCTIONALITY = "basic_functionality"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE_STRESS = "performance_stress"
    MIGRATION_SIMULATION = "migration_simulation"
    COMPLIANCE_TESTING = "compliance_testing"
    SECURITY_TESTING = "security_testing"
    INTEGRATION_TESTING = "integration_testing"
    SCALABILITY_TESTING = "scalability_testing"

class SystemLoadLevel(Enum):
    """System load levels for testing"""
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"
    PEAK = "peak"

# ===============================================================================
# ERROR INJECTION COMPONENTS
# ===============================================================================

@dataclass
class ErrorInjectionConfig:
    """Configuration for error injection"""
    mode: ErrorInjectionMode = ErrorInjectionMode.DISABLED
    global_error_rate: float = 0.05
    
    # Error rates by type
    error_rates: Dict[FailureType, float] = field(default_factory=lambda: {
        FailureType.DATA_CORRUPTION: 0.02,
        FailureType.MISSING_FIELDS: 0.03,
        FailureType.INVALID_FORMATS: 0.01,
        FailureType.NETWORK_TIMEOUT: 0.05,
        FailureType.SYSTEM_OVERLOAD: 0.02,
        FailureType.SECURITY_VIOLATION: 0.001,
        FailureType.TERMINOLOGY_FAILURE: 0.03,
        FailureType.VALIDATION_FAILURE: 0.04,
        FailureType.BUSINESS_RULE_VIOLATION: 0.02,
        FailureType.COMPLIANCE_VIOLATION: 0.001
    })
    
    # Error injection timing
    inject_during_generation: bool = True
    inject_during_validation: bool = True
    inject_during_persistence: bool = True
    
    # Error persistence
    persist_errors: bool = False
    error_log_path: Optional[str] = None
    
    # Recovery simulation
    simulate_recovery: bool = True
    recovery_delay_seconds: float = 1.0

@dataclass
class InjectedError:
    """Represents an injected error"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    failure_type: FailureType = FailureType.DATA_CORRUPTION
    timestamp: datetime = field(default_factory=datetime.now)
    location: str = ""
    message: str = ""
    severity: str = "medium"
    
    # Context information
    patient_id: Optional[str] = None
    format_type: Optional[HealthcareFormat] = None
    stage: Optional[GenerationStage] = None
    
    # Recovery information
    recovered: bool = False
    recovery_timestamp: Optional[datetime] = None
    recovery_method: Optional[str] = None
    
    # Impact assessment
    impact_assessment: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestScenario:
    """Defines a test scenario"""
    scenario_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    scenario_type: TestScenarioType = TestScenarioType.BASIC_FUNCTIONALITY
    
    # Test parameters
    patient_count: int = 10
    target_formats: List[HealthcareFormat] = field(default_factory=list)
    system_load_level: SystemLoadLevel = SystemLoadLevel.NORMAL
    
    # Error injection configuration
    error_injection_config: ErrorInjectionConfig = field(default_factory=ErrorInjectionConfig)
    
    # Expected outcomes
    expected_success_rate: float = 0.95
    expected_quality_score: float = 0.90
    max_acceptable_errors: int = 5
    
    # Test duration and timing
    max_execution_time_minutes: int = 30
    timeout_seconds: int = 1800
    
    # Validation requirements
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    validation_scope: ValidationScope = ValidationScope.SINGLE_RECORD

@dataclass
class TestExecutionResult:
    """Result of test scenario execution"""
    scenario_id: str = ""
    test_start_time: datetime = field(default_factory=datetime.now)
    test_end_time: Optional[datetime] = None
    
    # Execution status
    status: str = "running"  # running, completed, failed, timeout
    success: bool = False
    
    # Generation results
    patients_generated: int = 0
    formats_generated: Dict[HealthcareFormat, int] = field(default_factory=dict)
    generation_time_seconds: float = 0.0
    
    # Error injection results
    errors_injected: List[InjectedError] = field(default_factory=list)
    errors_recovered: int = 0
    unhandled_errors: int = 0
    
    # Validation results
    validation_results: Dict[HealthcareFormat, ComprehensiveValidationResult] = field(default_factory=dict)
    overall_quality_score: float = 0.0
    
    # Performance metrics
    memory_usage_peak_mb: float = 0.0
    cpu_usage_average_percent: float = 0.0
    generation_rate_per_second: float = 0.0
    
    # Test assertions
    assertions_passed: int = 0
    assertions_failed: int = 0
    assertion_failures: List[str] = field(default_factory=list)
    
    @property
    def execution_time_seconds(self) -> float:
        if self.test_end_time and self.test_start_time:
            return (self.test_end_time - self.test_start_time).total_seconds()
        return 0.0
    
    @property
    def error_injection_rate(self) -> float:
        if self.patients_generated > 0:
            return len(self.errors_injected) / self.patients_generated
        return 0.0

# ===============================================================================
# ERROR INJECTION ENGINE
# ===============================================================================

class ErrorInjector:
    """Core error injection engine"""
    
    def __init__(self, config: ErrorInjectionConfig):
        self.config = config
        self.injected_errors: List[InjectedError] = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._lock = threading.RLock()
        
        # Error injection statistics
        self.injection_stats = defaultdict(int)
        self.recovery_stats = defaultdict(int)
    
    def should_inject_error(self, context: Dict[str, Any] = None) -> Tuple[bool, Optional[FailureType]]:
        """
        Determine if an error should be injected based on configuration and context.
        
        Args:
            context: Context information for error injection decision
            
        Returns:
            Tuple of (should_inject, failure_type)
        """
        
        if self.config.mode == ErrorInjectionMode.DISABLED:
            return False, None
        
        context = context or {}
        
        # Check global error rate
        if random.random() > self.config.global_error_rate:
            return False, None
        
        # Select failure type based on rates
        failure_types = list(self.config.error_rates.keys())
        failure_rates = [self.config.error_rates[ft] for ft in failure_types]
        
        # Weighted random selection
        total_rate = sum(failure_rates)
        if total_rate == 0:
            return False, None
        
        normalized_rates = [rate / total_rate for rate in failure_rates]
        selected_failure = random.choices(failure_types, weights=normalized_rates, k=1)[0]
        
        return True, selected_failure
    
    def inject_error(self, failure_type: FailureType, context: Dict[str, Any] = None) -> InjectedError:
        """
        Inject a specific type of error.
        
        Args:
            failure_type: Type of failure to inject
            context: Context information for error injection
            
        Returns:
            InjectedError object representing the injected error
        """
        
        context = context or {}
        
        injected_error = InjectedError(
            failure_type=failure_type,
            location=context.get('location', 'unknown'),
            message=self._generate_error_message(failure_type, context),
            patient_id=context.get('patient_id'),
            format_type=context.get('format_type'),
            stage=context.get('stage'),
            severity=self._determine_error_severity(failure_type)
        )
        
        # Apply the specific error injection
        error_data = self._apply_error_injection(failure_type, context)
        injected_error.impact_assessment = error_data
        
        # Record the error
        with self._lock:
            self.injected_errors.append(injected_error)
            self.injection_stats[failure_type] += 1
        
        self.logger.info(f"Injected {failure_type.value} error: {injected_error.message}")
        
        return injected_error
    
    def _generate_error_message(self, failure_type: FailureType, context: Dict[str, Any]) -> str:
        """Generate appropriate error message for failure type"""
        
        error_messages = {
            FailureType.DATA_CORRUPTION: "Data corruption detected during processing",
            FailureType.MISSING_FIELDS: f"Missing required field: {context.get('field_name', 'unknown')}",
            FailureType.INVALID_FORMATS: f"Invalid data format in field: {context.get('field_name', 'unknown')}",
            FailureType.NETWORK_TIMEOUT: "Network timeout during data transmission",
            FailureType.SYSTEM_OVERLOAD: "System overload - resource exhaustion",
            FailureType.SECURITY_VIOLATION: "Security violation - unauthorized access attempt",
            FailureType.TERMINOLOGY_FAILURE: "Terminology mapping failure",
            FailureType.VALIDATION_FAILURE: "Data validation failure",
            FailureType.BUSINESS_RULE_VIOLATION: "Business rule violation detected",
            FailureType.COMPLIANCE_VIOLATION: "Regulatory compliance violation"
        }
        
        return error_messages.get(failure_type, f"Unknown error type: {failure_type}")
    
    def _determine_error_severity(self, failure_type: FailureType) -> str:
        """Determine error severity based on failure type"""
        
        high_severity = {
            FailureType.SECURITY_VIOLATION,
            FailureType.COMPLIANCE_VIOLATION,
            FailureType.BUSINESS_RULE_VIOLATION
        }
        
        medium_severity = {
            FailureType.DATA_CORRUPTION,
            FailureType.VALIDATION_FAILURE,
            FailureType.TERMINOLOGY_FAILURE
        }
        
        if failure_type in high_severity:
            return "high"
        elif failure_type in medium_severity:
            return "medium"
        else:
            return "low"
    
    def _apply_error_injection(self, failure_type: FailureType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply specific error injection based on failure type"""
        
        error_data = {"failure_type": failure_type.value}
        
        if failure_type == FailureType.DATA_CORRUPTION:
            error_data.update(self._corrupt_data(context))
        elif failure_type == FailureType.MISSING_FIELDS:
            error_data.update(self._remove_fields(context))
        elif failure_type == FailureType.INVALID_FORMATS:
            error_data.update(self._invalidate_formats(context))
        elif failure_type == FailureType.NETWORK_TIMEOUT:
            error_data.update(self._simulate_network_timeout(context))
        elif failure_type == FailureType.SYSTEM_OVERLOAD:
            error_data.update(self._simulate_system_overload(context))
        
        return error_data
    
    def _corrupt_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate data corruption"""
        corruption_types = ["character_substitution", "truncation", "encoding_error"]
        corruption_type = random.choice(corruption_types)
        
        return {
            "corruption_type": corruption_type,
            "affected_fields": context.get("data_fields", []),
            "corruption_percentage": random.uniform(0.05, 0.20)
        }
    
    def _remove_fields(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate missing required fields"""
        data = context.get("data", {})
        required_fields = context.get("required_fields", [])
        
        if required_fields:
            fields_to_remove = random.sample(required_fields, min(2, len(required_fields)))
        else:
            # Remove random fields from data
            fields_to_remove = random.sample(list(data.keys()), min(2, len(data.keys())))
        
        return {
            "removed_fields": fields_to_remove,
            "original_field_count": len(data),
            "remaining_field_count": len(data) - len(fields_to_remove)
        }
    
    def _invalidate_formats(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate invalid data formats"""
        format_errors = ["invalid_date", "invalid_phone", "invalid_email", "invalid_ssn"]
        selected_errors = random.sample(format_errors, min(2, len(format_errors)))
        
        return {
            "format_errors": selected_errors,
            "affected_records": random.randint(1, 5)
        }
    
    def _simulate_network_timeout(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate network timeout"""
        timeout_duration = random.uniform(5.0, 30.0)
        
        # Actually delay for testing purposes
        if context.get("simulate_delay", True):
            time.sleep(min(timeout_duration / 10, 1.0))  # Reduced delay for testing
        
        return {
            "timeout_duration_seconds": timeout_duration,
            "retry_count": random.randint(1, 3),
            "connection_type": "http"
        }
    
    def _simulate_system_overload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate system overload"""
        return {
            "cpu_usage_percent": random.uniform(85, 100),
            "memory_usage_percent": random.uniform(90, 100),
            "concurrent_requests": random.randint(100, 500),
            "queue_length": random.randint(50, 200)
        }
    
    def simulate_recovery(self, error: InjectedError) -> bool:
        """
        Simulate error recovery.
        
        Args:
            error: Error to attempt recovery for
            
        Returns:
            bool: True if recovery successful, False otherwise
        """
        
        if not self.config.simulate_recovery:
            return False
        
        # Simulate recovery delay
        time.sleep(self.config.recovery_delay_seconds)
        
        # Recovery success rates by error type
        recovery_rates = {
            FailureType.NETWORK_TIMEOUT: 0.80,
            FailureType.SYSTEM_OVERLOAD: 0.70,
            FailureType.DATA_CORRUPTION: 0.30,
            FailureType.INVALID_FORMATS: 0.60,
            FailureType.MISSING_FIELDS: 0.50,
            FailureType.TERMINOLOGY_FAILURE: 0.40,
            FailureType.VALIDATION_FAILURE: 0.70,
            FailureType.SECURITY_VIOLATION: 0.10,
            FailureType.COMPLIANCE_VIOLATION: 0.20,
            FailureType.BUSINESS_RULE_VIOLATION: 0.50
        }
        
        recovery_rate = recovery_rates.get(error.failure_type, 0.50)
        recovery_successful = random.random() < recovery_rate
        
        if recovery_successful:
            error.recovered = True
            error.recovery_timestamp = datetime.now()
            error.recovery_method = self._determine_recovery_method(error.failure_type)
            
            with self._lock:
                self.recovery_stats[error.failure_type] += 1
            
            self.logger.info(f"Recovery successful for error {error.error_id}: {error.recovery_method}")
        else:
            self.logger.warning(f"Recovery failed for error {error.error_id}")
        
        return recovery_successful
    
    def _determine_recovery_method(self, failure_type: FailureType) -> str:
        """Determine appropriate recovery method for failure type"""
        
        recovery_methods = {
            FailureType.NETWORK_TIMEOUT: "retry_with_backoff",
            FailureType.SYSTEM_OVERLOAD: "load_balancing_redirect",
            FailureType.DATA_CORRUPTION: "data_restoration_from_backup",
            FailureType.INVALID_FORMATS: "automatic_format_correction",
            FailureType.MISSING_FIELDS: "default_value_substitution",
            FailureType.TERMINOLOGY_FAILURE: "alternative_terminology_mapping",
            FailureType.VALIDATION_FAILURE: "validation_rule_relaxation",
            FailureType.SECURITY_VIOLATION: "security_protocol_reset",
            FailureType.COMPLIANCE_VIOLATION: "compliance_override_with_logging",
            FailureType.BUSINESS_RULE_VIOLATION: "business_rule_exception_handling"
        }
        
        return recovery_methods.get(failure_type, "manual_intervention_required")
    
    def get_injection_statistics(self) -> Dict[str, Any]:
        """Get error injection statistics"""
        
        with self._lock:
            total_errors = len(self.injected_errors)
            recovered_errors = sum(1 for error in self.injected_errors if error.recovered)
            
            return {
                "total_errors_injected": total_errors,
                "errors_recovered": recovered_errors,
                "recovery_rate": recovered_errors / total_errors if total_errors > 0 else 0.0,
                "injection_stats_by_type": dict(self.injection_stats),
                "recovery_stats_by_type": dict(self.recovery_stats),
                "active_errors": total_errors - recovered_errors
            }

# ===============================================================================
# TEST SCENARIO MANAGER
# ===============================================================================

class TestScenarioManager:
    """Manages test scenarios and execution"""
    
    def __init__(self):
        self.scenarios: Dict[str, TestScenario] = {}
        self.execution_results: Dict[str, TestExecutionResult] = {}
        self.config_manager = ConfigurationManager()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize with predefined scenarios
        self._initialize_default_scenarios()
    
    def _initialize_default_scenarios(self):
        """Initialize with common test scenarios"""
        
        # Basic functionality test
        basic_test = TestScenario(
            name="Basic Functionality Test",
            description="Test basic data generation without error injection",
            scenario_type=TestScenarioType.BASIC_FUNCTIONALITY,
            patient_count=10,
            target_formats=[HealthcareFormat.FHIR_R4, HealthcareFormat.CSV],
            error_injection_config=ErrorInjectionConfig(mode=ErrorInjectionMode.DISABLED),
            expected_success_rate=1.0,
            expected_quality_score=0.95
        )
        self.add_scenario(basic_test)
        
        # Error handling test
        error_handling_test = TestScenario(
            name="Error Handling Test",
            description="Test system behavior under controlled error conditions",
            scenario_type=TestScenarioType.ERROR_HANDLING,
            patient_count=20,
            target_formats=[HealthcareFormat.FHIR_R4, HealthcareFormat.HL7_V2_ADT],
            error_injection_config=ErrorInjectionConfig(
                mode=ErrorInjectionMode.CONTROLLED,
                global_error_rate=0.15
            ),
            expected_success_rate=0.80,
            expected_quality_score=0.75,
            max_acceptable_errors=10
        )
        self.add_scenario(error_handling_test)
        
        # Performance stress test
        stress_test = TestScenario(
            name="Performance Stress Test",
            description="Test system performance under high load and error conditions",
            scenario_type=TestScenarioType.PERFORMANCE_STRESS,
            patient_count=100,
            target_formats=[HealthcareFormat.FHIR_R4, HealthcareFormat.HL7_V2_ADT, HealthcareFormat.CSV],
            system_load_level=SystemLoadLevel.HIGH,
            error_injection_config=ErrorInjectionConfig(
                mode=ErrorInjectionMode.STRESS_TEST,
                global_error_rate=0.25
            ),
            expected_success_rate=0.70,
            expected_quality_score=0.65,
            max_acceptable_errors=25,
            max_execution_time_minutes=15
        )
        self.add_scenario(stress_test)
        
        # Migration simulation test
        migration_test = TestScenario(
            name="Migration Simulation Test",
            description="Test healthcare data migration with realistic failure patterns",
            scenario_type=TestScenarioType.MIGRATION_SIMULATION,
            patient_count=50,
            target_formats=[HealthcareFormat.VISTA_MUMPS, HealthcareFormat.FHIR_R4],
            error_injection_config=ErrorInjectionConfig(
                mode=ErrorInjectionMode.SCENARIO_BASED,
                global_error_rate=0.10,
                error_rates={
                    FailureType.NETWORK_TIMEOUT: 0.08,
                    FailureType.TERMINOLOGY_FAILURE: 0.15,
                    FailureType.DATA_CORRUPTION: 0.05,
                    FailureType.VALIDATION_FAILURE: 0.12
                }
            ),
            expected_success_rate=0.85,
            expected_quality_score=0.80,
            validation_level=ValidationLevel.COMPREHENSIVE
        )
        self.add_scenario(migration_test)
    
    def add_scenario(self, scenario: TestScenario):
        """Add a test scenario"""
        self.scenarios[scenario.scenario_id] = scenario
        self.logger.info(f"Added test scenario: {scenario.name}")
    
    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Get test scenario by ID"""
        return self.scenarios.get(scenario_id)
    
    def list_scenarios(self) -> List[TestScenario]:
        """List all available scenarios"""
        return list(self.scenarios.values())
    
    def execute_scenario(self, scenario_id: str) -> TestExecutionResult:
        """
        Execute a specific test scenario.
        
        Args:
            scenario_id: ID of scenario to execute
            
        Returns:
            TestExecutionResult with execution details
        """
        
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")
        
        self.logger.info(f"Executing test scenario: {scenario.name}")
        
        # Initialize execution result
        result = TestExecutionResult(
            scenario_id=scenario_id,
            test_start_time=datetime.now(),
            status="running"
        )
        
        try:
            # Create error injector
            error_injector = ErrorInjector(scenario.error_injection_config)
            
            # Create test configuration
            test_config = self._create_test_configuration(scenario)
            
            # Create generator with test configuration
            generator = MultiFormatHealthcareGenerator(test_config)
            
            # Execute generation with error injection
            generation_results = self._execute_generation_with_errors(
                generator, scenario, error_injector, result
            )
            
            # Validate results
            validation_results = self._validate_generation_results(
                generation_results, scenario, result
            )
            
            # Assess test results
            self._assess_test_results(scenario, result, generation_results, validation_results)
            
            result.test_end_time = datetime.now()
            result.status = "completed"
            
            self.logger.info(f"Test scenario completed: {scenario.name}")
            
        except Exception as e:
            result.test_end_time = datetime.now()
            result.status = "failed"
            result.assertion_failures.append(f"Test execution failed: {str(e)}")
            self.logger.error(f"Test scenario failed: {scenario.name} - {e}")
        
        # Store result
        self.execution_results[scenario_id] = result
        
        return result
    
    def _create_test_configuration(self, scenario: TestScenario) -> UnifiedConfiguration:
        """Create configuration for test scenario"""
        
        # Start with default configuration
        config = UnifiedConfiguration()
        
        # Apply scenario-specific settings
        config.num_records = scenario.patient_count
        config.output_dir = f"test_output_{scenario.scenario_id}"
        
        # Configure formats
        for format_type in scenario.target_formats:
            from multi_format_healthcare_generator import FormatConfiguration
            format_config = FormatConfiguration(format_type)
            format_config.enabled = True
            config.formats[format_type] = format_config
        
        # Apply system load level adjustments
        if scenario.system_load_level == SystemLoadLevel.HIGH:
            config.migration_settings.concurrent_patients = 20
            config.migration_settings.batch_size = 100
        elif scenario.system_load_level == SystemLoadLevel.EXTREME:
            config.migration_settings.concurrent_patients = 50
            config.migration_settings.batch_size = 200
        
        return config
    
    def _execute_generation_with_errors(self, generator: MultiFormatHealthcareGenerator,
                                      scenario: TestScenario, error_injector: ErrorInjector,
                                      result: TestExecutionResult) -> Dict[str, Any]:
        """Execute data generation with error injection"""
        
        start_time = time.time()
        
        # Hook into generator to inject errors
        original_execute_pipeline = generator._execute_generation_pipeline
        
        def error_injecting_pipeline(context, results):
            # Check for error injection before each stage
            for stage in GenerationStage:
                should_inject, failure_type = error_injector.should_inject_error({
                    'stage': stage,
                    'context': context
                })
                
                if should_inject:
                    injected_error = error_injector.inject_error(failure_type, {
                        'stage': stage,
                        'location': stage.value,
                        'context': context
                    })
                    result.errors_injected.append(injected_error)
                    
                    # Attempt recovery
                    if error_injector.simulate_recovery(injected_error):
                        result.errors_recovered += 1
                    else:
                        result.unhandled_errors += 1
            
            return original_execute_pipeline(context, results)
        
        # Temporarily replace method
        generator._execute_generation_pipeline = error_injecting_pipeline
        
        try:
            # Execute generation
            generation_results = generator.generate_healthcare_data(
                target_formats=scenario.target_formats,
                patient_count=scenario.patient_count
            )
            
            # Update result metrics
            result.patients_generated = generation_results.get('generation_summary', {}).get('total_patients', 0)
            result.generation_time_seconds = time.time() - start_time
            
            if result.generation_time_seconds > 0:
                result.generation_rate_per_second = result.patients_generated / result.generation_time_seconds
            
            # Update format counts
            for format_name in generation_results.get('generation_summary', {}).get('formats_generated', []):
                try:
                    format_type = HealthcareFormat(format_name)
                    result.formats_generated[format_type] = generation_results.get('format_outputs', {}).get(format_name, 0)
                except ValueError:
                    pass
            
            return generation_results
            
        finally:
            # Restore original method
            generator._execute_generation_pipeline = original_execute_pipeline
    
    def _validate_generation_results(self, generation_results: Dict[str, Any],
                                   scenario: TestScenario, result: TestExecutionResult) -> Dict[str, Any]:
        """Validate generation results according to scenario requirements"""
        
        validation_orchestrator = ValidationOrchestrator()
        
        # Prepare format data for validation
        format_data = {}
        format_outputs = generation_results.get('format_outputs', {})
        
        for format_name, data_list in format_outputs.items():
            try:
                format_type = HealthcareFormat(format_name)
                # Take first record for validation (in real scenario, might validate all)
                if data_list:
                    format_data[format_type] = data_list[0] if isinstance(data_list, list) else data_list
            except ValueError:
                continue
        
        # Perform validation
        if format_data:
            validation_results = validation_orchestrator.validate_multi_format_data(
                format_data=format_data,
                validation_level=scenario.validation_level
            )
            
            result.validation_results = validation_results
            
            # Calculate overall quality score
            quality_scores = [vr.overall_score for vr in validation_results.values()]
            result.overall_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return result.validation_results
    
    def _assess_test_results(self, scenario: TestScenario, result: TestExecutionResult,
                           generation_results: Dict[str, Any], validation_results: Dict[str, Any]):
        """Assess test results against scenario expectations"""
        
        # Check success rate
        total_operations = result.patients_generated
        successful_operations = total_operations - result.unhandled_errors
        actual_success_rate = successful_operations / total_operations if total_operations > 0 else 0.0
        
        if actual_success_rate >= scenario.expected_success_rate:
            result.assertions_passed += 1
        else:
            result.assertions_failed += 1
            result.assertion_failures.append(
                f"Success rate below threshold: {actual_success_rate:.2f} < {scenario.expected_success_rate:.2f}"
            )
        
        # Check quality score
        if result.overall_quality_score >= scenario.expected_quality_score:
            result.assertions_passed += 1
        else:
            result.assertions_failed += 1
            result.assertion_failures.append(
                f"Quality score below threshold: {result.overall_quality_score:.2f} < {scenario.expected_quality_score:.2f}"
            )
        
        # Check error count
        if len(result.errors_injected) <= scenario.max_acceptable_errors:
            result.assertions_passed += 1
        else:
            result.assertions_failed += 1
            result.assertion_failures.append(
                f"Error count exceeds maximum: {len(result.errors_injected)} > {scenario.max_acceptable_errors}"
            )
        
        # Check execution time
        if result.execution_time_seconds <= scenario.max_execution_time_minutes * 60:
            result.assertions_passed += 1
        else:
            result.assertions_failed += 1
            result.assertion_failures.append(
                f"Execution time exceeds maximum: {result.execution_time_seconds:.1f}s > {scenario.max_execution_time_minutes * 60}s"
            )
        
        # Determine overall success
        result.success = result.assertions_failed == 0
    
    def execute_all_scenarios(self) -> Dict[str, TestExecutionResult]:
        """Execute all test scenarios"""
        
        results = {}
        
        for scenario_id, scenario in self.scenarios.items():
            self.logger.info(f"Executing scenario: {scenario.name}")
            try:
                result = self.execute_scenario(scenario_id)
                results[scenario_id] = result
            except Exception as e:
                self.logger.error(f"Failed to execute scenario {scenario_id}: {e}")
        
        return results
    
    def generate_test_report(self, scenario_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        if scenario_ids is None:
            scenario_ids = list(self.scenarios.keys())
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "scenarios_executed": len(scenario_ids),
            "overall_summary": {
                "total_scenarios": len(scenario_ids),
                "successful_scenarios": 0,
                "failed_scenarios": 0,
                "total_patients_generated": 0,
                "total_errors_injected": 0,
                "total_errors_recovered": 0,
                "average_quality_score": 0.0,
                "average_execution_time_seconds": 0.0
            },
            "scenario_results": {},
            "error_analysis": {},
            "performance_analysis": {},
            "recommendations": []
        }
        
        # Process each scenario result
        total_quality_scores = []
        total_execution_times = []
        
        for scenario_id in scenario_ids:
            result = self.execution_results.get(scenario_id)
            scenario = self.scenarios.get(scenario_id)
            
            if not result or not scenario:
                continue
            
            # Update overall summary
            if result.success:
                report["overall_summary"]["successful_scenarios"] += 1
            else:
                report["overall_summary"]["failed_scenarios"] += 1
            
            report["overall_summary"]["total_patients_generated"] += result.patients_generated
            report["overall_summary"]["total_errors_injected"] += len(result.errors_injected)
            report["overall_summary"]["total_errors_recovered"] += result.errors_recovered
            
            if result.overall_quality_score > 0:
                total_quality_scores.append(result.overall_quality_score)
            
            if result.execution_time_seconds > 0:
                total_execution_times.append(result.execution_time_seconds)
            
            # Add scenario-specific results
            report["scenario_results"][scenario_id] = {
                "scenario_name": scenario.name,
                "scenario_type": scenario.scenario_type.value,
                "success": result.success,
                "patients_generated": result.patients_generated,
                "execution_time_seconds": result.execution_time_seconds,
                "quality_score": result.overall_quality_score,
                "errors_injected": len(result.errors_injected),
                "errors_recovered": result.errors_recovered,
                "assertions_passed": result.assertions_passed,
                "assertions_failed": result.assertions_failed,
                "assertion_failures": result.assertion_failures
            }
        
        # Calculate averages
        if total_quality_scores:
            report["overall_summary"]["average_quality_score"] = sum(total_quality_scores) / len(total_quality_scores)
        
        if total_execution_times:
            report["overall_summary"]["average_execution_time_seconds"] = sum(total_execution_times) / len(total_execution_times)
        
        # Generate recommendations
        failed_scenarios = report["overall_summary"]["failed_scenarios"]
        if failed_scenarios > 0:
            report["recommendations"].append(f"Review and address {failed_scenarios} failed test scenarios")
        
        recovery_rate = (report["overall_summary"]["total_errors_recovered"] / 
                        max(report["overall_summary"]["total_errors_injected"], 1))
        
        if recovery_rate < 0.70:
            report["recommendations"].append(f"Improve error recovery mechanisms (current rate: {recovery_rate:.2f})")
        
        avg_quality = report["overall_summary"]["average_quality_score"]
        if avg_quality < 0.80:
            report["recommendations"].append(f"Address data quality issues (current average: {avg_quality:.2f})")
        
        return report


# ===============================================================================
# EXAMPLE USAGE AND DEMO
# ===============================================================================

def main():
    """Example usage of error injection and testing framework"""
    
    # Create test scenario manager
    test_manager = TestScenarioManager()
    
    print("Available Test Scenarios:")
    for scenario in test_manager.list_scenarios():
        print(f"- {scenario.name}: {scenario.description}")
        print(f"  Type: {scenario.scenario_type.value}")
        print(f"  Patients: {scenario.patient_count}")
        print(f"  Error injection: {scenario.error_injection_config.mode.value}")
        print()
    
    # Execute a specific scenario
    basic_scenarios = [s for s in test_manager.list_scenarios() 
                      if s.scenario_type == TestScenarioType.BASIC_FUNCTIONALITY]
    
    if basic_scenarios:
        scenario = basic_scenarios[0]
        print(f"Executing test scenario: {scenario.name}")
        
        result = test_manager.execute_scenario(scenario.scenario_id)
        
        print(f"Test Results:")
        print(f"- Success: {result.success}")
        print(f"- Patients generated: {result.patients_generated}")
        print(f"- Execution time: {result.execution_time_seconds:.2f} seconds")
        print(f"- Quality score: {result.overall_quality_score:.2f}")
        print(f"- Errors injected: {len(result.errors_injected)}")
        print(f"- Errors recovered: {result.errors_recovered}")
        print(f"- Assertions passed: {result.assertions_passed}")
        print(f"- Assertions failed: {result.assertions_failed}")
        
        if result.assertion_failures:
            print("Assertion Failures:")
            for failure in result.assertion_failures:
                print(f"  - {failure}")
    
    # Generate comprehensive test report
    print("\nGenerating comprehensive test report...")
    report = test_manager.generate_test_report()
    
    print(f"Test Report Summary:")
    print(f"- Scenarios executed: {report['overall_summary']['total_scenarios']}")
    print(f"- Successful scenarios: {report['overall_summary']['successful_scenarios']}")
    print(f"- Failed scenarios: {report['overall_summary']['failed_scenarios']}")
    print(f"- Average quality score: {report['overall_summary']['average_quality_score']:.2f}")
    
    if report['recommendations']:
        print("Recommendations:")
        for recommendation in report['recommendations']:
            print(f"  - {recommendation}")


if __name__ == "__main__":
    main()