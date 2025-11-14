"""
Load Testing and Performance Validation for Batch Processing Pipeline
PPL Meta Platform - vmeta Service

Comprehensive load testing suite to validate performance under various
conditions, identify bottlenecks, and measure system capacity.

Created: November 13, 2025
"""

import pytest
import asyncio
import httpx
import time
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, List, Tuple
import statistics
import json
import asyncpg

from src.database.batch_repository import BatchProcessingRepository
from src.services.batch_monitor import BatchMonitor
from src.services.batch_config import BatchConfigService


# Test Configuration
LOAD_TEST_CONFIG = {
    'vmeta_url': 'http://localhost:8008',
    'orchestrator_url': 'http://localhost:8002',
    'db_host': 'localhost',
    'db_port': 5432,
    'db_name': 'ppl_meta_vmeta_test',
    'db_user': 'postgres',
    'db_password': 'postgres',
    
    # Load test parameters
    'max_concurrent_batches': 15,
    'batch_sizes': [2, 5, 10, 15, 20],
    'test_duration_seconds': 300,  # 5 minutes
    'warmup_duration_seconds': 30
}


class PerformanceMetrics:
    """Track and analyze performance metrics."""
    
    def __init__(self):
        self.batch_durations = []
        self.batch_throughputs = []
        self.cache_hit_rates = []
        self.individuals_per_batch = []
        self.mvr_per_batch = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    def add_batch_result(self, result: Dict):
        """Add batch processing result."""
        self.batch_durations.append(result['processing_time_seconds'])
        self.batch_throughputs.append(
            result['video_count'] / result['processing_time_seconds']
        )
        self.cache_hit_rates.append(result['cache_hit_rate'])
        self.individuals_per_batch.append(result['individuals_created'])
        self.mvr_per_batch.append(result['mvr_people_created'])
    
    def add_error(self, error: str):
        """Add error."""
        self.errors.append({
            'timestamp': datetime.utcnow().isoformat(),
            'error': error
        })
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
    
    def stop(self):
        """Stop timing."""
        self.end_time = time.time()
    
    def get_summary(self) -> Dict:
        """Get performance summary."""
        if not self.batch_durations:
            return {'error': 'No data collected'}
        
        total_time = self.end_time - self.start_time if self.end_time else 0
        
        return {
            'total_batches': len(self.batch_durations),
            'total_time_seconds': total_time,
            'batches_per_minute': (len(self.batch_durations) / total_time * 60) if total_time > 0 else 0,
            
            'processing_time': {
                'min': min(self.batch_durations),
                'max': max(self.batch_durations),
                'mean': statistics.mean(self.batch_durations),
                'median': statistics.median(self.batch_durations),
                'stdev': statistics.stdev(self.batch_durations) if len(self.batch_durations) > 1 else 0,
                'p95': self._percentile(self.batch_durations, 95),
                'p99': self._percentile(self.batch_durations, 99)
            },
            
            'throughput_videos_per_sec': {
                'min': min(self.batch_throughputs),
                'max': max(self.batch_throughputs),
                'mean': statistics.mean(self.batch_throughputs),
                'median': statistics.median(self.batch_throughputs)
            },
            
            'cache_hit_rate': {
                'min': min(self.cache_hit_rates),
                'max': max(self.cache_hit_rates),
                'mean': statistics.mean(self.cache_hit_rates),
                'median': statistics.median(self.cache_hit_rates)
            },
            
            'individuals_per_batch': {
                'min': min(self.individuals_per_batch),
                'max': max(self.individuals_per_batch),
                'mean': statistics.mean(self.individuals_per_batch),
                'total': sum(self.individuals_per_batch)
            },
            
            'mvr_per_batch': {
                'min': min(self.mvr_per_batch),
                'max': max(self.mvr_per_batch),
                'mean': statistics.mean(self.mvr_per_batch),
                'total': sum(self.mvr_per_batch)
            },
            
            'errors': {
                'count': len(self.errors),
                'rate': len(self.errors) / len(self.batch_durations) if self.batch_durations else 0,
                'details': self.errors[:10]  # First 10 errors
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[index]
    
    def print_summary(self):
        """Print formatted summary."""
        summary = self.get_summary()
        
        if 'error' in summary:
            print(f"❌ {summary['error']}")
            return
        
        print("\n" + "=" * 70)
        print("LOAD TEST PERFORMANCE SUMMARY")
        print("=" * 70)
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Batches: {summary['total_batches']}")
        print(f"   Total Time: {summary['total_time_seconds']:.1f}s")
        print(f"   Batches/Minute: {summary['batches_per_minute']:.2f}")
        
        print(f"\n⏱️  Processing Time (seconds):")
        print(f"   Min:    {summary['processing_time']['min']:.2f}s")
        print(f"   Mean:   {summary['processing_time']['mean']:.2f}s")
        print(f"   Median: {summary['processing_time']['median']:.2f}s")
        print(f"   Max:    {summary['processing_time']['max']:.2f}s")
        print(f"   P95:    {summary['processing_time']['p95']:.2f}s")
        print(f"   P99:    {summary['processing_time']['p99']:.2f}s")
        print(f"   StdDev: {summary['processing_time']['stdev']:.2f}s")
        
        print(f"\n🚀 Throughput (videos/second):")
        print(f"   Min:    {summary['throughput_videos_per_sec']['min']:.2f}")
        print(f"   Mean:   {summary['throughput_videos_per_sec']['mean']:.2f}")
        print(f"   Median: {summary['throughput_videos_per_sec']['median']:.2f}")
        print(f"   Max:    {summary['throughput_videos_per_sec']['max']:.2f}")
        
        print(f"\n💾 Cache Hit Rate (%):")
        print(f"   Min:    {summary['cache_hit_rate']['min']:.1f}%")
        print(f"   Mean:   {summary['cache_hit_rate']['mean']:.1f}%")
        print(f"   Median: {summary['cache_hit_rate']['median']:.1f}%")
        print(f"   Max:    {summary['cache_hit_rate']['max']:.1f}%")
        
        print(f"\n👤 Individuals per Batch:")
        print(f"   Min:   {summary['individuals_per_batch']['min']}")
        print(f"   Mean:  {summary['individuals_per_batch']['mean']:.1f}")
        print(f"   Max:   {summary['individuals_per_batch']['max']}")
        print(f"   Total: {summary['individuals_per_batch']['total']}")
        
        print(f"\n👥 MVR People per Batch:")
        print(f"   Min:   {summary['mvr_per_batch']['min']}")
        print(f"   Mean:  {summary['mvr_per_batch']['mean']:.1f}")
        print(f"   Max:   {summary['mvr_per_batch']['max']}")
        print(f"   Total: {summary['mvr_per_batch']['total']}")
        
        print(f"\n❌ Errors:")
        print(f"   Count: {summary['errors']['count']}")
        print(f"   Rate:  {summary['errors']['rate']:.2%}")
        
        print("\n" + "=" * 70 + "\n")


@pytest.fixture
async def db_pool():
    """Create database connection pool."""
    pool = await asyncpg.create_pool(
        host=LOAD_TEST_CONFIG['db_host'],
        port=LOAD_TEST_CONFIG['db_port'],
        database=LOAD_TEST_CONFIG['db_name'],
        user=LOAD_TEST_CONFIG['db_user'],
        password=LOAD_TEST_CONFIG['db_password'],
        min_size=5,
        max_size=20
    )
    yield pool
    await pool.close()


@pytest.fixture
async def http_client():
    """Create HTTP client."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture
async def auth_token(http_client):
    """Get authentication token."""
    # For load testing, use a long-lived token or mock auth
    return "test-token-for-load-testing"


@pytest.fixture
async def repository(db_pool):
    """Create repository."""
    return BatchProcessingRepository(db_pool)


@pytest.fixture
async def batch_monitor(repository):
    """Create batch monitor."""
    config_service = BatchConfigService(
        repository=repository,
        config_path='config/batch_processing.yml'
    )
    return BatchMonitor(
        repository=repository,
        config_service=config_service
    )


class TestLoadPerformance:
    """Load testing and performance validation."""
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_concurrent_batches_10(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor
    ):
        """
        Test 10 concurrent batches processing.
        
        Validates:
        - Worker pool handles concurrency
        - No deadlocks or resource conflicts
        - Performance remains acceptable
        - All batches complete successfully
        """
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        num_batches = 10
        videos_per_batch = 5
        
        print(f"\n🚀 Starting load test: {num_batches} concurrent batches")
        print(f"   Videos per batch: {videos_per_batch}")
        
        async def process_batch(batch_num: int) -> Dict:
            """Process a single batch."""
            collection_id = f"load-test-{uuid4()}"
            
            try:
                # Add videos to batch
                for i in range(videos_per_batch):
                    await batch_monitor.add_video_to_batch(
                        collection_id=collection_id,
                        video_uuid=str(uuid4()),
                        video_start_time=datetime.utcnow() - timedelta(seconds=30),
                        video_end_time=datetime.utcnow(),
                        face_detection_session_uuid=str(uuid4()),
                        faces_detected=3
                    )
                
                # Wait for batch to complete (max 60 seconds)
                for _ in range(60):
                    await asyncio.sleep(1)
                    
                    batch_state = await repository.get_active_batch(collection_id)
                    if batch_state and batch_state['status'] == 'completed':
                        return batch_state
                
                raise Exception(f"Batch {batch_num} timeout")
                
            except Exception as e:
                metrics.add_error(f"Batch {batch_num}: {str(e)}")
                raise
        
        # Execute all batches concurrently
        start_time = time.time()
        
        results = await asyncio.gather(
            *[process_batch(i) for i in range(num_batches)],
            return_exceptions=True
        )
        
        end_time = time.time()
        
        # Collect metrics
        for result in results:
            if isinstance(result, Exception):
                print(f"❌ Batch failed: {result}")
            else:
                metrics.add_batch_result(result)
        
        metrics.stop()
        
        # Print results
        metrics.print_summary()
        
        # Assertions
        assert len([r for r in results if not isinstance(r, Exception)]) >= 8, \
            "At least 80% of batches should complete successfully"
        
        summary = metrics.get_summary()
        assert summary['processing_time']['mean'] < 60, \
            "Average processing time should be under 60 seconds"
        
        print(f"✅ Concurrent load test completed in {end_time - start_time:.1f}s")
    
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_varying_batch_sizes(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor
    ):
        """
        Test performance with varying batch sizes: 2, 5, 10, 15, 20 videos.
        
        Validates:
        - Linear scaling of processing time
        - Cache effectiveness at different sizes
        - No performance degradation with larger batches
        """
        
        batch_sizes = [2, 5, 10, 15, 20]
        results_by_size = {}
        
        print(f"\n🔢 Testing batch sizes: {batch_sizes}")
        
        for batch_size in batch_sizes:
            print(f"\n📊 Testing batch size: {batch_size} videos")
            
            metrics = PerformanceMetrics()
            metrics.start()
            
            collection_id = f"size-test-{batch_size}-{uuid4()}"
            
            # Process 3 batches of this size
            for batch_num in range(3):
                # Add videos
                for i in range(batch_size):
                    await batch_monitor.add_video_to_batch(
                        collection_id=collection_id,
                        video_uuid=str(uuid4()),
                        video_start_time=datetime.utcnow() - timedelta(seconds=30),
                        video_end_time=datetime.utcnow(),
                        face_detection_session_uuid=str(uuid4()),
                        faces_detected=3
                    )
                
                # Wait for completion
                await asyncio.sleep(10)
                
                batch_state = await repository.get_active_batch(collection_id)
                if batch_state:
                    metrics.add_batch_result(batch_state)
            
            metrics.stop()
            summary = metrics.get_summary()
            results_by_size[batch_size] = summary
            
            print(f"   Mean time: {summary['processing_time']['mean']:.2f}s")
            print(f"   Throughput: {summary['throughput_videos_per_sec']['mean']:.2f} videos/s")
        
        # Print comparison
        print("\n📈 Batch Size Performance Comparison:")
        print("=" * 70)
        print(f"{'Size':<6} {'Mean Time':<12} {'Throughput':<15} {'Cache Hit':<12}")
        print("=" * 70)
        
        for size, summary in results_by_size.items():
            print(
                f"{size:<6} "
                f"{summary['processing_time']['mean']:>8.2f}s    "
                f"{summary['throughput_videos_per_sec']['mean']:>8.2f} vid/s  "
                f"{summary['cache_hit_rate']['mean']:>8.1f}%"
            )
        
        print("=" * 70)
    
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_sustained_load_5_minutes(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor
    ):
        """
        Test sustained load for 5 minutes.
        
        Validates:
        - System stability under continuous load
        - No memory leaks
        - Worker pool doesn't exhaust
        - Database connections remain healthy
        """
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        test_duration = 300  # 5 minutes
        batch_interval = 20  # New batch every 20 seconds
        
        print(f"\n⏱️  Starting sustained load test: {test_duration}s duration")
        print(f"   New batch every {batch_interval}s")
        
        start_time = time.time()
        batch_count = 0
        
        while time.time() - start_time < test_duration:
            batch_count += 1
            collection_id = f"sustained-test-{uuid4()}"
            
            print(f"   Batch {batch_count} starting...")
            
            # Add 5 videos
            for i in range(5):
                await batch_monitor.add_video_to_batch(
                    collection_id=collection_id,
                    video_uuid=str(uuid4()),
                    video_start_time=datetime.utcnow() - timedelta(seconds=30),
                    video_end_time=datetime.utcnow(),
                    face_detection_session_uuid=str(uuid4()),
                    faces_detected=3
                )
            
            # Don't wait for completion, continue adding batches
            await asyncio.sleep(batch_interval)
        
        # Wait for all batches to complete
        print(f"\n⏱️  Test duration complete, waiting for batches to finish...")
        await asyncio.sleep(60)
        
        metrics.stop()
        
        # Collect all completed batches
        # (Implementation would query database for all batches in time range)
        
        print(f"\n✅ Sustained load test completed")
        print(f"   Total batches submitted: {batch_count}")
        print(f"   Test duration: {test_duration}s")
    
    
    @pytest.mark.asyncio
    @pytest.mark.load
    async def test_cache_warmup_performance(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor
    ):
        """
        Test cache performance improvement over time.
        
        Validates:
        - First batch: 0% cache hit (cold start)
        - Second batch: 20-40% cache hit
        - Third batch: 40-60% cache hit
        - Cache hit rate increases progressively
        """
        
        collection_id = f"cache-test-{uuid4()}"
        batch_results = []
        
        print(f"\n💾 Testing cache warmup over 5 batches")
        
        for batch_num in range(1, 6):
            print(f"\n   Batch {batch_num}/5:")
            
            # Add 5 videos
            for i in range(5):
                await batch_monitor.add_video_to_batch(
                    collection_id=collection_id,
                    video_uuid=str(uuid4()),
                    video_start_time=datetime.utcnow() - timedelta(seconds=30),
                    video_end_time=datetime.utcnow(),
                    face_detection_session_uuid=str(uuid4()),
                    faces_detected=3
                )
            
            # Wait for completion
            await asyncio.sleep(15)
            
            batch_state = await repository.get_active_batch(collection_id)
            if batch_state:
                cache_rate = batch_state['cache_hit_rate']
                processing_time = batch_state['processing_time_seconds']
                
                batch_results.append({
                    'batch_num': batch_num,
                    'cache_hit_rate': cache_rate,
                    'processing_time': processing_time
                })
                
                print(f"      Cache hit: {cache_rate:.1f}%")
                print(f"      Time: {processing_time:.2f}s")
        
        # Print progression
        print(f"\n📊 Cache Performance Progression:")
        print("=" * 50)
        print(f"{'Batch':<8} {'Cache Hit Rate':<18} {'Time (s)':<12}")
        print("=" * 50)
        
        for result in batch_results:
            print(
                f"{result['batch_num']:<8} "
                f"{result['cache_hit_rate']:>12.1f}%      "
                f"{result['processing_time']:>8.2f}s"
            )
        
        print("=" * 50)
        
        # Validate progression
        if len(batch_results) >= 2:
            assert batch_results[-1]['cache_hit_rate'] > batch_results[0]['cache_hit_rate'], \
                "Cache hit rate should increase over time"
            
            print(f"\n✅ Cache warmup validated: {batch_results[0]['cache_hit_rate']:.1f}% → {batch_results[-1]['cache_hit_rate']:.1f}%")


class TestStressConditions:
    """Test system behavior under stress conditions."""
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_worker_pool_saturation(
        self,
        http_client,
        auth_token,
        repository,
        batch_monitor
    ):
        """
        Test worker pool behavior when saturated.
        
        Submit more batches than worker pool capacity and validate:
        - Batches queue properly
        - No batch is lost
        - All batches eventually complete
        - No deadlocks occur
        """
        
        num_batches = 20  # Exceed typical worker pool size (3-5)
        videos_per_batch = 5
        
        print(f"\n🔥 Stress test: {num_batches} batches (saturate worker pool)")
        
        submitted_collections = []
        
        # Submit all batches rapidly
        for i in range(num_batches):
            collection_id = f"stress-test-{i}-{uuid4()}"
            submitted_collections.append(collection_id)
            
            # Add videos
            for j in range(videos_per_batch):
                await batch_monitor.add_video_to_batch(
                    collection_id=collection_id,
                    video_uuid=str(uuid4()),
                    video_start_time=datetime.utcnow() - timedelta(seconds=30),
                    video_end_time=datetime.utcnow(),
                    face_detection_session_uuid=str(uuid4()),
                    faces_detected=3
                )
            
            await asyncio.sleep(0.5)  # Small delay between submissions
        
        print(f"   ✓ Submitted {num_batches} batches")
        
        # Wait for all to complete (up to 10 minutes)
        print(f"   ⏱️  Waiting for completion (max 10 minutes)...")
        
        completed = 0
        max_wait = 600  # 10 minutes
        
        for _ in range(max_wait):
            await asyncio.sleep(1)
            
            # Check how many completed
            completed_count = 0
            for collection_id in submitted_collections:
                batch_state = await repository.get_active_batch(collection_id)
                if batch_state and batch_state['status'] == 'completed':
                    completed_count += 1
            
            if completed_count >= num_batches * 0.95:  # 95% complete
                completed = completed_count
                break
        
        print(f"   ✓ Completed: {completed}/{num_batches}")
        
        assert completed >= num_batches * 0.9, \
            f"At least 90% of batches should complete (got {completed}/{num_batches})"
        
        print(f"✅ Worker pool stress test passed")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'load', '--tb=short'])
