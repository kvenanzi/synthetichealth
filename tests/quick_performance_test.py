#!/usr/bin/env python3
"""
Quick Healthcare Migration Performance Test

Rapid performance testing for migration simulation system.
"""

import gc
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
import pytest

psutil = pytest.importorskip("psutil", reason="performance tests require psutil")

@dataclass
class QuickPatientRecord:
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mrn: str = ""
    conditions: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.mrn:
            self.mrn = f"MRN{self.patient_id}"

class QuickMigrationSimulator:
    def __init__(self):
        self.processed = 0
        
    def simulate_patient_migration(self, patient: QuickPatientRecord) -> Dict[str, Any]:
        # Simulate processing with minimal overhead
        start = time.time()
        
        # Quick simulation of stage processing
        quality = 1.0
        for stage in ["extract", "transform", "validate", "load"]:
            time.sleep(0.001)  # 1ms per stage
            if hash(patient.patient_id + stage) % 20 == 0:  # 5% failure rate
                quality *= 0.85
        
        duration = time.time() - start
        self.processed += 1
        
        return {
            "patient_id": patient.patient_id,
            "processing_time": duration,
            "quality_score": quality,
            "success": quality > 0.7
        }
    
    def simulate_batch_migration(self, patients: List[QuickPatientRecord]) -> Dict[str, Any]:
        start = time.time()
        results = [self.simulate_patient_migration(p) for p in patients]
        batch_time = time.time() - start
        
        successful = sum(1 for r in results if r["success"])
        avg_quality = statistics.mean([r["quality_score"] for r in results])
        
        return {
            "batch_time": batch_time,
            "total_patients": len(patients),
            "successful_patients": successful,
            "success_rate": successful / len(patients),
            "average_quality": avg_quality,
            "throughput": len(patients) / batch_time
        }

def quick_test():
    print("🏥 Quick Healthcare Migration Performance Test")
    print("=" * 50)
    
    # Test configurations
    patient_counts = [50, 100, 250, 500]
    worker_counts = [1, 2, 4]
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "cpu_cores": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3)
        },
        "scalability_tests": [],
        "concurrency_tests": []
    }
    
    # Scalability Tests
    print("\n🔬 Testing Scalability...")
    simulator = QuickMigrationSimulator()
    
    for count in patient_counts:
        print(f"  Testing {count} patients...")
        
        # Generate test patients
        patients = [QuickPatientRecord() for _ in range(count)]
        for i, p in enumerate(patients):
            p.conditions = [{"name": "Test Condition"}] if i % 2 == 0 else []
        
        # Memory before
        gc.collect()
        mem_before = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Run test
        result = simulator.simulate_batch_migration(patients)
        
        # Memory after
        mem_after = psutil.Process().memory_info().rss / 1024 / 1024
        
        test_result = {
            "patient_count": count,
            "throughput": result["throughput"],
            "success_rate": result["success_rate"],
            "average_quality": result["average_quality"],
            "memory_used_mb": mem_after - mem_before,
            "memory_per_patient_kb": ((mem_after - mem_before) * 1024) / count if count > 0 else 0
        }
        
        results["scalability_tests"].append(test_result)
        print(f"    Throughput: {test_result['throughput']:.0f} patients/sec")
        print(f"    Memory: {test_result['memory_per_patient_kb']:.1f} KB/patient")
    
    # Concurrency Tests  
    print("\n⚡ Testing Concurrency...")
    test_patients = [QuickPatientRecord() for _ in range(200)]
    
    for workers in worker_counts:
        print(f"  Testing {workers} workers...")
        
        start_time = time.time()
        
        if workers == 1:
            sim = QuickMigrationSimulator()
            result = sim.simulate_batch_migration(test_patients)
        else:
            # Split patients among workers
            batch_size = len(test_patients) // workers
            batches = [test_patients[i:i+batch_size] for i in range(0, len(test_patients), batch_size)]
            
            batch_results = []
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(QuickMigrationSimulator().simulate_batch_migration, batch) 
                          for batch in batches]
                batch_results = [f.result() for f in futures]
            
            # Aggregate results
            total_time = time.time() - start_time
            total_patients = sum(r["total_patients"] for r in batch_results)
            successful = sum(r["successful_patients"] for r in batch_results)
            avg_quality = statistics.mean([r["average_quality"] for r in batch_results])
            
            result = {
                "throughput": total_patients / total_time,
                "success_rate": successful / total_patients,
                "average_quality": avg_quality
            }
        
        test_result = {
            "workers": workers,
            "throughput": result["throughput"],
            "success_rate": result["success_rate"],
            "average_quality": result["average_quality"],
            "scaling_efficiency": result["throughput"] / (results["concurrency_tests"][0]["throughput"] if results["concurrency_tests"] else result["throughput"])
        }
        
        results["concurrency_tests"].append(test_result)
        print(f"    Throughput: {test_result['throughput']:.0f} patients/sec")
    
    # Generate recommendations
    max_throughput = max([r["throughput"] for r in results["scalability_tests"]])
    best_memory_efficiency = min([r["memory_per_patient_kb"] for r in results["scalability_tests"]])
    best_workers = max(results["concurrency_tests"], key=lambda x: x["throughput"])["workers"]
    
    recommendations = [
        f"PERFORMANCE: Maximum throughput achieved: {max_throughput:.0f} patients/sec",
        f"MEMORY: Best efficiency: {best_memory_efficiency:.1f} KB per patient",
        f"CONCURRENCY: Optimal worker count: {best_workers}",
        "PRODUCTION: For 10,000+ patients, use batch processing with checkpoints",
        f"SCALING: Allocate {best_memory_efficiency * 10:.0f} MB per 10,000 patients"
    ]
    
    results["recommendations"] = recommendations
    
    # Save results
    filename = f"quick_performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📊 PERFORMANCE SUMMARY")
    print("=" * 30)
    print(f"Max Throughput: {max_throughput:.0f} patients/sec")
    print(f"Memory Efficiency: {best_memory_efficiency:.1f} KB/patient")
    print(f"Optimal Workers: {best_workers}")
    
    print(f"\n🔍 KEY RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"  {i}. {rec}")
    
    print(f"\n📁 Results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    quick_test()
