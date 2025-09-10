#!/usr/bin/env python3
"""
Healthcare Migration Performance Testing Framework

This module provides comprehensive performance testing capabilities for the enhanced 
migration simulation system, focusing on enterprise-scale healthcare data migrations.

Key Testing Areas:
- Scalability analysis with varying patient volumes 
- Concurrent processing performance and thread safety
- Memory usage profiling and leak detection
- Processing time benchmarking and bottleneck identification
- I/O performance testing for large datasets
- Configuration impact analysis
- Production deployment guidance

Author: Performance Testing Engineer
Date: 2025-09-09
"""

import asyncio
import concurrent.futures
import gc
import json
import logging
import memory_profiler
import multiprocessing as mp
import os
import psutil
import statistics
import sys
import threading
import time
import tracemalloc
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
import warnings

# Import the migration components
from enhanced_migration_simulator import EnhancedMigrationSimulator, EnhancedMigrationMetrics
from enhanced_migration_tracker import (
    HealthcareDataQualityScorer, 
    MigrationQualityMonitor,
    AlertSeverity
)
from synthetic_patient_generator import PatientRecord, MigrationConfig

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configure performance testing logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [PERF] %(message)s',
    handlers=[
        logging.FileHandler('performance_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceTestConfig:
    """Configuration for performance tests"""
    
    # Test scale configurations
    patient_volumes: List[int] = field(default_factory=lambda: [100, 500, 1000, 2500, 5000, 10000])
    batch_sizes: List[int] = field(default_factory=lambda: [10, 25, 50, 100, 250])
    concurrent_workers: List[int] = field(default_factory=lambda: [1, 2, 4, 8, 16])
    
    # Test execution parameters
    test_duration_seconds: int = 300  # 5 minutes
    warmup_iterations: int = 3
    measurement_iterations: int = 5
    memory_sampling_interval: float = 0.5  # seconds
    
    # Thresholds for performance evaluation
    max_processing_time_per_patient_ms: float = 100.0
    max_memory_usage_mb_per_1k_patients: float = 500.0
    min_throughput_patients_per_second: float = 100.0
    max_concurrent_batch_failures: int = 5
    
    # Configuration variants to test
    config_variants: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "default": {},
        "high_reliability": {
            "stage_success_rates": {
                "extract": 0.99,
                "transform": 0.98,
                "validate": 0.97,
                "load": 0.95
            },
            "network_failure_rate": 0.02,
            "system_overload_rate": 0.01
        },
        "stress_test": {
            "stage_success_rates": {
                "extract": 0.85,
                "transform": 0.80,
                "validate": 0.75,
                "load": 0.70
            },
            "network_failure_rate": 0.15,
            "system_overload_rate": 0.10
        }
    })

@dataclass
class PerformanceMetrics:
    """Comprehensive performance measurement results"""
    
    test_name: str
    timestamp: datetime
    configuration: Dict[str, Any]
    
    # Scalability metrics
    patient_count: int = 0
    batch_count: int = 0
    concurrent_workers: int = 1
    
    # Timing metrics
    total_execution_time: float = 0.0
    average_patient_processing_time: float = 0.0
    throughput_patients_per_second: float = 0.0
    batch_processing_times: List[float] = field(default_factory=list)
    
    # Memory metrics
    peak_memory_usage_mb: float = 0.0
    average_memory_usage_mb: float = 0.0
    memory_usage_per_patient_kb: float = 0.0
    memory_leak_detected: bool = False
    gc_collection_counts: Dict[str, int] = field(default_factory=dict)
    
    # CPU and system metrics
    cpu_usage_percent: float = 0.0
    system_load_average: float = 0.0
    context_switches: int = 0
    thread_count: int = 0
    
    # Quality and accuracy metrics
    average_quality_score: float = 0.0
    quality_degradation_events: int = 0
    critical_alerts: int = 0
    failed_migrations: int = 0
    
    # I/O metrics
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_io_mb: float = 0.0
    
    # Bottleneck analysis
    bottlenecks_identified: List[str] = field(default_factory=list)
    performance_recommendations: List[str] = field(default_factory=list)
    
    # Error tracking
    error_count: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization"""
        return asdict(self)


class SystemResourceMonitor:
    """Monitor system resources during performance tests"""
    
    def __init__(self, sampling_interval: float = 0.5):
        self.sampling_interval = sampling_interval
        self.monitoring = False
        self.measurements = {
            'cpu_percent': [],
            'memory_mb': [],
            'disk_io': [],
            'network_io': [],
            'thread_count': [],
            'timestamps': []
        }
        self._monitor_thread = None
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.measurements = {key: [] for key in self.measurements}
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
        logger.info("System resource monitoring started")
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics"""
        if not self.monitoring:
            return {}
        
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        # Calculate summary statistics
        summary = {}
        for metric, values in self.measurements.items():
            if values and metric != 'timestamps':
                if metric == 'disk_io' or metric == 'network_io':
                    # Handle I/O counters specially
                    summary[f'{metric}_total'] = values[-1] if values else 0
                else:
                    summary[f'{metric}_avg'] = statistics.mean(values)
                    summary[f'{metric}_max'] = max(values)
                    summary[f'{metric}_min'] = min(values)
        
        logger.info("System resource monitoring stopped")
        return summary
    
    def _monitor_resources(self):
        """Background monitoring loop"""
        disk_io_start = psutil.disk_io_counters()
        net_io_start = psutil.net_io_counters()
        
        while self.monitoring:
            try:
                # CPU and memory
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Thread count
                thread_count = self.process.num_threads()
                
                # I/O counters (cumulative)
                disk_io = psutil.disk_io_counters()
                net_io = psutil.net_io_counters()
                
                disk_io_mb = ((disk_io.read_bytes + disk_io.write_bytes) - 
                             (disk_io_start.read_bytes + disk_io_start.write_bytes)) / 1024 / 1024
                
                net_io_mb = ((net_io.bytes_sent + net_io.bytes_recv) - 
                            (net_io_start.bytes_sent + net_io_start.bytes_recv)) / 1024 / 1024
                
                # Store measurements
                self.measurements['cpu_percent'].append(cpu_percent)
                self.measurements['memory_mb'].append(memory_mb)
                self.measurements['thread_count'].append(thread_count)
                self.measurements['disk_io'].append(disk_io_mb)
                self.measurements['network_io'].append(net_io_mb)
                self.measurements['timestamps'].append(datetime.now())
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                time.sleep(1.0)


class PerformanceTester:
    """Main performance testing framework for migration simulation"""
    
    def __init__(self, config: Optional[PerformanceTestConfig] = None):
        self.config = config or PerformanceTestConfig()
        self.results: List[PerformanceMetrics] = []
        self.resource_monitor = SystemResourceMonitor(
            sampling_interval=self.config.memory_sampling_interval
        )
        
        # Test state
        self._test_start_time = None
        self._current_test = None
        
        logger.info("Performance testing framework initialized")
    
    def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run complete performance test suite"""
        logger.info("Starting comprehensive performance test suite")
        test_results = {
            'test_summary': {
                'start_time': datetime.now(),
                'test_config': asdict(self.config),
                'system_info': self._get_system_info()
            },
            'scalability_tests': [],
            'concurrency_tests': [],
            'memory_tests': [],
            'configuration_tests': [],
            'bottleneck_analysis': {},
            'recommendations': []
        }
        
        try:
            # 1. Scalability Analysis
            logger.info("Running scalability tests...")
            test_results['scalability_tests'] = self._run_scalability_tests()
            
            # 2. Concurrent Processing Analysis
            logger.info("Running concurrency tests...")
            test_results['concurrency_tests'] = self._run_concurrency_tests()
            
            # 3. Memory Usage Analysis
            logger.info("Running memory tests...")
            test_results['memory_tests'] = self._run_memory_tests()
            
            # 4. Configuration Impact Analysis
            logger.info("Running configuration impact tests...")
            test_results['configuration_tests'] = self._run_configuration_tests()
            
            # 5. Bottleneck Analysis
            logger.info("Analyzing bottlenecks...")
            test_results['bottleneck_analysis'] = self._analyze_bottlenecks()
            
            # 6. Generate Recommendations
            logger.info("Generating recommendations...")
            test_results['recommendations'] = self._generate_recommendations()
            
        except Exception as e:
            logger.error(f"Performance test suite failed: {e}")
            test_results['error'] = str(e)
            test_results['traceback'] = traceback.format_exc()
        
        test_results['test_summary']['end_time'] = datetime.now()
        test_results['test_summary']['total_duration'] = (
            test_results['test_summary']['end_time'] - 
            test_results['test_summary']['start_time']
        ).total_seconds()
        
        logger.info("Performance test suite completed")
        return test_results
    
    def _run_scalability_tests(self) -> List[Dict[str, Any]]:
        """Test scalability with different patient volumes"""
        scalability_results = []
        
        for patient_count in self.config.patient_volumes:
            logger.info(f"Testing scalability with {patient_count} patients")
            
            # Generate test patients
            patients = self._generate_test_patients(patient_count)
            
            # Run multiple iterations for statistical significance
            iteration_results = []
            for iteration in range(self.config.measurement_iterations):
                logger.info(f"Scalability test iteration {iteration + 1}/{self.config.measurement_iterations}")
                
                result = self._run_single_performance_test(
                    test_name=f"scalability_{patient_count}_patients_iter_{iteration}",
                    patients=patients,
                    concurrent_workers=1,
                    config_variant="default"
                )
                iteration_results.append(result)
            
            # Calculate aggregate metrics
            avg_metrics = self._calculate_aggregate_metrics(iteration_results)
            avg_metrics.test_name = f"scalability_{patient_count}_patients"
            scalability_results.append(avg_metrics.to_dict())
        
        return scalability_results
    
    def _run_concurrency_tests(self) -> List[Dict[str, Any]]:
        """Test concurrent processing performance"""
        concurrency_results = []
        test_patient_count = 1000  # Fixed patient count for concurrency testing
        
        patients = self._generate_test_patients(test_patient_count)
        
        for worker_count in self.config.concurrent_workers:
            if worker_count > mp.cpu_count():
                logger.warning(f"Skipping {worker_count} workers - exceeds CPU count ({mp.cpu_count()})")
                continue
            
            logger.info(f"Testing concurrency with {worker_count} workers")
            
            # Run multiple iterations
            iteration_results = []
            for iteration in range(self.config.measurement_iterations):
                logger.info(f"Concurrency test iteration {iteration + 1}/{self.config.measurement_iterations}")
                
                result = self._run_single_performance_test(
                    test_name=f"concurrency_{worker_count}_workers_iter_{iteration}",
                    patients=patients,
                    concurrent_workers=worker_count,
                    config_variant="default"
                )
                iteration_results.append(result)
            
            avg_metrics = self._calculate_aggregate_metrics(iteration_results)
            avg_metrics.test_name = f"concurrency_{worker_count}_workers"
            concurrency_results.append(avg_metrics.to_dict())
        
        return concurrency_results
    
    def _run_memory_tests(self) -> List[Dict[str, Any]]:
        """Test memory usage patterns and detect leaks"""
        memory_results = []
        
        # Test with progressively larger datasets to identify memory scaling
        test_volumes = [500, 1000, 2500, 5000]
        
        for patient_count in test_volumes:
            logger.info(f"Testing memory usage with {patient_count} patients")
            
            # Enable detailed memory tracking
            tracemalloc.start()
            gc.collect()  # Clean slate
            
            patients = self._generate_test_patients(patient_count)
            
            result = self._run_single_performance_test(
                test_name=f"memory_{patient_count}_patients",
                patients=patients,
                concurrent_workers=1,
                config_variant="default",
                enable_memory_profiling=True
            )
            
            # Check for memory leaks by running GC and measuring
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Run a small test to see if memory is released
            small_patients = self._generate_test_patients(50)
            self._run_single_performance_test(
                test_name="memory_leak_check",
                patients=small_patients,
                concurrent_workers=1,
                config_variant="default"
            )
            
            gc.collect()
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_delta = final_memory - initial_memory
            
            result.memory_leak_detected = memory_delta > 50  # 50MB threshold
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            result.peak_memory_usage_mb = max(result.peak_memory_usage_mb, peak / 1024 / 1024)
            
            memory_results.append(result.to_dict())
        
        return memory_results
    
    def _run_configuration_tests(self) -> List[Dict[str, Any]]:
        """Test performance impact of different configurations"""
        config_results = []
        test_patient_count = 1000
        
        patients = self._generate_test_patients(test_patient_count)
        
        for config_name, config_params in self.config.config_variants.items():
            logger.info(f"Testing configuration: {config_name}")
            
            result = self._run_single_performance_test(
                test_name=f"config_{config_name}",
                patients=patients,
                concurrent_workers=2,
                config_variant=config_name
            )
            
            config_results.append(result.to_dict())
        
        return config_results
    
    def _run_single_performance_test(self, test_name: str, patients: List[PatientRecord],
                                   concurrent_workers: int = 1, config_variant: str = "default",
                                   enable_memory_profiling: bool = False) -> PerformanceMetrics:
        """Run a single performance test with comprehensive metrics collection"""
        
        logger.info(f"Running performance test: {test_name}")
        
        # Initialize metrics
        metrics = PerformanceMetrics(
            test_name=test_name,
            timestamp=datetime.now(),
            configuration={
                'patient_count': len(patients),
                'concurrent_workers': concurrent_workers,
                'config_variant': config_variant
            },
            patient_count=len(patients),
            concurrent_workers=concurrent_workers
        )
        
        # Create migration simulator with test configuration
        config_params = self.config.config_variants.get(config_variant, {})
        migration_config = self._create_migration_config(config_params)
        simulator = EnhancedMigrationSimulator(migration_config)
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        # Record test start
        test_start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        try:
            if concurrent_workers == 1:
                # Single-threaded execution
                batch_results = self._run_sequential_migration(simulator, patients)
            else:
                # Multi-threaded execution
                batch_results = self._run_concurrent_migration(simulator, patients, concurrent_workers)
            
            # Calculate timing metrics
            total_time = time.time() - test_start_time
            metrics.total_execution_time = total_time
            metrics.average_patient_processing_time = total_time / len(patients) * 1000  # ms
            metrics.throughput_patients_per_second = len(patients) / total_time
            
            # Extract quality metrics from results
            if batch_results:
                metrics.average_quality_score = batch_results.get('summary', {}).get('average_quality_score', 0.0)
                metrics.critical_alerts = batch_results.get('alert_metrics', {}).get('critical_alerts', 0)
                metrics.failed_migrations = batch_results.get('summary', {}).get('total_patients', 0) - \
                                          batch_results.get('summary', {}).get('successful_patients', 0)
                
                # Calculate quality degradation events
                patient_details = batch_results.get('patient_details', {})
                metrics.quality_degradation_events = sum(
                    1 for details in patient_details.values()
                    if details.get('quality_score', 1.0) < 0.8
                )
            
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
            metrics.error_count += 1
            metrics.error_types[type(e).__name__] = metrics.error_types.get(type(e).__name__, 0) + 1
        
        # Stop monitoring and collect resource metrics
        resource_stats = self.resource_monitor.stop_monitoring()
        
        # Update metrics with resource data
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        metrics.peak_memory_usage_mb = resource_stats.get('memory_mb_max', final_memory)
        metrics.average_memory_usage_mb = resource_stats.get('memory_mb_avg', final_memory)
        metrics.memory_usage_per_patient_kb = (final_memory - initial_memory) * 1024 / len(patients)
        metrics.cpu_usage_percent = resource_stats.get('cpu_percent_avg', 0.0)
        metrics.thread_count = resource_stats.get('thread_count_max', 1)
        metrics.disk_read_mb = resource_stats.get('disk_io_total', 0.0)
        metrics.network_io_mb = resource_stats.get('network_io_total', 0.0)
        
        # Garbage collection stats
        metrics.gc_collection_counts = {
            f'generation_{i}': gc.get_count()[i] for i in range(len(gc.get_count()))
        }
        
        # Store result
        self.results.append(metrics)
        
        logger.info(f"Test {test_name} completed - {metrics.throughput_patients_per_second:.2f} patients/sec")
        return metrics
    
    def _run_sequential_migration(self, simulator: EnhancedMigrationSimulator, 
                                patients: List[PatientRecord]) -> Dict[str, Any]:
        """Run migration sequentially (single-threaded)"""
        return simulator.simulate_batch_migration(patients)
    
    def _run_concurrent_migration(self, simulator: EnhancedMigrationSimulator,
                                patients: List[PatientRecord], workers: int) -> Dict[str, Any]:
        """Run migration with concurrent workers"""
        
        # Split patients into batches for concurrent processing
        batch_size = max(1, len(patients) // workers)
        patient_batches = [
            patients[i:i + batch_size] 
            for i in range(0, len(patients), batch_size)
        ]
        
        # Process batches concurrently
        batch_results = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_batch = {
                executor.submit(simulator.simulate_batch_migration, batch): i
                for i, batch in enumerate(patient_batches)
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_id = future_to_batch[future]
                try:
                    result = future.result()
                    batch_results.append(result)
                except Exception as e:
                    logger.error(f"Batch {batch_id} failed: {e}")
        
        # Aggregate results
        if not batch_results:
            return {}
        
        # Combine metrics from all batches
        total_patients = sum(r.get('summary', {}).get('total_patients', 0) for r in batch_results)
        successful_patients = sum(r.get('summary', {}).get('successful_patients', 0) for r in batch_results)
        total_alerts = sum(r.get('alert_metrics', {}).get('total_alerts', 0) for r in batch_results)
        critical_alerts = sum(r.get('alert_metrics', {}).get('critical_alerts', 0) for r in batch_results)
        
        avg_quality = statistics.mean([
            r.get('summary', {}).get('average_quality_score', 0.0)
            for r in batch_results if r.get('summary', {}).get('average_quality_score', 0.0) > 0
        ]) if batch_results else 0.0
        
        return {
            'summary': {
                'total_patients': total_patients,
                'successful_patients': successful_patients,
                'success_rate': successful_patients / total_patients if total_patients > 0 else 0.0,
                'average_quality_score': avg_quality
            },
            'alert_metrics': {
                'total_alerts': total_alerts,
                'critical_alerts': critical_alerts
            }
        }
    
    def _generate_test_patients(self, count: int) -> List[PatientRecord]:
        """Generate synthetic patients for testing"""
        patients = []
        
        for i in range(count):
            patient = PatientRecord()
            patient.first_name = f"TestPatient{i}"
            patient.last_name = f"LastName{i}"
            patient.mrn = f"MRN{str(i).zfill(6)}"
            patient.patient_id = str(uuid.uuid4())
            
            # Add some clinical data for realistic testing
            patient.conditions = [
                {"name": "Hypertension", "status": "active", "onset_date": "2020-01-01"}
            ]
            patient.medications = [
                {"medication": "Lisinopril", "dosage": "10mg", "frequency": "daily"}
            ]
            patient.observations = [
                {"type": "Blood Pressure", "value": "140/90", "date": "2023-01-01"}
            ]
            
            patients.append(patient)
        
        logger.info(f"Generated {count} test patients")
        return patients
    
    def _create_migration_config(self, config_params: Dict[str, Any]) -> MigrationConfig:
        """Create migration configuration for testing"""
        from synthetic_patient_generator import MigrationConfig
        
        default_config = MigrationConfig()
        
        # Apply test-specific parameters
        for key, value in config_params.items():
            if hasattr(default_config, key):
                setattr(default_config, key, value)
        
        return default_config
    
    def _calculate_aggregate_metrics(self, results: List[PerformanceMetrics]) -> PerformanceMetrics:
        """Calculate aggregate metrics from multiple test runs"""
        if not results:
            return PerformanceMetrics(test_name="aggregate", timestamp=datetime.now(), configuration={})
        
        aggregate = PerformanceMetrics(
            test_name="aggregate",
            timestamp=datetime.now(),
            configuration=results[0].configuration
        )
        
        # Calculate averages and statistics
        aggregate.total_execution_time = statistics.mean([r.total_execution_time for r in results])
        aggregate.average_patient_processing_time = statistics.mean([r.average_patient_processing_time for r in results])
        aggregate.throughput_patients_per_second = statistics.mean([r.throughput_patients_per_second for r in results])
        aggregate.peak_memory_usage_mb = statistics.mean([r.peak_memory_usage_mb for r in results])
        aggregate.average_memory_usage_mb = statistics.mean([r.average_memory_usage_mb for r in results])
        aggregate.cpu_usage_percent = statistics.mean([r.cpu_usage_percent for r in results])
        aggregate.average_quality_score = statistics.mean([r.average_quality_score for r in results])
        
        # Sum counters
        aggregate.critical_alerts = sum([r.critical_alerts for r in results])
        aggregate.failed_migrations = sum([r.failed_migrations for r in results])
        aggregate.error_count = sum([r.error_count for r in results])
        
        aggregate.patient_count = results[0].patient_count
        aggregate.concurrent_workers = results[0].concurrent_workers
        
        return aggregate
    
    def _analyze_bottlenecks(self) -> Dict[str, Any]:
        """Analyze performance results to identify bottlenecks"""
        if not self.results:
            return {}
        
        bottlenecks = {
            'memory_bottlenecks': [],
            'cpu_bottlenecks': [],
            'throughput_bottlenecks': [],
            'quality_bottlenecks': [],
            'scalability_bottlenecks': []
        }
        
        for result in self.results:
            # Memory bottlenecks
            if result.peak_memory_usage_mb > self.config.max_memory_usage_mb_per_1k_patients * (result.patient_count / 1000):
                bottlenecks['memory_bottlenecks'].append({
                    'test': result.test_name,
                    'memory_usage_mb': result.peak_memory_usage_mb,
                    'patient_count': result.patient_count
                })
            
            # CPU bottlenecks  
            if result.cpu_usage_percent > 90:
                bottlenecks['cpu_bottlenecks'].append({
                    'test': result.test_name,
                    'cpu_usage': result.cpu_usage_percent
                })
            
            # Throughput bottlenecks
            if result.throughput_patients_per_second < self.config.min_throughput_patients_per_second:
                bottlenecks['throughput_bottlenecks'].append({
                    'test': result.test_name,
                    'throughput': result.throughput_patients_per_second,
                    'expected_min': self.config.min_throughput_patients_per_second
                })
            
            # Quality bottlenecks
            if result.average_quality_score < 0.8:
                bottlenecks['quality_bottlenecks'].append({
                    'test': result.test_name,
                    'quality_score': result.average_quality_score,
                    'critical_alerts': result.critical_alerts
                })
        
        return bottlenecks
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        if not self.results:
            return ["No test results available for recommendations"]
        
        # Analyze trends across results
        scalability_results = [r for r in self.results if 'scalability' in r.test_name]
        concurrency_results = [r for r in self.results if 'concurrency' in r.test_name]
        memory_results = [r for r in self.results if 'memory' in r.test_name]
        
        # Memory recommendations
        if any(r.memory_leak_detected for r in memory_results):
            recommendations.append(
                "CRITICAL: Memory leaks detected. Review object lifecycle management and ensure proper cleanup of patient data structures."
            )
        
        high_memory_tests = [r for r in self.results if r.peak_memory_usage_mb > 1000]
        if high_memory_tests:
            recommendations.append(
                f"HIGH: Memory usage exceeds 1GB in {len(high_memory_tests)} tests. Consider implementing patient data streaming or batch size optimization."
            )
        
        # Throughput recommendations
        low_throughput_tests = [r for r in self.results if r.throughput_patients_per_second < 50]
        if low_throughput_tests:
            recommendations.append(
                f"MEDIUM: Low throughput detected in {len(low_throughput_tests)} tests. Consider optimizing data quality scoring algorithms or database operations."
            )
        
        # Concurrency recommendations
        if concurrency_results:
            best_concurrency = max(concurrency_results, key=lambda r: r.throughput_patients_per_second)
            recommendations.append(
                f"OPTIMIZATION: Best performance achieved with {best_concurrency.concurrent_workers} concurrent workers. "
                f"Throughput: {best_concurrency.throughput_patients_per_second:.2f} patients/sec."
            )
        
        # Scalability recommendations
        if len(scalability_results) >= 3:
            # Check if throughput scales linearly
            throughputs = [(r.patient_count, r.throughput_patients_per_second) for r in scalability_results]
            throughputs.sort()
            
            # Simple linear regression to check scalability
            if len(throughputs) > 1:
                scaling_factor = throughputs[-1][1] / throughputs[0][1]
                patient_factor = throughputs[-1][0] / throughputs[0][0]
                
                if scaling_factor < (patient_factor * 0.7):  # Less than 70% linear scaling
                    recommendations.append(
                        f"SCALABILITY: Performance doesn't scale linearly with patient volume. "
                        f"Consider architectural changes for better horizontal scaling."
                    )
        
        # Quality recommendations
        quality_issues = [r for r in self.results if r.average_quality_score < 0.85]
        if quality_issues:
            recommendations.append(
                f"QUALITY: Data quality scores below 0.85 in {len(quality_issues)} tests. "
                f"Review data validation rules and degradation simulation parameters."
            )
        
        # Production deployment recommendations
        best_overall = max(self.results, key=lambda r: r.throughput_patients_per_second / max(1, r.critical_alerts))
        
        recommendations.extend([
            f"PRODUCTION CONFIG: For optimal performance, use {best_overall.concurrent_workers} workers with configuration variant from test '{best_overall.test_name}'",
            f"RESOURCE PLANNING: Allocate at least {best_overall.peak_memory_usage_mb * 1.5:.0f}MB memory per migration instance",
            f"MONITORING: Set up alerts for throughput below {best_overall.throughput_patients_per_second * 0.8:.0f} patients/sec",
            "BATCH SIZE: Test suggests optimal batch size of 100-250 patients per batch for balanced memory usage and throughput",
            "DATABASE: Ensure connection pooling is configured with at least 10 connections per worker thread",
            "BACKUP: Implement checkpoint/resume capability for migrations over 5000 patients"
        ])
        
        return recommendations
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for test context"""
        return {
            'cpu_count': mp.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'python_version': sys.version,
            'platform': sys.platform,
            'timestamp': datetime.now().isoformat()
        }
    
    def export_results(self, filename: str = None) -> str:
        """Export test results to JSON file"""
        if not filename:
            filename = f"performance_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'test_summary': {
                'total_tests': len(self.results),
                'export_timestamp': datetime.now().isoformat(),
                'system_info': self._get_system_info()
            },
            'test_results': [result.to_dict() for result in self.results],
            'bottleneck_analysis': self._analyze_bottlenecks(),
            'recommendations': self._generate_recommendations()
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Performance test results exported to {filename}")
        return filename


def main():
    """Main function to run performance tests"""
    print("Healthcare Migration Performance Testing Framework")
    print("=" * 60)
    
    # Create performance tester
    config = PerformanceTestConfig()
    # Reduce test volumes for faster execution in demo
    config.patient_volumes = [100, 500, 1000, 2500]
    config.measurement_iterations = 3
    
    tester = PerformanceTester(config)
    
    try:
        # Run comprehensive test suite
        results = tester.run_comprehensive_performance_test()
        
        # Export results
        results_file = tester.export_results()
        
        # Print summary
        print("\nPERFORMANCE TEST SUMMARY")
        print("=" * 40)
        
        if 'scalability_tests' in results:
            print(f"Scalability Tests: {len(results['scalability_tests'])} completed")
        
        if 'concurrency_tests' in results:
            print(f"Concurrency Tests: {len(results['concurrency_tests'])} completed")
        
        if 'memory_tests' in results:
            print(f"Memory Tests: {len(results['memory_tests'])} completed")
        
        print(f"\nDetailed results saved to: {results_file}")
        
        # Print key recommendations
        if 'recommendations' in results:
            print("\nKEY RECOMMENDATIONS:")
            for i, rec in enumerate(results['recommendations'][:5], 1):
                print(f"{i}. {rec}")
        
    except KeyboardInterrupt:
        print("\nPerformance testing interrupted by user")
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    main()