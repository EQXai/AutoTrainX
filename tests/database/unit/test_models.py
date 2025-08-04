"""Unit tests for database models."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.database.models import Execution, Variation, JobSummaryCache
from src.database.enums import ExecutionStatus, PipelineMode


class TestExecutionModel:
    """Test Execution model."""
    
    def test_execution_creation(self, db_manager):
        """Test creating an execution record."""
        execution = Execution(
            job_id="test-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset",
            status=ExecutionStatus.PENDING.value,
            total_steps=100
        )
        
        with db_manager.get_session() as session:
            session.add(execution)
            session.commit()
            
            # Verify
            saved = session.query(Execution).filter_by(job_id="test-001").first()
            assert saved is not None
            assert saved.dataset_name == "test_dataset"
            assert saved.status == ExecutionStatus.PENDING.value
            assert saved.total_steps == 100
            assert saved.created_at is not None
    
    def test_execution_to_dict(self):
        """Test execution to_dict method."""
        execution = Execution(
            job_id="test-002",
            pipeline_mode=PipelineMode.BATCH.value,
            dataset_name="test_dataset",
            preset="test_preset",
            status=ExecutionStatus.DONE.value,
            success=True,
            duration_seconds=123.45
        )
        
        result = execution.to_dict()
        
        assert result["job_id"] == "test-002"
        assert result["pipeline_mode"] == PipelineMode.BATCH.value
        assert result["status"] == ExecutionStatus.DONE.value
        assert result["success"] is True
        assert result["duration_seconds"] == 123.45
    
    def test_execution_status_transitions(self, db_manager):
        """Test execution status transitions."""
        execution = db_manager.create_execution(
            job_id="test-003",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        assert execution.status == ExecutionStatus.PENDING.value
        
        # Update to training
        success = db_manager.update_execution_status(
            "test-003", 
            ExecutionStatus.TRAINING
        )
        assert success
        
        with db_manager.get_session() as session:
            updated = session.query(Execution).filter_by(job_id="test-003").first()
            assert updated.status == ExecutionStatus.TRAINING.value
            
        # Update to done
        success = db_manager.update_execution_status(
            "test-003",
            ExecutionStatus.DONE
        )
        assert success
        
        with db_manager.get_session() as session:
            final = session.query(Execution).filter_by(job_id="test-003").first()
            assert final.status == ExecutionStatus.DONE.value
            assert final.success is True
            assert final.end_time is not None
            assert final.duration_seconds is not None


class TestVariationModel:
    """Test Variation model."""
    
    def test_variation_creation(self, db_manager):
        """Test creating a variation record."""
        variation = Variation(
            job_id="var-001",
            parent_job_id="parent-001",
            experiment_name="test_exp",
            variation_id="v1",
            dataset_name="test_dataset",
            preset="test_preset",
            status=ExecutionStatus.PENDING.value,
            varied_parameters={"lr": 0.001},
            parameter_values={"batch_size": 32}
        )
        
        with db_manager.get_session() as session:
            session.add(variation)
            session.commit()
            
            saved = session.query(Variation).filter_by(job_id="var-001").first()
            assert saved is not None
            assert saved.experiment_name == "test_exp"
            assert saved.varied_parameters == {"lr": 0.001}
            assert saved.parameter_values == {"batch_size": 32}
    
    def test_variation_json_fields(self, db_manager):
        """Test JSON field handling in variations."""
        complex_params = {
            "network": {
                "layers": [128, 64, 32],
                "activation": "relu"
            },
            "training": {
                "optimizer": "adam",
                "schedule": {"initial": 0.001, "decay": 0.95}
            }
        }
        
        variation = Variation(
            job_id="var-002",
            parent_job_id="parent-002",
            experiment_name="complex_exp",
            variation_id="v2",
            dataset_name="test_dataset",
            preset="test_preset",
            varied_parameters=complex_params,
            parameter_values={"seed": 42}
        )
        
        with db_manager.get_session() as session:
            session.add(variation)
            session.commit()
            
            saved = session.query(Variation).filter_by(job_id="var-002").first()
            assert saved.varied_parameters == complex_params
            assert saved.varied_parameters["network"]["layers"] == [128, 64, 32]


class TestJobSummaryCache:
    """Test JobSummaryCache model."""
    
    def test_cache_creation(self, db_manager):
        """Test creating cache entries."""
        cache_entry = JobSummaryCache(
            job_id="cache-001",
            job_type="execution",
            status=ExecutionStatus.DONE.value,
            dataset_name="test_dataset",
            preset="test_preset",
            success=True,
            duration_seconds=100.5
        )
        
        with db_manager.get_session() as session:
            session.add(cache_entry)
            session.commit()
            
            saved = session.query(JobSummaryCache).filter_by(
                job_id="cache-001"
            ).first()
            assert saved is not None
            assert saved.job_type == "execution"
            assert saved.success is True
            assert saved.last_updated is not None
    
    def test_cache_update(self, db_manager):
        """Test updating cache entries."""
        # Create initial entry
        db_manager.create_execution(
            job_id="cache-002",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Cache should be updated automatically
        with db_manager.get_session() as session:
            cache = session.query(JobSummaryCache).filter_by(
                job_id="cache-002"
            ).first()
            assert cache is not None
            assert cache.status == ExecutionStatus.PENDING.value
            
        # Update status
        db_manager.update_execution_status("cache-002", ExecutionStatus.DONE)
        
        # Cache should reflect the update
        with db_manager.get_session() as session:
            updated_cache = session.query(JobSummaryCache).filter_by(
                job_id="cache-002"
            ).first()
            assert updated_cache.status == ExecutionStatus.DONE.value
            assert updated_cache.success is True


class TestModelConstraints:
    """Test model constraints and validations."""
    
    def test_unique_job_id_constraint(self, db_manager):
        """Test that job_id must be unique."""
        # Create first execution
        db_manager.create_execution(
            job_id="unique-001",
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name="test_dataset",
            preset="test_preset"
        )
        
        # Try to create duplicate
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_manager.create_execution(
                job_id="unique-001",  # Same ID
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
    
    def test_required_fields(self, db_manager):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            with db_manager.get_session() as session:
                # Missing required fields
                execution = Execution(
                    job_id="invalid-001"
                    # Missing pipeline_mode, dataset_name, preset
                )
                session.add(execution)
                session.commit()


class TestModelQueries:
    """Test common model query patterns."""
    
    def test_filter_by_status(self, db_manager):
        """Test filtering by status."""
        # Create executions with different statuses
        statuses = [
            ExecutionStatus.PENDING,
            ExecutionStatus.TRAINING,
            ExecutionStatus.DONE,
            ExecutionStatus.FAILED
        ]
        
        for i, status in enumerate(statuses):
            execution = Execution(
                job_id=f"status-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset",
                status=status.value
            )
            with db_manager.get_session() as session:
                session.add(execution)
                session.commit()
        
        # Query by status
        with db_manager.get_session() as session:
            training = session.query(Execution).filter_by(
                status=ExecutionStatus.TRAINING.value
            ).all()
            assert len(training) == 1
            assert training[0].job_id == "status-1"
            
            completed = session.query(Execution).filter(
                Execution.status.in_([
                    ExecutionStatus.DONE.value,
                    ExecutionStatus.FAILED.value
                ])
            ).all()
            assert len(completed) == 2
    
    def test_filter_by_dataset(self, db_manager):
        """Test filtering by dataset name."""
        datasets = ["dataset_a", "dataset_b", "dataset_a"]
        
        for i, dataset in enumerate(datasets):
            db_manager.create_execution(
                job_id=f"dataset-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name=dataset,
                preset="test_preset"
            )
        
        with db_manager.get_session() as session:
            dataset_a_jobs = session.query(Execution).filter_by(
                dataset_name="dataset_a"
            ).all()
            assert len(dataset_a_jobs) == 2
            
            dataset_b_jobs = session.query(Execution).filter_by(
                dataset_name="dataset_b"
            ).all()
            assert len(dataset_b_jobs) == 1
    
    def test_order_by_created_at(self, db_manager):
        """Test ordering by creation time."""
        # Create executions with small delays
        job_ids = []
        for i in range(3):
            execution = db_manager.create_execution(
                job_id=f"order-{i}",
                pipeline_mode=PipelineMode.SINGLE.value,
                dataset_name="test_dataset",
                preset="test_preset"
            )
            job_ids.append(execution.job_id)
        
        with db_manager.get_session() as session:
            # Get in ascending order
            ascending = session.query(Execution).order_by(
                Execution.created_at.asc()
            ).all()
            assert [e.job_id for e in ascending] == job_ids
            
            # Get in descending order
            descending = session.query(Execution).order_by(
                Execution.created_at.desc()
            ).all()
            assert [e.job_id for e in descending] == job_ids[::-1]