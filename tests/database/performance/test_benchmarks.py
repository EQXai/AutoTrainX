"""Performance benchmark tests for database operations."""

import pytest
import time
import statistics
from typing import List, Callable
from datetime import datetime, timedelta

from src.database.enums import ExecutionStatus, PipelineMode
from src.database.models import Execution, Variation


class BenchmarkHelper:
    """Helper class for running benchmarks."""
    
    @staticmethod
    def time_operation(func: Callable, iterations: int = 10) -> dict:
        """Time an operation over multiple iterations.
        
        Returns:
            Dictionary with timing statistics
        """
        times = []
        
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "total": sum(times),
            "iterations": iterations
        }
    
    @staticmethod
    def format_timing(timing: dict) -> str:
        """Format timing results for display."""
        return (
            f"Mean: {timing['mean']*1000:.2f}ms, "
            f"Median: {timing['median']*1000:.2f}ms, "
            f"StdDev: {timing['stdev']*1000:.2f}ms, "
            f"Min: {timing['min']*1000:.2f}ms, "
            f"Max: {timing['max']*1000:.2f}ms"
        )


@pytest.mark.benchmark
class TestCreateOperationPerformance:
    """Benchmark tests for create operations."""
    
    def test_single_create_performance(self, db_manager):
        """Benchmark single execution creation."""
        counter = 0
        
        def create_single():
            nonlocal counter
            db_manager.create_execution(
                job_id=f"bench-single-{counter}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="benchmark_dataset",
                preset="benchmark_preset"
            )
            counter += 1
        
        timing = BenchmarkHelper.time_operation(create_single, iterations=100)
        print(f"\nSingle create: {BenchmarkHelper.format_timing(timing)}")
        
        # Performance assertion - single create should be fast
        assert timing["mean"] < 0.05  # Less than 50ms average
    
    def test_batch_create_performance(self, db_manager):
        """Benchmark batch execution creation."""
        counter = 0
        
        def create_batch():
            nonlocal counter
            batch_data = [
                {
                    "job_id": f"bench-batch-{counter}-{i}",
                    "pipeline_mode": PipelineMode.SINGLE.value,
                    "dataset_name": "benchmark_dataset",
                    "preset": "benchmark_preset"
                }
                for i in range(10)
            ]
            db_manager.batch_create_executions(batch_data)
            counter += 1
        
        timing = BenchmarkHelper.time_operation(create_batch, iterations=10)
        print(f"\nBatch create (10 items): {BenchmarkHelper.format_timing(timing)}")
        
        # Batch should be more efficient per item
        per_item_time = timing["mean"] / 10
        assert per_item_time < 0.01  # Less than 10ms per item
    
    def test_create_vs_batch_efficiency(self, db_manager):
        """Compare single vs batch creation efficiency."""
        # Time 100 single creates
        single_times = []
        for i in range(100):
            start = time.perf_counter()
            db_manager.create_execution(
                job_id=f"compare-single-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="benchmark_dataset",
                preset="benchmark_preset"
            )
            single_times.append(time.perf_counter() - start)
        
        single_total = sum(single_times)
        
        # Time batch create of 100
        start = time.perf_counter()
        batch_data = [
            {
                "job_id": f"compare-batch-{i}",
                "pipeline_mode": PipelineMode.SINGLE.value,
                "dataset_name": "benchmark_dataset",
                "preset": "benchmark_preset"
            }
            for i in range(100)
        ]
        db_manager.batch_create_executions(batch_data)
        batch_total = time.perf_counter() - start
        
        print(f"\n100 single creates: {single_total:.3f}s")
        print(f"100 batch create: {batch_total:.3f}s")
        print(f"Speedup: {single_total/batch_total:.2f}x")
        
        # Batch should be at least 5x faster
        assert batch_total < single_total / 5


@pytest.mark.benchmark
class TestUpdateOperationPerformance:
    """Benchmark tests for update operations."""
    
    def test_single_update_performance(self, db_manager):
        """Benchmark single status updates."""
        # Create test data
        job_ids = []
        for i in range(100):
            exec = db_manager.create_execution(
                job_id=f"update-single-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="benchmark_dataset",
                preset="benchmark_preset"
            )
            job_ids.append(exec.job_id)
        
        # Benchmark updates
        index = 0
        def update_single():
            nonlocal index
            db_manager.update_execution_status(
                job_ids[index % len(job_ids)],
                ExecutionStatus.DONE
            )
            index += 1
        
        timing = BenchmarkHelper.time_operation(update_single, iterations=50)
        print(f"\nSingle update: {BenchmarkHelper.format_timing(timing)}")
        
        assert timing["mean"] < 0.05  # Less than 50ms average
    
    def test_batch_update_performance(self, db_manager):
        """Benchmark batch status updates."""
        # Create test data
        base_ids = []
        for batch in range(10):
            for i in range(50):
                exec = db_manager.create_execution(
                    job_id=f"update-batch-{batch}-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name="benchmark_dataset",
                    preset="benchmark_preset"
                )
                base_ids.append(exec.job_id)
        
        # Benchmark batch updates
        batch_num = 0
        def update_batch():
            nonlocal batch_num
            start_idx = (batch_num * 50) % len(base_ids)
            updates = [
                {
                    "job_id": base_ids[start_idx + i],
                    "status": ExecutionStatus.DONE
                }
                for i in range(50)
            ]
            db_manager.batch_update_execution_status(updates)
            batch_num += 1
        
        timing = BenchmarkHelper.time_operation(update_batch, iterations=10)
        print(f"\nBatch update (50 items): {BenchmarkHelper.format_timing(timing)}")
        
        # Should be efficient
        per_item_time = timing["mean"] / 50
        assert per_item_time < 0.005  # Less than 5ms per item


@pytest.mark.benchmark 
class TestQueryPerformance:
    """Benchmark tests for query operations."""
    
    def test_statistics_query_performance(self, db_manager):
        """Benchmark statistics queries."""
        # Create diverse test data
        statuses = list(ExecutionStatus)
        for i in range(200):
            db_manager.create_execution(
                job_id=f"stats-bench-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i % 10}",
                preset=f"preset_{i % 5}"
            )
            # Update to various statuses
            if i % 4 != 0:
                db_manager.update_execution_status(
                    f"stats-bench-{i}",
                    statuses[i % len(statuses)]
                )
        
        # Benchmark original statistics
        def get_stats_original():
            return db_manager.get_statistics()
        
        timing_original = BenchmarkHelper.time_operation(get_stats_original, iterations=10)
        print(f"\nOriginal statistics: {BenchmarkHelper.format_timing(timing_original)}")
        
        # Benchmark optimized statistics
        def get_stats_optimized():
            return db_manager.get_statistics_optimized()
        
        timing_optimized = BenchmarkHelper.time_operation(get_stats_optimized, iterations=10)
        print(f"Optimized statistics: {BenchmarkHelper.format_timing(timing_optimized)}")
        
        # Optimized should be faster
        speedup = timing_original["mean"] / timing_optimized["mean"]
        print(f"Speedup: {speedup:.2f}x")
        assert speedup > 2.0  # At least 2x faster
    
    def test_all_jobs_query_performance(self, db_manager):
        """Benchmark all jobs retrieval."""
        # Create mixed data
        for i in range(100):
            db_manager.create_execution(
                job_id=f"all-jobs-exec-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i % 5}",
                preset="benchmark_preset"
            )
        
        with db_manager.get_session() as session:
            for i in range(50):
                var = Variation(
                    job_id=f"all-jobs-var-{i}",
                    parent_job_id="parent-001",
                    experiment_name="benchmark_exp",
                    variation_id=f"v{i}",
                    dataset_name=f"dataset_{i % 3}",
                    preset="benchmark_preset"
                )
                session.add(var)
            session.commit()
        
        # Benchmark optimized query
        def get_all_jobs():
            return db_manager.get_all_jobs_optimized(limit=100)
        
        timing = BenchmarkHelper.time_operation(get_all_jobs, iterations=20)
        print(f"\nAll jobs query (150 items): {BenchmarkHelper.format_timing(timing)}")
        
        # Should be reasonably fast even with UNION
        assert timing["mean"] < 0.1  # Less than 100ms
    
    def test_dataset_stats_performance(self, db_manager):
        """Benchmark dataset statistics queries."""
        # Create data for specific datasets
        datasets = ["dataset_a", "dataset_b", "dataset_c"]
        for dataset in datasets:
            for i in range(100):
                exec = db_manager.create_execution(
                    job_id=f"ds-perf-{dataset}-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name=dataset,
                    preset="benchmark_preset"
                )
                if i % 3 == 0:
                    db_manager.update_execution_status(exec.job_id, ExecutionStatus.DONE)
        
        # Refresh cache for optimal performance
        db_manager.refresh_job_cache_optimized()
        
        # Benchmark dataset stats
        def get_dataset_stats():
            return db_manager.get_dataset_stats_optimized("dataset_a")
        
        timing = BenchmarkHelper.time_operation(get_dataset_stats, iterations=20)
        print(f"\nDataset stats query: {BenchmarkHelper.format_timing(timing)}")
        
        # Should be fast with cache table
        assert timing["mean"] < 0.02  # Less than 20ms


@pytest.mark.benchmark
class TestCachePerformance:
    """Benchmark cache effectiveness."""
    
    def test_cache_hit_performance(self, db_manager):
        """Test performance improvement from cache hits."""
        # Create test data
        for i in range(100):
            db_manager.create_execution(
                job_id=f"cache-hit-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="cache_dataset",
                preset="cache_preset"
            )
        
        # First call - cache miss
        start = time.perf_counter()
        stats1 = db_manager.get_statistics_cached()
        miss_time = time.perf_counter() - start
        
        # Subsequent calls - cache hits
        hit_times = []
        for _ in range(10):
            start = time.perf_counter()
            stats = db_manager.get_statistics_cached()
            hit_times.append(time.perf_counter() - start)
            assert stats == stats1  # Same result
        
        avg_hit_time = statistics.mean(hit_times)
        
        print(f"\nCache miss time: {miss_time*1000:.2f}ms")
        print(f"Cache hit time (avg): {avg_hit_time*1000:.2f}ms")
        print(f"Cache speedup: {miss_time/avg_hit_time:.1f}x")
        
        # Cache should provide significant speedup
        assert avg_hit_time < miss_time / 10  # At least 10x faster
    
    def test_cache_invalidation_overhead(self, db_manager):
        """Test overhead of cache invalidation."""
        # Populate cache
        db_manager.get_statistics_cached()
        db_manager.get_recent_jobs_cached()
        
        # Time creation with cache invalidation
        start = time.perf_counter()
        db_manager.create_execution(
            job_id="invalidation-test",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        invalidation_time = time.perf_counter() - start
        
        print(f"\nCreate with cache invalidation: {invalidation_time*1000:.2f}ms")
        
        # Should still be fast
        assert invalidation_time < 0.1  # Less than 100ms


@pytest.mark.benchmark
@pytest.mark.slow
class TestLargeScalePerformance:
    """Test performance with large datasets."""
    
    def test_large_dataset_performance(self, db_manager):
        """Test performance with 10k+ records."""
        print("\nCreating large dataset...")
        
        # Create 10k records in batches
        total_records = 10000
        batch_size = 100
        
        start_time = time.time()
        
        for batch in range(total_records // batch_size):
            batch_data = [
                {
                    "job_id": f"large-{batch}-{i}",
                    "pipeline_mode": PipelineMode.SINGLE.value,
                    "dataset_name": f"dataset_{i % 20}",
                    "preset": f"preset_{i % 10}"
                }
                for i in range(batch_size)
            ]
            db_manager.batch_create_executions(batch_data)
            
            if batch % 10 == 0:
                print(f"  Created {(batch + 1) * batch_size} records...")
        
        creation_time = time.time() - start_time
        print(f"Created {total_records} records in {creation_time:.2f}s")
        print(f"Rate: {total_records/creation_time:.0f} records/second")
        
        # Test query performance on large dataset
        
        # 1. Statistics
        start = time.perf_counter()
        stats = db_manager.get_statistics_optimized()
        stats_time = time.perf_counter() - start
        print(f"\nStatistics query on {total_records} records: {stats_time*1000:.2f}ms")
        assert stats_time < 1.0  # Less than 1 second
        
        # 2. Recent jobs
        start = time.perf_counter()
        recent = db_manager.get_recent_jobs_optimized(limit=100)
        recent_time = time.perf_counter() - start
        print(f"Recent jobs query: {recent_time*1000:.2f}ms")
        assert recent_time < 0.1  # Less than 100ms
        
        # 3. Dataset stats
        start = time.perf_counter()
        ds_stats = db_manager.get_dataset_stats_optimized("dataset_0")
        ds_time = time.perf_counter() - start
        print(f"Dataset stats query: {ds_time*1000:.2f}ms")
        assert ds_time < 0.1  # Less than 100ms
        
        # 4. Cleanup old jobs
        print("\nTesting cleanup performance...")
        start = time.perf_counter()
        # Make half the jobs "old"
        with db_manager.get_session() as session:
            session.query(Execution).filter(
                Execution.job_id.like("large-%")
            ).limit(5000).update({
                "created_at": datetime.utcnow() - timedelta(days=40)
            }, synchronize_session=False)
            session.commit()
        
        result = db_manager.cleanup_old_jobs(days=30)
        cleanup_time = time.perf_counter() - start
        print(f"Cleaned up {result['executions_deleted']} records in {cleanup_time:.2f}s")
        
        # Cleanup should be efficient
        assert cleanup_time < 5.0  # Less than 5 seconds for 5k records