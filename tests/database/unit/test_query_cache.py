"""Unit tests for query caching system."""

import pytest
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock

from src.database.query_cache import QueryCache, CacheMixin
from src.database.enums import ExecutionStatus, PipelineMode


class TestQueryCache:
    """Test the QueryCache class."""
    
    def test_cache_basic_operations(self):
        """Test basic cache get/set operations."""
        cache = QueryCache(default_ttl=timedelta(seconds=1))
        
        # Test set and get
        cache.set("test_key", {"value": 42})
        result = cache.get("test_key")
        assert result == {"value": 42}
        assert cache.hits == 1
        assert cache.misses == 0
        
        # Test cache miss
        missing = cache.get("nonexistent")
        assert missing is None
        assert cache.misses == 1
    
    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = QueryCache(default_ttl=timedelta(seconds=0.1))
        
        # Set value
        cache.set("expire_test", "value")
        
        # Should be available immediately
        assert cache.get("expire_test") == "value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("expire_test") is None
        assert "expire_test" not in cache._cache
    
    def test_cache_custom_ttl(self):
        """Test setting custom TTL per entry."""
        cache = QueryCache(default_ttl=timedelta(seconds=10))
        
        # Set with custom short TTL
        cache.set("custom_ttl", "value", ttl=timedelta(seconds=0.1))
        
        # Should exist
        assert cache.get("custom_ttl") == "value"
        
        # Wait for custom TTL
        time.sleep(0.2)
        
        # Should be expired despite longer default TTL
        assert cache.get("custom_ttl") is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = QueryCache()
        
        # Set multiple values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("other_key", "value3")
        
        # Invalidate by pattern
        cache.invalidate("key")
        
        # Pattern-matched keys should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        
        # Other key should remain
        assert cache.get("other_key") == "value3"
        
        # Invalidate all
        cache.invalidate()
        assert cache.get("other_key") is None
        assert len(cache._cache) == 0
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = QueryCache()
        
        # Generate some activity
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss
        cache.get("missing2")  # Miss
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["total_requests"] == 4
        assert stats["hit_rate"] == 50.0


class TestCacheMixin:
    """Test the CacheMixin functionality."""
    
    def test_statistics_caching(self, db_manager):
        """Test that get_statistics_cached uses cache."""
        # Create some test data
        for i in range(5):
            db_manager.create_execution(
                job_id=f"stats-cache-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
        
        # First call - cache miss
        stats1 = db_manager.get_statistics_cached()
        cache_stats1 = db_manager.get_cache_stats()
        assert cache_stats1["misses"] == 1
        assert cache_stats1["hits"] == 0
        
        # Second call - cache hit
        stats2 = db_manager.get_statistics_cached()
        cache_stats2 = db_manager.get_cache_stats()
        assert cache_stats2["hits"] == 1
        assert stats1 == stats2  # Same result
        
        # Verify actual method not called again
        with patch.object(db_manager, 'get_statistics') as mock_get_stats:
            stats3 = db_manager.get_statistics_cached()
            mock_get_stats.assert_not_called()
            assert stats3 == stats1
    
    def test_dataset_stats_caching(self, db_manager):
        """Test dataset statistics caching."""
        # Create test data
        datasets = ["dataset_a", "dataset_b"]
        for i, dataset in enumerate(datasets * 3):
            db_manager.create_execution(
                job_id=f"ds-cache-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=dataset,
                preset="test_preset"
            )
        
        # Get stats for dataset_a
        stats_a1 = db_manager.get_dataset_stats_cached("dataset_a")
        
        # Should be cached on second call
        with patch.object(db_manager, 'get_dataset_stats') as mock:
            mock.return_value = {"mocked": True}
            stats_a2 = db_manager.get_dataset_stats_cached("dataset_a")
            mock.assert_not_called()  # Should use cache
            assert stats_a2 == stats_a1
        
        # Different dataset should not use cache
        stats_b = db_manager.get_dataset_stats_cached("dataset_b")
        assert stats_b != stats_a1
    
    def test_recent_jobs_caching(self, db_manager):
        """Test recent jobs caching with short TTL."""
        # Create test jobs
        for i in range(5):
            db_manager.create_execution(
                job_id=f"recent-cache-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
        
        # First call
        jobs1 = db_manager.get_recent_jobs_cached(limit=5)
        assert len(jobs1) == 5
        
        # Second call should use cache
        with patch.object(db_manager, 'get_recent_jobs_optimized') as mock:
            jobs2 = db_manager.get_recent_jobs_cached(limit=5)
            mock.assert_not_called()
            assert jobs2 == jobs1
        
        # Different limit should not use cache
        jobs3 = db_manager.get_recent_jobs_cached(limit=3)
        assert len(jobs3) == 3
    
    def test_cache_invalidation_on_create(self, db_manager):
        """Test that cache is invalidated on data creation."""
        # Get initial statistics (populates cache)
        stats1 = db_manager.get_statistics_cached()
        total_before = stats1["total_executions"]
        
        # Create new execution
        db_manager.create_execution(
            job_id="invalidate-test-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Statistics should be fresh (cache invalidated)
        stats2 = db_manager.get_statistics_cached()
        assert stats2["total_executions"] == total_before + 1
        
        # Check cache was actually invalidated
        cache_stats = db_manager.get_cache_stats()
        # Should have 2 misses (initial + after invalidation)
        assert cache_stats["misses"] >= 2
    
    def test_cache_invalidation_on_update(self, db_manager):
        """Test that cache is invalidated on data updates."""
        # Create execution
        execution = db_manager.create_execution(
            job_id="update-invalidate-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Get statistics (cache populated)
        stats1 = db_manager.get_statistics_cached()
        
        # Update status
        db_manager.update_execution_status(
            execution.job_id,
            ExecutionStatus.DONE
        )
        
        # Statistics should reflect update
        stats2 = db_manager.get_statistics_cached()
        done_count = stats2.get("executions_by_status", {}).get(
            ExecutionStatus.DONE.value, 0
        )
        assert done_count > 0
    
    def test_cache_invalidation_on_batch_update(self, db_manager):
        """Test cache invalidation with batch updates."""
        # Create multiple executions
        job_ids = []
        for i in range(5):
            execution = db_manager.create_execution(
                job_id=f"batch-inv-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            job_ids.append(execution.job_id)
        
        # Cache statistics
        stats1 = db_manager.get_statistics_cached()
        
        # Batch update
        updates = [
            {"job_id": job_id, "status": ExecutionStatus.DONE}
            for job_id in job_ids
        ]
        db_manager.batch_update_execution_status(updates)
        
        # Cache should be invalidated
        stats2 = db_manager.get_statistics_cached()
        done_count = stats2.get("executions_by_status", {}).get(
            ExecutionStatus.DONE.value, 0
        )
        assert done_count >= 5


class TestCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_make_cache_key(self, db_manager):
        """Test cache key generation."""
        # Simple key
        key1 = db_manager._make_cache_key("method_name", "arg1", "arg2")
        assert "method_name" in key1
        assert "arg1" in key1
        assert "arg2" in key1
        
        # With kwargs
        key2 = db_manager._make_cache_key(
            "method", 
            "arg1",
            param1="value1",
            param2="value2"
        )
        assert "param1=value1" in key2
        assert "param2=value2" in key2
        
        # Long key should be hashed
        long_args = ["x" * 50 for _ in range(10)]
        key3 = db_manager._make_cache_key("method", *long_args)
        assert len(key3) == 32  # MD5 hash length
    
    def test_cache_key_consistency(self, db_manager):
        """Test that same arguments produce same cache key."""
        key1 = db_manager._make_cache_key("method", "arg1", param="value")
        key2 = db_manager._make_cache_key("method", "arg1", param="value")
        assert key1 == key2
        
        # Different order of kwargs should still match
        key3 = db_manager._make_cache_key("method", param="value", arg="arg1")
        key4 = db_manager._make_cache_key("method", arg="arg1", param="value")
        # Keys should differ from key1/key2 due to different args


class TestCachePerformance:
    """Test cache performance benefits."""
    
    def test_cache_performance_improvement(self, db_manager):
        """Test that cache improves query performance."""
        import time
        
        # Create substantial test data
        for i in range(50):
            db_manager.create_execution(
                job_id=f"perf-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i % 5}",
                preset="test_preset"
            )
        
        # Time uncached call
        start = time.time()
        stats1 = db_manager.get_statistics()
        uncached_time = time.time() - start
        
        # Time cached call
        start = time.time()
        stats2 = db_manager.get_statistics_cached()
        first_cached_time = time.time() - start
        
        # Time second cached call (should be very fast)
        start = time.time()
        stats3 = db_manager.get_statistics_cached()
        second_cached_time = time.time() - start
        
        # Cache hit should be much faster
        assert second_cached_time < uncached_time * 0.1  # At least 10x faster
        assert stats1 == stats2 == stats3  # Same results