"""
Database adapter to make DatabaseManager v2 compatible with services expecting EnhancedDatabaseManager.

This is a temporary adapter while we migrate the codebase to use DatabaseManager v2 everywhere.
"""

from typing import Any, Optional, Dict, List
from contextlib import contextmanager
from datetime import datetime

from src.database.manager_v2 import DatabaseManager
from src.database.models import Execution, Variation
from src.database.enums import ExecutionStatus


class DatabaseManagerAdapter:
    """Adapter to make DatabaseManager v2 compatible with EnhancedDatabaseManager interface."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize adapter with DatabaseManager v2 instance."""
        self.db_manager = db_manager
        self._enable_monitoring = True
    
    @contextmanager
    def get_session(self):
        """Get database session using v2 manager."""
        # DatabaseManager v2 uses get_session() which returns a context manager
        with self.db_manager.get_session() as session:
            yield session
    
    def create_execution(self, execution: Execution) -> Execution:
        """Create execution using v2 manager methods."""
        # Convert the ORM model to v2 method parameters
        self.db_manager.create_execution(
            job_id=execution.job_id,
            pipeline_mode=execution.pipeline_mode,
            dataset_name=execution.dataset_name,
            dataset_path=execution.dataset_path,
            preset_name=execution.preset_name,
            preset_config=execution.preset_config,
            base_model=execution.base_model,
            output_dir=execution.output_dir,
            metadata=execution.metadata
        )
        # Return the execution object (v2 doesn't return it, so we return the input)
        return execution
    
    def update_execution(self, execution: Execution) -> Execution:
        """Update execution using v2 manager methods."""
        # Update status if changed
        if hasattr(execution, 'status'):
            self.db_manager.update_execution_status(
                job_id=execution.job_id,
                status=execution.status,
                error_message=getattr(execution, 'error_message', None),
                metadata=getattr(execution, 'metadata', None)
            )
        return execution
    
    def get_execution(self, job_id: str) -> Optional[Execution]:
        """Get execution using v2 manager."""
        return self.db_manager.get_execution(job_id)
    
    def list_executions(self, **kwargs) -> List[Execution]:
        """List executions using v2 manager."""
        return self.db_manager.list_executions(**kwargs)
    
    def create_variation(self, variation: Variation) -> Variation:
        """Create variation using v2 manager methods."""
        self.db_manager.create_variation(
            job_id=variation.job_id,
            variation_id=variation.variation_id,
            parameters=variation.parameters,
            metadata=variation.metadata
        )
        return variation
    
    def update_variation(self, variation: Variation) -> Variation:
        """Update variation using v2 manager methods."""
        if hasattr(variation, 'status'):
            self.db_manager.update_variation_status(
                job_id=variation.job_id,
                status=variation.status,
                error_message=getattr(variation, 'error_message', None),
                metadata=getattr(variation, 'metadata', None)
            )
        return variation
    
    def get_variation(self, job_id: str) -> Optional[Variation]:
        """Get variation using v2 manager."""
        return self.db_manager.get_variation(job_id)
    
    def list_variations(self, **kwargs) -> List[Variation]:
        """List variations using v2 manager."""
        return self.db_manager.list_variations(**kwargs)
    
    # Methods that EnhancedDatabaseManager might have but v2 doesn't
    @property
    def enable_monitoring(self) -> bool:
        """Monitoring is always enabled in v2."""
        return self._enable_monitoring
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics (not implemented in v2, return empty)."""
        return {}
    
    def __getattr__(self, name):
        """Forward any other method calls to the underlying db_manager."""
        return getattr(self.db_manager, name)