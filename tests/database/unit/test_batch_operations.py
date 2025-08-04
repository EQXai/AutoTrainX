"""Unit tests for batch operations."""

import pytest
from datetime import datetime

from src.database.enums import ExecutionStatus, PipelineMode
from src.database.models import Execution, Variation, JobSummaryCache


class TestBatchExecutionOperations:
    """Test batch operations for executions."""
    
    def test_batch_create_executions(self, db_manager, multiple_executions_data):
        """Test creating multiple executions in batch."""
        job_ids = db_manager.batch_create_executions(multiple_executions_data)
        
        assert len(job_ids) == len(multiple_executions_data)
        
        # Verify all were created
        with db_manager.get_session() as session:
            created = session.query(Execution).filter(
                Execution.job_id.in_(job_ids)
            ).all()
            assert len(created) == len(multiple_executions_data)
            
            # Check cache was updated
            cache_entries = session.query(JobSummaryCache).filter(
                JobSummaryCache.job_id.in_(job_ids)
            ).all()
            assert len(cache_entries) == len(job_ids)
    
    def test_batch_update_execution_status(self, db_manager):
        """Test batch updating execution statuses."""
        # Create test executions
        job_ids = []
        for i in range(5):
            execution = db_manager.create_execution(
                job_id=f"batch-update-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            job_ids.append(execution.job_id)
        
        # Prepare batch updates
        updates = [
            {"job_id": job_ids[0], "status": ExecutionStatus.TRAINING},
            {"job_id": job_ids[1], "status": ExecutionStatus.TRAINING},
            {"job_id": job_ids[2], "status": ExecutionStatus.DONE},
            {"job_id": job_ids[3], "status": ExecutionStatus.FAILED, 
             "error_message": "Test error"},
            {"job_id": job_ids[4], "status": ExecutionStatus.DONE},
        ]
        
        # Perform batch update
        updated_count = db_manager.batch_update_execution_status(updates)
        assert updated_count == 5
        
        # Verify updates
        with db_manager.get_session() as session:
            # Check training status
            training = session.query(Execution).filter(
                Execution.status == ExecutionStatus.TRAINING.value
            ).all()
            assert len(training) == 2
            
            # Check completed
            done = session.query(Execution).filter(
                Execution.status == ExecutionStatus.DONE.value
            ).all()
            assert len(done) == 2
            assert all(e.success is True for e in done)
            
            # Check failed
            failed = session.query(Execution).filter(
                Execution.status == ExecutionStatus.FAILED.value
            ).first()
            assert failed is not None
            assert failed.success is False
            assert failed.error_message == "Test error"
    
    def test_batch_update_performance(self, db_manager):
        """Test that batch updates are more efficient than individual updates."""
        import time
        
        # Create many executions
        job_ids = []
        for i in range(50):
            execution = db_manager.create_execution(
                job_id=f"perf-test-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            job_ids.append(execution.job_id)
        
        # Time individual updates
        start_individual = time.time()
        for i in range(25):
            db_manager.update_execution_status(
                job_ids[i], 
                ExecutionStatus.DONE
            )
        individual_time = time.time() - start_individual
        
        # Time batch update
        updates = [
            {"job_id": job_ids[i], "status": ExecutionStatus.DONE}
            for i in range(25, 50)
        ]
        start_batch = time.time()
        db_manager.batch_update_execution_status(updates)
        batch_time = time.time() - start_batch
        
        # Batch should be significantly faster
        assert batch_time < individual_time * 0.5  # At least 2x faster
        
        # Verify all updates succeeded
        with db_manager.get_session() as session:
            completed = session.query(Execution).filter(
                Execution.status == ExecutionStatus.DONE.value
            ).count()
            assert completed == 50


class TestBatchVariationOperations:
    """Test batch operations for variations."""
    
    def test_batch_update_variation_status(self, db_manager):
        """Test batch updating variation statuses."""
        # Create parent execution
        parent = db_manager.create_execution(
            job_id="parent-batch-001",
            pipeline_mode=PipelineMode.VARIATIONS.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Create variations
        var_ids = []
        for i in range(5):
            with db_manager.get_session() as session:
                variation = Variation(
                    job_id=f"var-batch-{i}",
                    parent_job_id=parent.job_id,
                    experiment_name="test_exp",
                    variation_id=f"v{i}",
                    dataset_name="test_dataset",
                    preset="test_preset",
                    status=ExecutionStatus.PENDING.value,
                    varied_parameters={"param": i}
                )
                session.add(variation)
                session.commit()
                var_ids.append(variation.job_id)
        
        # Batch update
        updates = [
            {"job_id": var_ids[0], "status": ExecutionStatus.TRAINING},
            {"job_id": var_ids[1], "status": ExecutionStatus.DONE},
            {"job_id": var_ids[2], "status": ExecutionStatus.FAILED,
             "error_message": "Variation failed"},
            {"job_id": var_ids[3], "status": ExecutionStatus.DONE},
            {"job_id": var_ids[4], "status": ExecutionStatus.TRAINING},
        ]
        
        updated_count = db_manager.batch_update_variation_status(updates)
        assert updated_count == 5
        
        # Verify
        with db_manager.get_session() as session:
            training = session.query(Variation).filter(
                Variation.status == ExecutionStatus.TRAINING.value
            ).count()
            assert training == 2
            
            done = session.query(Variation).filter(
                Variation.status == ExecutionStatus.DONE.value
            ).count()
            assert done == 2
            
            failed = session.query(Variation).filter(
                Variation.status == ExecutionStatus.FAILED.value
            ).first()
            assert failed is not None
            assert failed.error_message == "Variation failed"


class TestBatchCacheOperations:
    """Test batch cache update operations."""
    
    def test_refresh_job_cache_optimized(self, db_manager):
        """Test optimized cache refresh."""
        # Create mixed executions and variations
        for i in range(10):
            db_manager.create_execution(
                job_id=f"cache-exec-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=f"dataset_{i % 3}",
                preset="test_preset"
            )
        
        # Create variations
        with db_manager.get_session() as session:
            for i in range(5):
                variation = Variation(
                    job_id=f"cache-var-{i}",
                    parent_job_id="parent-001",
                    experiment_name="test_exp",
                    variation_id=f"v{i}",
                    dataset_name=f"dataset_{i % 2}",
                    preset="test_preset",
                    status=ExecutionStatus.DONE.value,
                    success=True
                )
                session.add(variation)
            session.commit()
        
        # Clear cache
        with db_manager.get_session() as session:
            session.query(JobSummaryCache).delete()
            session.commit()
        
        # Refresh cache
        db_manager.refresh_job_cache_optimized()
        
        # Verify cache rebuilt
        with db_manager.get_session() as session:
            cache_count = session.query(JobSummaryCache).count()
            assert cache_count == 15  # 10 executions + 5 variations
            
            exec_cache = session.query(JobSummaryCache).filter_by(
                job_type="execution"
            ).count()
            assert exec_cache == 10
            
            var_cache = session.query(JobSummaryCache).filter_by(
                job_type="variation"
            ).count()
            assert var_cache == 5
    
    def test_batch_cache_update_postgresql_upsert(self, db_manager):
        """Test PostgreSQL UPSERT functionality in cache updates."""
        if db_manager.config.db_type != 'postgresql':
            pytest.skip("PostgreSQL-specific test")
        
        # Create initial execution
        execution = db_manager.create_execution(
            job_id="upsert-test-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Update multiple times
        for status in [ExecutionStatus.TRAINING, ExecutionStatus.DONE]:
            db_manager.update_execution_status(execution.job_id, status)
        
        # Cache should have only one entry (upserted)
        with db_manager.get_session() as session:
            cache_entries = session.query(JobSummaryCache).filter_by(
                job_id="upsert-test-001"
            ).all()
            assert len(cache_entries) == 1
            assert cache_entries[0].status == ExecutionStatus.DONE.value


class TestBatchErrorHandling:
    """Test error handling in batch operations."""
    
    def test_batch_update_with_invalid_job_ids(self, db_manager):
        """Test batch update with some invalid job IDs."""
        # Create some valid executions
        valid_ids = []
        for i in range(3):
            execution = db_manager.create_execution(
                job_id=f"valid-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            valid_ids.append(execution.job_id)
        
        # Mix valid and invalid IDs
        updates = [
            {"job_id": valid_ids[0], "status": ExecutionStatus.DONE},
            {"job_id": "invalid-001", "status": ExecutionStatus.DONE},  # Invalid
            {"job_id": valid_ids[1], "status": ExecutionStatus.FAILED},
            {"job_id": "invalid-002", "status": ExecutionStatus.DONE},  # Invalid
            {"job_id": valid_ids[2], "status": ExecutionStatus.DONE},
        ]
        
        # Should update only valid ones
        updated_count = db_manager.batch_update_execution_status(updates)
        assert updated_count == 3  # Only valid ones
        
        # Verify valid ones were updated
        with db_manager.get_session() as session:
            done = session.query(Execution).filter(
                Execution.status == ExecutionStatus.DONE.value
            ).count()
            assert done == 2
            
            failed = session.query(Execution).filter(
                Execution.status == ExecutionStatus.FAILED.value
            ).count()
            assert failed == 1
    
    def test_batch_create_rollback_on_error(self, db_manager):
        """Test that batch create rolls back on error."""
        # Create data with duplicate job_id
        duplicate_data = [
            {
                "job_id": "duplicate-001",
                "pipeline_mode": PipelineMode.SINGLE.value,
                "dataset_name": "test_dataset",
                "preset": "test_preset"
            },
            {
                "job_id": "duplicate-001",  # Duplicate!
                "pipeline_mode": PipelineMode.SINGLE.value,
                "dataset_name": "test_dataset",
                "preset": "test_preset"
            }
        ]
        
        # Should raise error and rollback
        with pytest.raises(Exception):
            db_manager.batch_create_executions(duplicate_data)
        
        # Nothing should be created
        with db_manager.get_session() as session:
            count = session.query(Execution).filter(
                Execution.job_id == "duplicate-001"
            ).count()
            assert count == 0