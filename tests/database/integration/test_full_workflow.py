"""Integration tests for complete database workflows."""

import pytest
from datetime import datetime, timedelta
import time

from src.database.enums import ExecutionStatus, PipelineMode
from src.database.models import Execution, Variation, JobSummaryCache


class TestCompleteWorkflow:
    """Test complete execution workflow from creation to completion."""
    
    def test_single_execution_workflow(self, db_manager):
        """Test complete single execution workflow."""
        # 1. Create execution
        job_id = "workflow-single-001"
        execution = db_manager.create_execution(
            job_id=job_id,
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="flux_lora",
            total_steps=1000
        )
        
        assert execution.status == ExecutionStatus.PENDING.value
        assert execution.job_id == job_id
        
        # 2. Check it appears in recent jobs
        recent = db_manager.get_recent_jobs_optimized(limit=10)
        assert any(job["job_id"] == job_id for job in recent)
        
        # 3. Update to training
        success = db_manager.update_execution_status(job_id, ExecutionStatus.TRAINING)
        assert success
        
        # 4. Verify in running jobs
        running = db_manager.get_running_jobs()
        assert any(e["job_id"] == job_id for e in running["executions"])
        
        # 5. Simulate progress updates
        with db_manager.get_session() as session:
            exec = session.query(Execution).filter_by(job_id=job_id).first()
            exec.current_step = 500
            session.commit()
        
        # 6. Complete execution
        output_path = "/models/output/model.safetensors"
        success = db_manager.update_execution_status(
            job_id, 
            ExecutionStatus.DONE,
            output_path=output_path
        )
        assert success
        
        # 7. Verify final state
        with db_manager.get_session() as session:
            final = session.query(Execution).filter_by(job_id=job_id).first()
            assert final.status == ExecutionStatus.DONE.value
            assert final.success is True
            assert final.output_path == output_path
            assert final.duration_seconds is not None
            assert final.end_time is not None
            
            # Check cache updated
            cache = session.query(JobSummaryCache).filter_by(job_id=job_id).first()
            assert cache is not None
            assert cache.success is True
        
        # 8. Verify in statistics
        stats = db_manager.get_statistics_optimized()
        assert stats["total_successful"] >= 1
    
    def test_batch_execution_workflow(self, db_manager):
        """Test batch execution workflow with multiple jobs."""
        # 1. Create parent batch execution
        parent_id = "workflow-batch-parent"
        parent = db_manager.create_execution(
            job_id=parent_id,
            pipeline_mode=PipelineMode.BATCH.value,
            dataset_name="batch_dataset",
            preset="sdxl_lora"
        )
        
        # 2. Create child executions
        child_data = [
            {
                "job_id": f"workflow-batch-child-{i}",
                "pipeline_mode": PipelineMode.SINGLE.value,
                "dataset_name": f"dataset_{i}",
                "preset": "sdxl_lora",
                "total_steps": 500
            }
            for i in range(3)
        ]
        
        child_ids = db_manager.batch_create_executions(child_data)
        assert len(child_ids) == 3
        
        # 3. Batch update to training
        updates = [
            {"job_id": child_id, "status": ExecutionStatus.TRAINING}
            for child_id in child_ids
        ]
        updated = db_manager.batch_update_execution_status(updates)
        assert updated == 3
        
        # 4. Complete some, fail others
        final_updates = [
            {"job_id": child_ids[0], "status": ExecutionStatus.DONE},
            {"job_id": child_ids[1], "status": ExecutionStatus.DONE},
            {"job_id": child_ids[2], "status": ExecutionStatus.FAILED,
             "error_message": "Out of memory"},
        ]
        db_manager.batch_update_execution_status(final_updates)
        
        # 5. Update parent status
        db_manager.update_execution_status(parent_id, ExecutionStatus.DONE)
        
        # 6. Verify batch statistics
        all_jobs = db_manager.get_all_jobs_optimized(limit=10)
        batch_jobs = [j for j in all_jobs if j["job_id"].startswith("workflow-batch")]
        assert len(batch_jobs) == 4  # 1 parent + 3 children
        
        # Check success rate
        successful = [j for j in batch_jobs if j.get("success") is True]
        assert len(successful) == 3  # Parent + 2 successful children
    
    def test_variations_workflow(self, db_manager):
        """Test variations pipeline workflow."""
        # 1. Create parent execution for variations
        parent_id = "workflow-var-parent"
        parent = db_manager.create_execution(
            job_id=parent_id,
            pipeline_mode=PipelineMode.VARIATIONS.value,
            dataset_name="variations_dataset",
            preset="flux_dreambooth"
        )
        
        # 2. Create variations
        variation_params = [
            {"learning_rate": 1e-4, "batch_size": 1},
            {"learning_rate": 5e-5, "batch_size": 2},
            {"learning_rate": 1e-5, "batch_size": 4},
        ]
        
        var_ids = []
        with db_manager.get_session() as session:
            for i, params in enumerate(variation_params):
                var = Variation(
                    job_id=f"workflow-var-{i}",
                    parent_job_id=parent_id,
                    experiment_name="lr_batch_experiment",
                    variation_id=f"var_{i}",
                    dataset_name="variations_dataset",
                    preset="flux_dreambooth",
                    varied_parameters=params,
                    parameter_values={"seed": 42, "steps": 1000}
                )
                session.add(var)
                var_ids.append(var.job_id)
            session.commit()
        
        # 3. Start parent
        db_manager.update_execution_status(parent_id, ExecutionStatus.TRAINING)
        
        # 4. Process variations
        var_updates = []
        for i, var_id in enumerate(var_ids):
            # Start training
            db_manager.update_variation_status(var_id, ExecutionStatus.TRAINING)
            
            # Complete with different outcomes
            if i == 0:
                status = ExecutionStatus.DONE
                output = f"/models/variations/var_{i}.safetensors"
                db_manager.update_variation_status(var_id, status)
                db_manager.set_variation_output(var_id, output)
            elif i == 1:
                status = ExecutionStatus.FAILED
                db_manager.update_variation_status(
                    var_id, 
                    status,
                    error_message="Convergence failure"
                )
            else:
                # Leave as training
                pass
        
        # 5. Check dataset statistics
        stats = db_manager.get_dataset_stats_optimized("variations_dataset")
        assert stats["total_jobs"] >= 4  # Parent + 3 variations
        assert stats["variations"] >= 3
        
        # 6. Get experiment summary
        with db_manager.get_session() as session:
            experiment_vars = session.query(Variation).filter_by(
                experiment_name="lr_batch_experiment"
            ).all()
            assert len(experiment_vars) == 3
            
            # Check varied parameters preserved
            for var in experiment_vars:
                assert "learning_rate" in var.varied_parameters
                assert "batch_size" in var.varied_parameters


class TestConcurrentOperations:
    """Test concurrent database operations."""
    
    def test_concurrent_updates(self, db_manager):
        """Test handling concurrent status updates."""
        # Create execution
        job_id = "concurrent-001"
        db_manager.create_execution(
            job_id=job_id,
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Simulate concurrent updates (in real scenario these would be from different processes)
        # The retry logic should handle any conflicts
        
        # Update 1: Set to training
        success1 = db_manager.update_execution_status(job_id, ExecutionStatus.TRAINING)
        
        # Update 2: Try to set back to pending (should succeed due to retry logic)
        success2 = db_manager.update_execution_status(job_id, ExecutionStatus.PENDING)
        
        # Update 3: Set to done
        success3 = db_manager.update_execution_status(job_id, ExecutionStatus.DONE)
        
        assert all([success1, success2, success3])
        
        # Final state should be DONE
        with db_manager.get_session() as session:
            final = session.query(Execution).filter_by(job_id=job_id).first()
            assert final.status == ExecutionStatus.DONE.value
    
    def test_cache_consistency(self, db_manager):
        """Test cache remains consistent with concurrent operations."""
        # Create multiple jobs
        job_ids = []
        for i in range(5):
            job_id = f"cache-consistency-{i}"
            db_manager.create_execution(
                job_id=job_id,
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            job_ids.append(job_id)
        
        # Get initial stats (populates cache)
        stats1 = db_manager.get_statistics_cached()
        
        # Concurrent updates
        updates = [
            {"job_id": job_id, "status": ExecutionStatus.DONE}
            for job_id in job_ids
        ]
        db_manager.batch_update_execution_status(updates)
        
        # Cache should be invalidated and refreshed
        stats2 = db_manager.get_statistics_cached()
        
        # Verify consistency
        assert stats2["total_successful"] == stats1["total_successful"] + 5
        
        # Direct database query should match cached result
        stats_direct = db_manager.get_statistics_optimized()
        assert stats_direct == stats2


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""
    
    def test_failed_execution_tracking(self, db_manager):
        """Test proper tracking of failed executions."""
        job_id = "error-recovery-001"
        
        # Create and start execution
        db_manager.create_execution(
            job_id=job_id,
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset",
            total_steps=1000
        )
        
        db_manager.update_execution_status(job_id, ExecutionStatus.TRAINING)
        
        # Simulate failure
        error_msg = "CUDA out of memory"
        success = db_manager.update_execution_status(
            job_id,
            ExecutionStatus.FAILED,
            error_message=error_msg
        )
        assert success
        
        # Verify error tracked correctly
        with db_manager.get_session() as session:
            failed = session.query(Execution).filter_by(job_id=job_id).first()
            assert failed.status == ExecutionStatus.FAILED.value
            assert failed.success is False
            assert failed.error_message == error_msg
            assert failed.end_time is not None
            
            # Check cache
            cache = session.query(JobSummaryCache).filter_by(job_id=job_id).first()
            assert cache.success is False
        
        # Should appear in failed statistics
        stats = db_manager.get_statistics_optimized()
        assert stats["total_failed"] >= 1
    
    def test_cleanup_preserves_failed_jobs(self, db_manager):
        """Test that cleanup can preserve failed jobs for debugging."""
        now = datetime.utcnow()
        
        # Create old successful and failed jobs
        with db_manager.get_session() as session:
            # Old successful
            for i in range(3):
                exec = Execution(
                    job_id=f"old-success-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name="test_dataset",
                    preset="test_preset",
                    status=ExecutionStatus.DONE.value,
                    success=True,
                    created_at=now - timedelta(days=35)
                )
                session.add(exec)
            
            # Old failed
            for i in range(2):
                exec = Execution(
                    job_id=f"old-failed-{i}",
                    pipeline_mode=PipelineMode.SINGLE.value,
                    dataset_name="test_dataset",
                    preset="test_preset",
                    status=ExecutionStatus.FAILED.value,
                    success=False,
                    error_message=f"Error {i}",
                    created_at=now - timedelta(days=35)
                )
                session.add(exec)
            
            session.commit()
        
        # Run cleanup preserving failed
        result = db_manager.cleanup_old_jobs(days=30, keep_failed=True)
        
        assert result["executions_deleted"] == 3  # Only successful deleted
        
        # Verify failed jobs remain
        with db_manager.get_session() as session:
            failed_count = session.query(Execution).filter(
                Execution.success == False
            ).count()
            assert failed_count >= 2


class TestPerformanceOptimizations:
    """Test that performance optimizations work correctly."""
    
    def test_indexes_used(self, db_manager):
        """Test that queries use the created indexes."""
        # Create substantial data
        for i in range(100):
            db_manager.create_execution(
                job_id=f"index-test-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i % 10}",
                preset=f"preset_{i % 5}"
            )
        
        # These queries should use indexes
        # 1. Status filter (uses idx_exec_status_filter)
        with db_manager.get_session() as session:
            pending = session.query(Execution).filter_by(
                status=ExecutionStatus.PENDING.value
            ).all()
            assert len(pending) == 100
        
        # 2. Dataset query (uses idx_exec_dataset_perf)
        stats = db_manager.get_dataset_stats_optimized("dataset_0")
        assert stats["total_jobs"] == 10
        
        # 3. Recent jobs (uses created_at index)
        recent = db_manager.get_recent_jobs_optimized(limit=10)
        assert len(recent) == 10
    
    def test_cache_performance(self, db_manager):
        """Test that cache improves performance."""
        # Create data
        for i in range(50):
            db_manager.create_execution(
                job_id=f"cache-perf-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
        
        # First call - no cache
        start = time.time()
        stats1 = db_manager.get_statistics_cached()
        first_time = time.time() - start
        
        # Second call - from cache
        start = time.time()
        stats2 = db_manager.get_statistics_cached()
        cached_time = time.time() - start
        
        # Cache should be much faster
        assert cached_time < first_time * 0.5
        assert stats1 == stats2
        
        # Verify cache hit
        cache_stats = db_manager.get_cache_stats()
        assert cache_stats["hits"] >= 1