#!/usr/bin/env python3
"""
Healthcare Migration Performance Test Runner

This script executes comprehensive performance tests on the migration simulation system
and generates detailed analysis reports with optimization recommendations.

Usage:
    python run_performance_tests.py [--scale SCALE] [--quick] [--memory-only] [--concurrent-only]

Author: Performance Testing Engineer  
Date: 2025-09-09
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from performance_testing_framework import PerformanceTester, PerformanceTestConfig

def setup_logging():
    """Setup logging for test execution"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(logs_dir / f"performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
            logging.StreamHandler()
        ]
    )

def run_quick_tests():
    """Run a quick subset of performance tests for rapid feedback"""
    print("Running Quick Performance Tests...")
    
    config = PerformanceTestConfig()
    # Reduced test parameters for quick execution
    config.patient_volumes = [100, 500, 1000]
    config.concurrent_workers = [1, 2, 4]
    config.measurement_iterations = 2
    config.warmup_iterations = 1
    
    tester = PerformanceTester(config)
    
    # Run only essential tests
    print("\n1. Testing basic scalability...")
    scalability_results = tester._run_scalability_tests()
    
    print("\n2. Testing concurrent processing...")
    concurrency_results = tester._run_concurrency_tests()
    
    print("\n3. Analyzing results...")
    bottlenecks = tester._analyze_bottlenecks()
    recommendations = tester._generate_recommendations()
    
    # Generate quick report
    quick_results = {
        'test_type': 'quick',
        'timestamp': datetime.now().isoformat(),
        'scalability_results': scalability_results,
        'concurrency_results': concurrency_results,
        'bottlenecks': bottlenecks,
        'recommendations': recommendations
    }
    
    return quick_results

def run_memory_focused_tests():
    """Run memory-focused performance tests"""
    print("Running Memory-Focused Performance Tests...")
    
    config = PerformanceTestConfig()
    # Focus on memory testing with larger datasets
    config.patient_volumes = [1000, 2500, 5000, 7500, 10000]
    config.measurement_iterations = 3
    
    tester = PerformanceTester(config)
    
    print("\n1. Running memory usage analysis...")
    memory_results = tester._run_memory_tests()
    
    print("\n2. Testing scalability for memory impact...")
    scalability_results = tester._run_scalability_tests()
    
    print("\n3. Analyzing memory bottlenecks...")
    bottlenecks = tester._analyze_bottlenecks()
    
    memory_focused_results = {
        'test_type': 'memory_focused',
        'timestamp': datetime.now().isoformat(),
        'memory_results': memory_results,
        'scalability_results': scalability_results,
        'bottlenecks': bottlenecks,
        'recommendations': tester._generate_recommendations()
    }
    
    return memory_focused_results

def run_concurrent_focused_tests():
    """Run concurrency-focused performance tests"""
    print("Running Concurrency-Focused Performance Tests...")
    
    config = PerformanceTestConfig()
    # Focus on concurrency testing
    config.concurrent_workers = [1, 2, 4, 6, 8, 12, 16]
    config.patient_volumes = [1000]  # Fixed patient count
    config.measurement_iterations = 4
    
    tester = PerformanceTester(config)
    
    print("\n1. Running concurrency analysis...")
    concurrency_results = tester._run_concurrency_tests()
    
    print("\n2. Testing configuration variants with concurrency...")
    config_results = tester._run_configuration_tests()
    
    print("\n3. Analyzing concurrency bottlenecks...")
    bottlenecks = tester._analyze_bottlenecks()
    
    concurrent_focused_results = {
        'test_type': 'concurrent_focused',
        'timestamp': datetime.now().isoformat(),
        'concurrency_results': concurrency_results,
        'configuration_results': config_results,
        'bottlenecks': bottlenecks,
        'recommendations': tester._generate_recommendations()
    }
    
    return concurrent_focused_results

def run_full_performance_suite(scale='medium'):
    """Run the complete performance test suite"""
    print(f"Running Full Performance Test Suite (Scale: {scale})...")
    
    # Configure test scale
    config = PerformanceTestConfig()
    
    if scale == 'small':
        config.patient_volumes = [100, 500, 1000, 2500]
        config.concurrent_workers = [1, 2, 4]
        config.measurement_iterations = 3
    elif scale == 'medium':
        config.patient_volumes = [100, 500, 1000, 2500, 5000]
        config.concurrent_workers = [1, 2, 4, 8]
        config.measurement_iterations = 3
    elif scale == 'large':
        config.patient_volumes = [100, 500, 1000, 2500, 5000, 10000, 15000]
        config.concurrent_workers = [1, 2, 4, 8, 16]
        config.measurement_iterations = 5
    elif scale == 'enterprise':
        config.patient_volumes = [1000, 2500, 5000, 10000, 25000, 50000]
        config.concurrent_workers = [1, 2, 4, 8, 16, 32]
        config.measurement_iterations = 5
        config.test_duration_seconds = 600  # 10 minutes
    
    tester = PerformanceTester(config)
    
    # Run comprehensive test suite
    results = tester.run_comprehensive_performance_test()
    
    return results

def generate_performance_report(results, output_dir="results"):
    """Generate comprehensive performance analysis report"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save raw JSON results
    json_file = output_path / f"performance_results_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate markdown report
    report_file = output_path / f"performance_report_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write("# Healthcare Migration System Performance Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Test Type:** {results.get('test_type', 'comprehensive')}\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        
        if 'test_summary' in results:
            summary = results['test_summary']
            f.write(f"- **Total Test Duration:** {summary.get('total_duration', 'N/A')} seconds\n")
            f.write(f"- **System Configuration:** {summary.get('system_info', {}).get('cpu_count', 'N/A')} CPU cores, ")
            f.write(f"{summary.get('system_info', {}).get('memory_gb', 'N/A'):.1f} GB RAM\n")
        
        # Key Findings
        f.write("\n## Key Performance Findings\n\n")
        
        # Scalability Results
        if 'scalability_results' in results or 'scalability_tests' in results:
            scalability_data = results.get('scalability_results') or results.get('scalability_tests', [])
            f.write("### Scalability Performance\n\n")
            f.write("| Patient Count | Throughput (patients/sec) | Memory Usage (MB) | Quality Score |\n")
            f.write("|---------------|---------------------------|-------------------|---------------|\n")
            
            for test in scalability_data:
                if isinstance(test, dict):
                    patient_count = test.get('configuration', {}).get('patient_count', test.get('patient_count', 'N/A'))
                    throughput = test.get('throughput_patients_per_second', 0)
                    memory = test.get('peak_memory_usage_mb', 0)
                    quality = test.get('average_quality_score', 0)
                    f.write(f"| {patient_count} | {throughput:.2f} | {memory:.1f} | {quality:.3f} |\n")
        
        # Concurrency Results
        if 'concurrency_results' in results or 'concurrency_tests' in results:
            concurrency_data = results.get('concurrency_results') or results.get('concurrency_tests', [])
            f.write("\n### Concurrency Performance\n\n")
            f.write("| Workers | Throughput (patients/sec) | CPU Usage (%) | Memory Usage (MB) |\n")
            f.write("|---------|---------------------------|---------------|-------------------|\n")
            
            for test in concurrency_data:
                if isinstance(test, dict):
                    workers = test.get('concurrent_workers', test.get('configuration', {}).get('concurrent_workers', 'N/A'))
                    throughput = test.get('throughput_patients_per_second', 0)
                    cpu = test.get('cpu_usage_percent', 0)
                    memory = test.get('peak_memory_usage_mb', 0)
                    f.write(f"| {workers} | {throughput:.2f} | {cpu:.1f} | {memory:.1f} |\n")
        
        # Memory Analysis
        if 'memory_results' in results or 'memory_tests' in results:
            memory_data = results.get('memory_results') or results.get('memory_tests', [])
            f.write("\n### Memory Usage Analysis\n\n")
            
            for test in memory_data:
                if isinstance(test, dict):
                    patient_count = test.get('patient_count', 0)
                    memory_per_patient = test.get('memory_usage_per_patient_kb', 0)
                    leak_detected = test.get('memory_leak_detected', False)
                    
                    f.write(f"- **{patient_count} patients:** {memory_per_patient:.2f} KB per patient")
                    if leak_detected:
                        f.write(" ⚠️ *Memory leak detected*")
                    f.write("\n")
        
        # Bottleneck Analysis
        bottlenecks = results.get('bottleneck_analysis', results.get('bottlenecks', {}))
        if bottlenecks:
            f.write("\n## Bottleneck Analysis\n\n")
            
            for bottleneck_type, issues in bottlenecks.items():
                if issues:
                    f.write(f"### {bottleneck_type.replace('_', ' ').title()}\n\n")
                    for issue in issues:
                        f.write(f"- **{issue.get('test', 'Unknown test')}:** ")
                        if 'memory_usage_mb' in issue:
                            f.write(f"Memory usage: {issue['memory_usage_mb']:.1f} MB")
                        elif 'cpu_usage' in issue:
                            f.write(f"CPU usage: {issue['cpu_usage']:.1f}%")
                        elif 'throughput' in issue:
                            f.write(f"Throughput: {issue['throughput']:.2f} patients/sec")
                        elif 'quality_score' in issue:
                            f.write(f"Quality score: {issue['quality_score']:.3f}")
                        f.write("\n")
                    f.write("\n")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            f.write("\n## Performance Optimization Recommendations\n\n")
            
            # Group recommendations by priority
            critical_recs = [r for r in recommendations if r.startswith('CRITICAL:')]
            high_recs = [r for r in recommendations if r.startswith('HIGH:')]
            medium_recs = [r for r in recommendations if r.startswith('MEDIUM:')]
            other_recs = [r for r in recommendations if not any(r.startswith(p) for p in ['CRITICAL:', 'HIGH:', 'MEDIUM:'])]
            
            if critical_recs:
                f.write("### 🚨 Critical Priority\n\n")
                for rec in critical_recs:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            if high_recs:
                f.write("### ⚠️ High Priority\n\n")
                for rec in high_recs:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            if medium_recs:
                f.write("### ℹ️ Medium Priority\n\n")
                for rec in medium_recs:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            if other_recs:
                f.write("### 📈 General Optimizations\n\n")
                for rec in other_recs:
                    f.write(f"- {rec}\n")
        
        # Production Deployment Guidelines
        f.write("\n## Production Deployment Guidelines\n\n")
        f.write("Based on the performance test results, here are the recommended production configurations:\n\n")
        
        # Find best performing configuration
        best_throughput = 0
        best_config = None
        
        all_results = []
        for test_type in ['scalability_results', 'scalability_tests', 'concurrency_results', 'concurrency_tests']:
            if test_type in results:
                all_results.extend(results[test_type])
        
        for result in all_results:
            if isinstance(result, dict):
                throughput = result.get('throughput_patients_per_second', 0)
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_config = result
        
        if best_config:
            f.write("### Recommended Configuration\n\n")
            f.write(f"- **Concurrent Workers:** {best_config.get('concurrent_workers', 'N/A')}\n")
            f.write(f"- **Expected Throughput:** {best_throughput:.2f} patients/sec\n")
            f.write(f"- **Memory Allocation:** {best_config.get('peak_memory_usage_mb', 0) * 1.5:.0f} MB per instance\n")
            f.write(f"- **CPU Utilization:** {best_config.get('cpu_usage_percent', 0):.1f}%\n")
        
        f.write("\n### Scaling Guidelines\n\n")
        f.write("- For migrations under 1,000 patients: Single instance sufficient\n")
        f.write("- For migrations 1,000-10,000 patients: Use 2-4 concurrent workers\n") 
        f.write("- For migrations over 10,000 patients: Consider horizontal scaling with multiple instances\n")
        f.write("- Monitor memory usage and scale vertically if exceeding 80% of available RAM\n")
        
        f.write("\n### Monitoring and Alerting\n\n")
        f.write("Set up the following monitoring thresholds in production:\n\n")
        f.write(f"- **Throughput Alert:** Below {best_throughput * 0.7:.0f} patients/sec\n")
        f.write("- **Memory Alert:** Above 80% of allocated memory\n")
        f.write("- **Quality Alert:** Average quality score below 0.85\n")
        f.write("- **Error Rate Alert:** More than 5% failed migrations\n")
        
    print(f"\n📊 Performance report generated:")
    print(f"   - JSON Results: {json_file}")
    print(f"   - Markdown Report: {report_file}")
    
    return report_file, json_file

def main():
    """Main function for performance test runner"""
    parser = argparse.ArgumentParser(description="Healthcare Migration Performance Test Runner")
    parser.add_argument('--scale', choices=['small', 'medium', 'large', 'enterprise'], 
                       default='medium', help='Test scale (default: medium)')
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick tests for rapid feedback')
    parser.add_argument('--memory-only', action='store_true', 
                       help='Run memory-focused tests only')
    parser.add_argument('--concurrent-only', action='store_true', 
                       help='Run concurrency-focused tests only')
    parser.add_argument('--output-dir', default='results', 
                       help='Output directory for results (default: results)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    print("🏥 Healthcare Migration Performance Testing Suite")
    print("=" * 60)
    
    start_time = time.time()
    results = None
    
    try:
        if args.quick:
            results = run_quick_tests()
        elif args.memory_only:
            results = run_memory_focused_tests()
        elif args.concurrent_only:
            results = run_concurrent_focused_tests()
        else:
            results = run_full_performance_suite(args.scale)
        
        # Generate comprehensive report
        if results:
            report_file, json_file = generate_performance_report(results, args.output_dir)
            
            execution_time = time.time() - start_time
            print(f"\n✅ Performance testing completed in {execution_time:.1f} seconds")
            print(f"📁 Results saved to: {args.output_dir}/")
            
            # Print key metrics summary
            print("\n📈 KEY PERFORMANCE METRICS:")
            
            if 'recommendations' in results and results['recommendations']:
                print("🔍 TOP RECOMMENDATIONS:")
                for i, rec in enumerate(results['recommendations'][:3], 1):
                    print(f"  {i}. {rec}")
            
        else:
            print("❌ No results generated")
            
    except KeyboardInterrupt:
        print("\n⏹️  Performance testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Performance testing failed: {e}")
        logging.error(f"Performance testing failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()