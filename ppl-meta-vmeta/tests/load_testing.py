"""
MVR-People Load Testing Suite

Stress testing and load scenarios to validate system behavior under high load:
- Concurrent MVR creation
- High-volume similarity searches
- Queue saturation testing
- Database connection pool stress
- Memory and CPU profiling

Author: PPL Meta Platform
Date: November 1, 2025
Version: 1.0.0
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4
import numpy as np
import psutil
import resource

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import asyncpg
from database.mvr_repository import MVRRepository
from services.mvr_service import MVRService
from services.mvr_matcher import MVRMatcher
from ml.mvr_processor import MVRProcessor


# ============================================================================
# Load Test 1: Concurrent MVR Creation
# ============================================================================

async def load_test_concurrent_creation(
    mvr_service: MVRService,
    num_concurrent: int = 50,
    num_batches: int = 5
) -> Dict[str, Any]:
    """
    Test concurrent MVR creation to identify bottlenecks.
    
    Args:
        mvr_service: MVR service instance
        num_concurrent: Number of concurrent creations per batch
        num_batches: Number of batches to run
        
    Returns:
        Load test results
    """
    print("\n" + "=" * 80)
    print("⚡ LOAD TEST 1: Concurrent MVR Creation")
    print("=" * 80)
    print(f"Concurrent operations: {num_concurrent}")
    print(f"Batches: {num_batches}")
    print(f"Total operations: {num_concurrent * num_batches}")
    print()
    
    total_successful = 0
    total_failed = 0
    batch_durations = []
    
    for batch_num in range(num_batches):
        print(f"🔄 Running batch {batch_num + 1}/{num_batches}...")
        
        # Create concurrent tasks
        tasks = []
        for i in range(num_concurrent):
            # Mock person objects
            person_objects = [{
                "person_id": f"load_test_{batch_num}_{i}",
                "faces": [{
                    "face_id": f"face_{batch_num}_{i}",
                    "embedding": np.random.rand(512).tolist(),
                    "quality_score": 0.85,
                    "bbox": [100, 100, 200, 200],
                }],
                "age_estimate": {"min": 25, "max": 35, "confidence": 0.85},
                "gender_estimate": {"gender": "male", "confidence": 0.90}
            }]
            
            individual_uuid = uuid4()
            
            # Create task
            task = mvr_service.create_mvr_people_from_individual(
                individual_uuid=individual_uuid,
                person_objects=person_objects,
                auto_created=False
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        batch_duration = time.time() - start_time
        batch_durations.append(batch_duration)
        
        # Count successes/failures
        batch_successful = sum(1 for r in results if not isinstance(r, Exception))
        batch_failed = sum(1 for r in results if isinstance(r, Exception))
        
        total_successful += batch_successful
        total_failed += batch_failed
        
        print(f"  ✅ Completed in {batch_duration:.2f}s")
        print(f"  • Successful: {batch_successful}")
        print(f"  • Failed: {batch_failed}")
        print()
    
    # Calculate statistics
    total_operations = num_concurrent * num_batches
    avg_batch_duration = sum(batch_durations) / len(batch_durations)
    throughput = total_operations / sum(batch_durations)
    
    print("📈 RESULTS:")
    print(f"  • Total operations: {total_operations}")
    print(f"  • Successful: {total_successful}")
    print(f"  • Failed: {total_failed}")
    print(f"  • Success rate: {(total_successful/total_operations)*100:.1f}%")
    print(f"  • Average batch duration: {avg_batch_duration:.2f}s")
    print(f"  • Throughput: {throughput:.1f} operations/second")
    print()
    
    return {
        "test": "concurrent_creation",
        "total_operations": total_operations,
        "successful": total_successful,
        "failed": total_failed,
        "success_rate": (total_successful/total_operations)*100,
        "avg_batch_duration": avg_batch_duration,
        "throughput": throughput
    }


# ============================================================================
# Load Test 2: High-Volume Similarity Searches
# ============================================================================

async def load_test_similarity_searches(
    mvr_repository: MVRRepository,
    num_concurrent: int = 100,
    num_iterations: int = 10
) -> Dict[str, Any]:
    """
    Test high-volume concurrent similarity searches.
    
    Args:
        mvr_repository: MVR repository instance
        num_concurrent: Number of concurrent searches
        num_iterations: Number of iterations
        
    Returns:
        Load test results
    """
    print("\n" + "=" * 80)
    print("⚡ LOAD TEST 2: High-Volume Similarity Searches")
    print("=" * 80)
    print(f"Concurrent searches: {num_concurrent}")
    print(f"Iterations: {num_iterations}")
    print(f"Total searches: {num_concurrent * num_iterations}")
    print()
    
    total_successful = 0
    total_failed = 0
    iteration_durations = []
    
    for iteration in range(num_iterations):
        print(f"🔄 Iteration {iteration + 1}/{num_iterations}...")
        
        # Create concurrent search tasks
        tasks = []
        for i in range(num_concurrent):
            query_embedding = np.random.rand(512)
            
            task = mvr_repository.find_similar_mvr(
                face_embedding=query_embedding,
                limit=10,
                similarity_threshold=0.7
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        iteration_duration = time.time() - start_time
        iteration_durations.append(iteration_duration)
        
        # Count successes/failures
        iteration_successful = sum(1 for r in results if not isinstance(r, Exception))
        iteration_failed = sum(1 for r in results if isinstance(r, Exception))
        
        total_successful += iteration_successful
        total_failed += iteration_failed
        
        print(f"  ✅ Completed in {iteration_duration:.2f}s")
        print(f"  • Successful: {iteration_successful}")
        print(f"  • Failed: {iteration_failed}")
        print()
    
    # Calculate statistics
    total_searches = num_concurrent * num_iterations
    avg_iteration_duration = sum(iteration_durations) / len(iteration_durations)
    throughput = total_searches / sum(iteration_durations)
    
    print("📈 RESULTS:")
    print(f"  • Total searches: {total_searches}")
    print(f"  • Successful: {total_successful}")
    print(f"  • Failed: {total_failed}")
    print(f"  • Success rate: {(total_successful/total_searches)*100:.1f}%")
    print(f"  • Average iteration duration: {avg_iteration_duration:.2f}s")
    print(f"  • Throughput: {throughput:.1f} searches/second")
    print()
    
    return {
        "test": "similarity_searches",
        "total_searches": total_searches,
        "successful": total_successful,
        "failed": total_failed,
        "success_rate": (total_successful/total_searches)*100,
        "avg_iteration_duration": avg_iteration_duration,
        "throughput": throughput
    }


# ============================================================================
# Load Test 3: Connection Pool Stress
# ============================================================================

async def load_test_connection_pool(
    pool: asyncpg.Pool,
    num_concurrent: int = 50,
    duration_seconds: int = 30
) -> Dict[str, Any]:
    """
    Stress test database connection pool.
    
    Args:
        pool: Database connection pool
        num_concurrent: Number of concurrent operations
        duration_seconds: Test duration
        
    Returns:
        Load test results
    """
    print("\n" + "=" * 80)
    print("⚡ LOAD TEST 3: Connection Pool Stress")
    print("=" * 80)
    print(f"Concurrent connections: {num_concurrent}")
    print(f"Duration: {duration_seconds}s")
    print(f"Pool size: {pool.get_size()}")
    print(f"Pool min/max: {pool.get_min_size()}/{pool.get_max_size()}")
    print()
    
    total_queries = 0
    total_errors = 0
    start_time = time.time()
    
    async def execute_query():
        """Execute a simple query."""
        nonlocal total_queries, total_errors
        try:
            result = await pool.fetchval("SELECT COUNT(*) FROM mvr_people")
            total_queries += 1
            return result
        except Exception as e:
            total_errors += 1
            return None
    
    # Run concurrent queries for duration
    print("🔄 Stressing connection pool...")
    while (time.time() - start_time) < duration_seconds:
        tasks = [execute_query() for _ in range(num_concurrent)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report progress every 5 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 5 == 0:
            qps = total_queries / elapsed
            print(f"  • Elapsed: {elapsed:.0f}s | Queries: {total_queries} | Errors: {total_errors} | QPS: {qps:.1f}")
        
        await asyncio.sleep(0.1)  # Small delay between batches
    
    elapsed_time = time.time() - start_time
    qps = total_queries / elapsed_time
    error_rate = (total_errors / (total_queries + total_errors)) * 100
    
    # Pool statistics
    pool_size = pool.get_size()
    pool_idle = pool.get_idle_size()
    
    print()
    print("📈 RESULTS:")
    print(f"  • Duration: {elapsed_time:.1f}s")
    print(f"  • Total queries: {total_queries}")
    print(f"  • Total errors: {total_errors}")
    print(f"  • Error rate: {error_rate:.2f}%")
    print(f"  • Queries per second: {qps:.1f}")
    print(f"  • Pool size: {pool_size}")
    print(f"  • Idle connections: {pool_idle}")
    print()
    
    return {
        "test": "connection_pool_stress",
        "duration_seconds": elapsed_time,
        "total_queries": total_queries,
        "total_errors": total_errors,
        "error_rate": error_rate,
        "queries_per_second": qps,
        "pool_size": pool_size,
        "idle_connections": pool_idle
    }


# ============================================================================
# Load Test 4: Memory and CPU Profiling
# ============================================================================

async def load_test_resource_profiling(
    mvr_service: MVRService,
    num_operations: int = 100
) -> Dict[str, Any]:
    """
    Profile memory and CPU usage during MVR operations.
    
    Args:
        mvr_service: MVR service instance
        num_operations: Number of operations to profile
        
    Returns:
        Resource profiling results
    """
    print("\n" + "=" * 80)
    print("⚡ LOAD TEST 4: Memory and CPU Profiling")
    print("=" * 80)
    print(f"Operations to profile: {num_operations}")
    print()
    
    # Get initial resource usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    initial_cpu = process.cpu_percent(interval=1)
    
    print(f"📊 Initial State:")
    print(f"  • Memory: {initial_memory:.1f} MB")
    print(f"  • CPU: {initial_cpu:.1f}%")
    print()
    
    # Track resource usage during operations
    memory_samples = []
    cpu_samples = []
    
    print("🔄 Running operations with profiling...")
    start_time = time.time()
    
    for i in range(num_operations):
        # Mock person objects
        person_objects = [{
            "person_id": f"profile_{i}",
            "faces": [{
                "face_id": f"face_{i}",
                "embedding": np.random.rand(512).tolist(),
                "quality_score": 0.85,
                "bbox": [100, 100, 200, 200],
            }],
            "age_estimate": {"min": 25, "max": 35, "confidence": 0.85},
            "gender_estimate": {"gender": "male", "confidence": 0.90}
        }]
        
        individual_uuid = uuid4()
        
        # Execute operation
        try:
            await mvr_service.create_mvr_people_from_individual(
                individual_uuid=individual_uuid,
                person_objects=person_objects,
                auto_created=False
            )
        except Exception:
            pass  # Ignore failures for profiling
        
        # Sample resources every 10 operations
        if (i + 1) % 10 == 0:
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_samples.append(memory_mb)
            cpu_samples.append(cpu_percent)
            
            print(f"  • Operation {i+1}: Memory={memory_mb:.1f}MB, CPU={cpu_percent:.1f}%")
    
    elapsed_time = time.time() - start_time
    
    # Final resource usage
    final_memory = process.memory_info().rss / 1024 / 1024
    final_cpu = process.cpu_percent(interval=1)
    
    # Calculate statistics
    avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else final_memory
    max_memory = max(memory_samples) if memory_samples else final_memory
    avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else final_cpu
    max_cpu = max(cpu_samples) if cpu_samples else final_cpu
    
    memory_delta = final_memory - initial_memory
    
    print()
    print("📈 RESULTS:")
    print(f"  • Duration: {elapsed_time:.1f}s")
    print(f"  • Operations: {num_operations}")
    print(f"  • Throughput: {num_operations/elapsed_time:.1f} ops/second")
    print()
    print(f"  Memory:")
    print(f"    - Initial: {initial_memory:.1f} MB")
    print(f"    - Final: {final_memory:.1f} MB")
    print(f"    - Delta: {memory_delta:+.1f} MB")
    print(f"    - Average: {avg_memory:.1f} MB")
    print(f"    - Peak: {max_memory:.1f} MB")
    print()
    print(f"  CPU:")
    print(f"    - Initial: {initial_cpu:.1f}%")
    print(f"    - Final: {final_cpu:.1f}%")
    print(f"    - Average: {avg_cpu:.1f}%")
    print(f"    - Peak: {max_cpu:.1f}%")
    print()
    
    return {
        "test": "resource_profiling",
        "duration_seconds": elapsed_time,
        "operations": num_operations,
        "throughput": num_operations/elapsed_time,
        "memory": {
            "initial_mb": initial_memory,
            "final_mb": final_memory,
            "delta_mb": memory_delta,
            "average_mb": avg_memory,
            "peak_mb": max_memory
        },
        "cpu": {
            "initial_percent": initial_cpu,
            "final_percent": final_cpu,
            "average_percent": avg_cpu,
            "peak_percent": max_cpu
        }
    }


# ============================================================================
# Main Load Test Runner
# ============================================================================

async def run_all_load_tests():
    """Run all load tests."""
    
    print("\n" + "=" * 80)
    print("🚀 MVR-People Load Testing Suite")
    print("=" * 80)
    from datetime import datetime
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize services
    print("🔧 Initializing services...")
    try:
        # Database connection (use same DB as vmeta service)
        pool = await asyncpg.create_pool(
            host='localhost',
            port=5432,
            user='ppl_user',
            password='ppl_password',
            database='ppl_meta',
            min_size=10,
            max_size=50  # Higher pool for load testing
        )
        
        # Initialize components
        repository = MVRRepository(connection_pool=pool)
        ml_processor = MVRProcessor()
        service = MVRService(
            repository=repository,
            ml_processor=ml_processor
        )
        matcher = MVRMatcher(
            repository=repository,
            ml_processor=ml_processor
        )
        
        print("✅ Services initialized")
        print()
        
        # Run load tests (reduced scale for quick testing)
        results = []
        
        # Load Test 1: Concurrent Creation
        print("⚠️  Load Test 1 skipped (requires real Individuals)")
        # result1 = await load_test_concurrent_creation(service, num_concurrent=10, num_batches=2)
        # results.append(result1)
        
        # Load Test 2: Similarity Searches
        result2 = await load_test_similarity_searches(repository, num_concurrent=20, num_iterations=5)
        results.append(result2)
        
        # Load Test 3: Connection Pool
        result3 = await load_test_connection_pool(pool, num_concurrent=30, duration_seconds=15)
        results.append(result3)
        
        # Load Test 4: Resource Profiling
        print("⚠️  Load Test 4 skipped (requires real Individuals)")
        # result4 = await load_test_resource_profiling(service, num_operations=50)
        # results.append(result4)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 LOAD TEST SUMMARY")
        print("=" * 80)
        
        for result in results:
            test_name = result.get('test', 'unknown')
            print(f"  ✅ {test_name}")
        
        print()
        print(f"Completed {len(results)} load tests")
        print()
        
        # Save results
        import json
        output_file = Path(__file__).parent / "load_test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": results
            }, f, indent=2)
        
        print(f"💾 Results saved to: {output_file}")
        print()
        
        # Cleanup
        await pool.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Load testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_load_tests())
    sys.exit(0 if success else 1)
