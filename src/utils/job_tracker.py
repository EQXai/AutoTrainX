"""Job tracking utilities for AutoTrainX pipelines."""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from contextlib import contextmanager
import traceback

from src.database import EnhancedDatabaseManager
from src.database.enums import ExecutionStatus, PipelineMode


logger = logging.getLogger(__name__)


class JobTracker:
    """Tracks job execution across pipelines."""
    
    def __init__(self, enabled: bool = True, db_path: Optional[Path] = None):
        """Initialize job tracker.
        
        Args:
            enabled: Whether tracking is enabled
            db_path: Optional path to database file
        """
        self.enabled = enabled
        self.db_manager = None
        
        if self.enabled:
            try:
                from src.utils.quiet_mode import quiet_database_init
                from src.database.config import db_settings
                
                with quiet_database_init():
                    # Use the v2 manager with auto-configuration
                    self.db_manager = EnhancedDatabaseManager()
                logger.debug(f"Job tracking enabled with {db_settings.db_type}")
            except Exception as e:
                logger.warning(f"Failed to initialize job tracking: {e}")
                self.enabled = False
    
    @property
    def is_enabled(self) -> bool:
        """Check if tracking is enabled and functional."""
        return self.enabled and self.db_manager is not None
    
    # ===== Single/Batch Execution Tracking =====
    
    def create_execution(self, job_id: str, pipeline_mode: str,
                        dataset_name: str, preset: str,
                        total_steps: Optional[int] = None) -> bool:
        """Create a new execution record.
        
        Args:
            job_id: Unique job identifier
            pipeline_mode: Pipeline mode (single/batch)
            dataset_name: Name of the dataset
            preset: Preset name
            total_steps: Total training steps if known
            
        Returns:
            True if created successfully
        """
        if not self.is_enabled:
            return False
        
        try:
            self.db_manager.create_execution(
                job_id=job_id,
                pipeline_mode=pipeline_mode,
                dataset_name=dataset_name,
                preset=preset,
                total_steps=total_steps
            )
            logger.debug(f"Created execution record for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create execution record: {e}")
            return False
    
    def update_status(self, job_id: str, status: ExecutionStatus,
                     error_message: Optional[str] = None) -> bool:
        """Update job status.
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if failed
            
        Returns:
            True if updated successfully
        """
        if not self.is_enabled:
            return False
        
        try:
            # Check if it's a variation first to avoid unnecessary warnings
            if self.db_manager.get_variation(job_id):
                return self.db_manager.update_variation_status(
                    job_id, status, error_message
                )
            else:
                # Try as execution
                return self.db_manager.update_execution_status(
                    job_id, status, error_message
                )
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False
    
    def set_output_path(self, job_id: str, output_path: str) -> bool:
        """Set output path for job.
        
        Args:
            job_id: Job identifier
            output_path: Path to output model
            
        Returns:
            True if updated successfully
        """
        if not self.is_enabled:
            return False
        
        try:
            # Check if it's a variation first to avoid unnecessary warnings
            if self.db_manager.get_variation(job_id):
                return self.db_manager.set_variation_output(job_id, output_path)
            else:
                # Try as execution
                return self.db_manager.set_execution_output(job_id, output_path)
        except Exception as e:
            logger.error(f"Failed to set output path: {e}")
            return False
    
    # ===== Variation Execution Tracking =====
    
    def create_variation(self, job_id: str, variation_id: str,
                        experiment_name: str, dataset_name: str,
                        preset: str, total_combinations: int,
                        varied_parameters: Dict[str, List[Any]],
                        parameter_values: Dict[str, Any],
                        parent_experiment_id: Optional[str] = None,
                        total_steps: Optional[int] = None) -> bool:
        """Create a new variation record.
        
        Args:
            job_id: Unique job identifier
            variation_id: Variation identifier
            experiment_name: Experiment name
            dataset_name: Dataset name
            preset: Preset name
            total_combinations: Total number of variations
            varied_parameters: Parameters being varied
            parameter_values: Values for this variation
            parent_experiment_id: Parent experiment ID
            total_steps: Total training steps if known
            
        Returns:
            True if created successfully
        """
        if not self.is_enabled:
            return False
        
        try:
            self.db_manager.create_variation(
                job_id=job_id,
                variation_id=variation_id,
                experiment_name=experiment_name,
                dataset_name=dataset_name,
                preset=preset,
                total_combinations=total_combinations,
                varied_parameters=varied_parameters,
                parameter_values=parameter_values,
                parent_experiment_id=parent_experiment_id
            )
            logger.debug(f"Created variation record for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create variation record: {e}")
            return False
    
    # ===== Context Managers =====
    
    @contextmanager
    def track_execution(self, job_id: str, pipeline_mode: str,
                       dataset_name: str, preset: str,
                       total_steps: Optional[int] = None):
        """Context manager for tracking execution lifecycle.
        
        Args:
            job_id: Unique job identifier
            pipeline_mode: Pipeline mode (single/batch)
            dataset_name: Name of the dataset
            preset: Preset name
            total_steps: Total training steps if known
        """
        # Create execution record
        self.create_execution(job_id, pipeline_mode, dataset_name, preset, total_steps)
        
        try:
            yield self
        except Exception as e:
            # Capture error and update status
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.update_status(job_id, ExecutionStatus.FAILED, error_message=error_msg)
            raise
        else:
            # If no exception, mark as done
            self.update_status(job_id, ExecutionStatus.DONE)
    
    @contextmanager
    def track_stage(self, job_id: str, status: ExecutionStatus):
        """Context manager for tracking pipeline stages.
        
        Args:
            job_id: Job identifier
            status: Stage status
        """
        # Update status at start
        self.update_status(job_id, status)
        
        try:
            yield
        except Exception as e:
            # Capture error and update status
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            self.update_status(job_id, ExecutionStatus.FAILED, error_message=error_msg)
            raise
    
    # ===== Query Methods =====
    
    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job dictionary or None
        """
        if not self.is_enabled:
            return None
        
        try:
            # Try as execution first
            execution = self.db_manager.get_execution(job_id)
            if execution:
                info = execution.to_dict()
                info['type'] = 'execution'
                return info
            
            # Then try as variation
            variation = self.db_manager.get_variation(job_id)
            if variation:
                info = variation.to_dict()
                info['type'] = 'variation'
                return info
            
            return None
        except Exception as e:
            logger.error(f"Failed to get job info: {e}")
            return None
    
    def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs.
        
        Args:
            limit: Maximum number of jobs
            
        Returns:
            List of job dictionaries
        """
        if not self.is_enabled:
            return []
        
        try:
            return self.db_manager.get_all_jobs(limit)
        except Exception as e:
            logger.error(f"Failed to get recent jobs: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.is_enabled:
            return {}
        
        try:
            return self.db_manager.get_statistics()
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# Global tracker instance
_tracker: Optional[JobTracker] = None


def initialize_tracker(enabled: bool = True, db_path: Optional[Path] = None):
    """Initialize global job tracker.
    
    Args:
        enabled: Whether tracking is enabled
        db_path: Optional path to database file
    """
    global _tracker
    _tracker = JobTracker(enabled, db_path)


def get_tracker() -> JobTracker:
    """Get global job tracker instance.
    
    Returns:
        JobTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = JobTracker()
    return _tracker