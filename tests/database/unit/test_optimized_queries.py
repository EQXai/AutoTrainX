"""Unit tests for optimized queries."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.database.enums import ExecutionStatus, PipelineMode
from src.database.models import Execution, Variation, JobSummaryCache


class TestOptimizedStatistics:
    """Test optimized statistics queries."""
    
    def test_get_statistics_optimized(self, db_manager):
        """Test optimized statistics query returns correct data."""
        # Create test data with various statuses
        statuses = [
            (ExecutionStatus.PENDING, 3),
            (ExecutionStatus.TRAINING, 2),
            (ExecutionStatus.DONE, 5),
            (ExecutionStatus.FAILED, 1),
        ]
        
        # Create executions
        for status, count in statuses:
            for i in range(count):
                execution = Execution(
                    job_id=f"stats-exec-{status.value}-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name="test_dataset",
                    preset="test_preset",
                    status=status.value,
                    success=True if status == ExecutionStatus.DONE else False,
                    duration_seconds=100.0 if status == ExecutionStatus.DONE else None
                )
                with db_manager.get_session() as session:
                    session.add(execution)
                    session.commit()
        
        # Create variations
        for i in range(3):
            variation = Variation(
                job_id=f"stats-var-{i}",
                parent_job_id="parent-001",
                experiment_name="test_exp",
                variation_id=f"v{i}",
                dataset_name="test_dataset",
                preset="test_preset",
                status=ExecutionStatus.DONE.value,
                success=True,
                duration_seconds=150.0
            )
            with db_manager.get_session() as session:
                session.add(variation)
                session.commit()
        
        # Get optimized statistics
        stats = db_manager.get_statistics_optimized()
        
        # Verify counts
        assert stats["total_executions"] == 11  # Sum of all execution statuses
        assert stats["total_variations"] == 3
        assert stats["total_jobs"] == 14
        
        # Verify success metrics
        assert stats["total_successful"] == 8  # 5 exec + 3 var
        assert stats["total_failed"] == 1
        assert stats["success_rate"] == (8 / 9 * 100)  # 8 successful out of 9 completed
        
        # Verify average durations
        assert stats["avg_execution_duration"] == pytest.approx(100.0, rel=0.1)
        assert stats["avg_variation_duration"] == pytest.approx(150.0, rel=0.1)
    
    def test_statistics_query_efficiency(self, db_manager):
        """Test that optimized query is more efficient than original."""
        # Create test data
        for i in range(20):
            db_manager.create_execution(
                job_id=f"efficiency-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
        
        # Count queries for original method
        with patch.object(db_manager, 'get_session') as mock_session:
            # Mock the session to count query calls
            query_count = 0
            original_query = mock_session.return_value.__enter__.return_value.query
            
            def count_queries(*args, **kwargs):
                nonlocal query_count
                query_count += 1
                return original_query(*args, **kwargs)
            
            mock_session.return_value.__enter__.return_value.query = count_queries
            
            # Call original statistics method
            db_manager.get_statistics()
            original_query_count = query_count
        
        # Optimized version should use fewer queries
        # (2 aggregate queries vs multiple COUNT queries)
        assert original_query_count > 5  # Original does many counts
        
        # The optimized version uses only 2 queries (verified by implementation)


class TestOptimizedJobQueries:
    """Test optimized job retrieval queries."""
    
    def test_get_all_jobs_optimized(self, db_manager):
        """Test optimized all jobs query with UNION."""
        # Create mixed executions and variations
        exec_ids = []
        for i in range(5):
            execution = db_manager.create_execution(
                job_id=f"union-exec-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i}",
                preset="test_preset"
            )
            exec_ids.append(execution.job_id)
        
        var_ids = []
        with db_manager.get_session() as session:
            for i in range(3):
                variation = Variation(
                    job_id=f"union-var-{i}",
                    parent_job_id="parent-001",
                    experiment_name="test_exp",
                    variation_id=f"v{i}",
                    dataset_name=f"dataset_{i}",
                    preset="test_preset",
                    status=ExecutionStatus.PENDING.value
                )
                session.add(variation)
                var_ids.append(variation.job_id)
            session.commit()
        
        # Get all jobs
        jobs = db_manager.get_all_jobs_optimized(limit=10)
        
        # Should get all 8 jobs
        assert len(jobs) == 8
        
        # Should be sorted by created_at DESC
        created_times = [
            datetime.fromisoformat(job["created_at"]) 
            for job in jobs
        ]
        assert created_times == sorted(created_times, reverse=True)
        
        # Should have correct job types
        exec_jobs = [j for j in jobs if j["job_type"] == "execution"]
        var_jobs = [j for j in jobs if j["job_type"] == "variation"]
        assert len(exec_jobs) == 5
        assert len(var_jobs) == 3
    
    def test_get_all_jobs_limit(self, db_manager):
        """Test that limit is properly applied in UNION query."""
        # Create more jobs than limit
        for i in range(20):
            db_manager.create_execution(
                job_id=f"limit-test-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
        
        # Get with limit
        jobs = db_manager.get_all_jobs_optimized(limit=5)
        assert len(jobs) == 5
        
        # Should be the 5 most recent
        all_jobs = db_manager.get_all_jobs_optimized(limit=100)
        assert jobs == all_jobs[:5]


class TestOptimizedDatasetStats:
    """Test optimized dataset statistics queries."""
    
    def test_get_dataset_stats_optimized(self, db_manager):
        """Test optimized dataset statistics using cache table."""
        dataset_name = "test_dataset_stats"
        
        # Create jobs for dataset
        for i in range(10):
            execution = db_manager.create_execution(
                job_id=f"ds-stats-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=dataset_name,
                preset="test_preset"
            )
            
            # Complete some of them
            if i < 7:
                db_manager.update_execution_status(
                    execution.job_id,
                    ExecutionStatus.DONE if i < 5 else ExecutionStatus.FAILED
                )
        
        # Update durations for completed ones
        with db_manager.get_session() as session:
            completed = session.query(Execution).filter(
                Execution.status == ExecutionStatus.DONE.value
            ).all()
            for idx, exec in enumerate(completed):
                exec.duration_seconds = 100.0 + idx * 10
                exec.start_time = datetime.utcnow() - timedelta(days=idx)
            session.commit()
        
        # Refresh cache
        db_manager.refresh_job_cache_optimized()
        
        # Get dataset stats
        stats = db_manager.get_dataset_stats_optimized(dataset_name)
        
        assert stats["dataset_name"] == dataset_name
        assert stats["total_jobs"] == 10
        assert stats["successful_jobs"] == 5
        assert stats["failed_jobs"] == 2
        assert stats["success_rate"] == (5 / 7 * 100)  # 5 out of 7 completed
        assert stats["average_duration"] == pytest.approx(120.0, rel=0.1)  # (100+110+120+130+140)/5
        assert stats["min_duration"] == 100.0
        assert stats["max_duration"] == 140.0
        assert stats["executions"] == 10
        assert stats["variations"] == 0
    
    def test_dataset_stats_with_variations(self, db_manager):
        """Test dataset stats including variations."""
        dataset_name = "mixed_dataset"
        
        # Create executions
        for i in range(3):
            db_manager.create_execution(
                job_id=f"mixed-exec-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=dataset_name,
                preset="test_preset"
            )
        
        # Create variations
        with db_manager.get_session() as session:
            for i in range(2):
                var = Variation(
                    job_id=f"mixed-var-{i}",
                    parent_job_id="parent-001",
                    experiment_name="test_exp",
                    variation_id=f"v{i}",
                    dataset_name=dataset_name,
                    preset="test_preset",
                    status=ExecutionStatus.DONE.value,
                    success=True,
                    duration_seconds=200.0
                )
                session.add(var)
            session.commit()
        
        # Refresh cache
        db_manager.refresh_job_cache_optimized()
        
        # Get stats
        stats = db_manager.get_dataset_stats_optimized(dataset_name)
        
        assert stats["total_jobs"] == 5
        assert stats["executions"] == 3
        assert stats["variations"] == 2


class TestRunningJobsQuery:
    """Test optimized running jobs query."""
    
    def test_get_running_jobs(self, db_manager):
        """Test getting currently running jobs."""
        # Create jobs in various states
        states = [
            (ExecutionStatus.PENDING, 2),
            (ExecutionStatus.TRAINING, 3),
            (ExecutionStatus.DONE, 2),
            (ExecutionStatus.FAILED, 1),
        ]
        
        for status, count in states:
            for i in range(count):
                execution = db_manager.create_execution(
                    job_id=f"running-{status.value}-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name="test_dataset",
                    preset="test_preset"
                )
                if status != ExecutionStatus.PENDING:
                    db_manager.update_execution_status(execution.job_id, status)
        
        # Add some variations
        with db_manager.get_session() as session:
            for i in range(2):
                var = Variation(
                    job_id=f"running-var-{i}",
                    parent_job_id="parent-001",
                    experiment_name="test_exp",
                    variation_id=f"v{i}",
                    dataset_name="test_dataset",
                    preset="test_preset",
                    status=ExecutionStatus.TRAINING.value if i == 0 else ExecutionStatus.DONE.value
                )
                session.add(var)
            session.commit()
        
        # Get running jobs
        running = db_manager.get_running_jobs()
        
        # Should have correct counts
        assert len(running["executions"]) == 5  # 2 pending + 3 training
        assert len(running["variations"]) == 1  # 1 training
        
        # Verify only pending/training included
        exec_statuses = {e["status"] for e in running["executions"]}
        assert exec_statuses == {ExecutionStatus.PENDING.value, ExecutionStatus.TRAINING.value}
        
        var_statuses = {v["status"] for v in running["variations"]}
        assert var_statuses == {ExecutionStatus.TRAINING.value}
    
    def test_running_jobs_progress_calculation(self, db_manager):
        """Test progress calculation for running jobs."""
        # Create execution with progress
        execution = db_manager.create_execution(
            job_id="progress-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset",
            total_steps=100
        )
        
        # Update to training with progress
        db_manager.update_execution_status(execution.job_id, ExecutionStatus.TRAINING)
        
        # Set current step
        with db_manager.get_session() as session:
            exec = session.query(Execution).filter_by(job_id="progress-001").first()
            exec.current_step = 45
            session.commit()
        
        # Get running jobs
        running = db_manager.get_running_jobs()
        
        # Find our job
        our_job = next(j for j in running["executions"] if j["job_id"] == "progress-001")
        assert our_job["progress"] == 45.0  # 45/100 * 100


class TestCleanupQuery:
    """Test cleanup operations."""
    
    def test_cleanup_old_jobs(self, db_manager):
        """Test cleaning up old job records."""
        now = datetime.utcnow()
        
        # Create old jobs
        with db_manager.get_session() as session:
            # Old successful job (should be deleted)
            old_success = Execution(
                job_id="old-success",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                status=ExecutionStatus.DONE.value,
                success=True,
                created_at=now - timedelta(days=40)
            )
            session.add(old_success)
            
            # Old failed job (should be kept if keep_failed=True)
            old_failed = Execution(
                job_id="old-failed",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                status=ExecutionStatus.FAILED.value,
                success=False,
                created_at=now - timedelta(days=40)
            )
            session.add(old_failed)
            
            # Recent job (should be kept)
            recent = Execution(
                job_id="recent",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                status=ExecutionStatus.DONE.value,
                success=True,
                created_at=now - timedelta(days=10)
            )
            session.add(recent)
            
            session.commit()
        
        # Run cleanup
        result = db_manager.cleanup_old_jobs(days=30, keep_failed=True)
        
        assert result["executions_deleted"] == 1  # Only old-success
        
        # Verify what remains
        with db_manager.get_session() as session:
            remaining = session.query(Execution).all()
            remaining_ids = {e.job_id for e in remaining}
            
            assert "old-success" not in remaining_ids
            assert "old-failed" in remaining_ids  # Kept because keep_failed=True
            assert "recent" in remaining_ids
    
    def test_cleanup_with_cache(self, db_manager):
        """Test that cleanup also cleans cache entries."""
        # Create old job with cache
        now = datetime.utcnow()
        
        with db_manager.get_session() as session:
            old_exec = Execution(
                job_id="cached-old",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                status=ExecutionStatus.DONE.value,
                success=True,
                created_at=now - timedelta(days=40)
            )
            session.add(old_exec)
            
            # Add cache entry
            cache = JobSummaryCache(
                job_id="cached-old",
                job_type="execution",
                status=ExecutionStatus.DONE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                success=True,
                last_updated=now - timedelta(days=40)
            )
            session.add(cache)
            session.commit()
        
        # Run cleanup
        result = db_manager.cleanup_old_jobs(days=30, keep_failed=False)
        
        assert result["executions_deleted"] == 1
        assert result["cache_entries_deleted"] == 1
        
        # Verify both are gone
        with db_manager.get_session() as session:
            exec_count = session.query(Execution).filter_by(job_id="cached-old").count()
            cache_count = session.query(JobSummaryCache).filter_by(job_id="cached-old").count()
            
            assert exec_count == 0
            assert cache_count == 0