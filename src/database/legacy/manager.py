"""Database manager for AutoTrainX execution tracking."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
import logging

from sqlalchemy import create_engine, desc, and_, or_
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Execution, Variation
from .enums import ExecutionStatus, PipelineMode


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use project directory DB folder
            db_dir = Path(__file__).parent.parent.parent / "DB"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "executions.db"
        
        self.db_path = db_path
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},  # Allow multi-threading
            echo=False
        )
        
        # Enable WAL mode for better concurrency
        from sqlalchemy import text
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA busy_timeout=5000"))  # 5 second timeout
            conn.commit()
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    # ===== Execution CRUD Operations =====
    
    def create_execution(self, job_id: str, pipeline_mode: str, 
                        dataset_name: str, preset: str,
                        total_steps: Optional[int] = None) -> Execution:
        """Create a new execution record.
        
        Args:
            job_id: Unique job identifier
            pipeline_mode: Pipeline mode (single/batch)
            dataset_name: Name of the dataset
            preset: Preset name
            total_steps: Total training steps if known
            
        Returns:
            Created Execution object
        """
        with self.get_session() as session:
            execution = Execution(
                job_id=job_id,
                pipeline_mode=pipeline_mode,
                dataset_name=dataset_name,
                preset=preset,
                total_steps=total_steps,
                status=ExecutionStatus.PENDING.value,
                start_time=datetime.utcnow()
            )
            session.add(execution)
            session.commit()
            session.refresh(execution)
            return execution
    
    def update_execution_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update execution status.
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if failed
            
        Returns:
            True if updated successfully
        """
        with self.get_session() as session:
            execution = session.query(Execution).filter_by(job_id=job_id).first()
            if not execution:
                logger.warning(f"Execution {job_id} not found")
                return False
            
            execution.status = status.value
            execution.updated_at = datetime.utcnow()
            
            if error_message:
                execution.error_message = error_message
            
            # Handle completion
            if status in [ExecutionStatus.DONE, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                execution.end_time = datetime.utcnow()
                if execution.start_time:
                    duration = (execution.end_time - execution.start_time).total_seconds()
                    execution.duration_seconds = duration
                
                if status == ExecutionStatus.DONE:
                    execution.success = True
                elif status == ExecutionStatus.CANCELLED:
                    execution.success = False
            
            session.commit()
            return True
    
    def set_execution_output(self, job_id: str, output_path: str) -> bool:
        """Set output path for execution.
        
        Args:
            job_id: Job identifier
            output_path: Path to output model
            
        Returns:
            True if updated successfully
        """
        with self.get_session() as session:
            execution = session.query(Execution).filter_by(job_id=job_id).first()
            if not execution:
                return False
            
            execution.output_path = output_path
            execution.updated_at = datetime.utcnow()
            session.commit()
            return True
    
    def get_execution(self, job_id: str) -> Optional[Execution]:
        """Get execution by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Execution object or None
        """
        with self.get_session() as session:
            return session.query(Execution).filter_by(job_id=job_id).first()
    
    def get_executions(self, status: Optional[ExecutionStatus] = None,
                      dataset_name: Optional[str] = None,
                      limit: int = 100) -> List[Execution]:
        """Get executions with filters.
        
        Args:
            status: Filter by status
            dataset_name: Filter by dataset name
            limit: Maximum results
            
        Returns:
            List of Execution objects
        """
        with self.get_session() as session:
            query = session.query(Execution)
            
            if status:
                query = query.filter_by(status=status.value)
            
            if dataset_name:
                query = query.filter_by(dataset_name=dataset_name)
            
            return query.order_by(desc(Execution.created_at)).limit(limit).all()
    
    # ===== Variation CRUD Operations =====
    
    def create_variation(self, job_id: str, variation_id: str,
                        experiment_name: str, dataset_name: str,
                        preset: str, total_combinations: int,
                        varied_parameters: Dict[str, List[Any]],
                        parameter_values: Dict[str, Any],
                        parent_experiment_id: Optional[str] = None,
                        total_steps: Optional[int] = None) -> Variation:
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
            Created Variation object
        """
        with self.get_session() as session:
            variation = Variation(
                job_id=job_id,
                variation_id=variation_id,
                experiment_name=experiment_name,
                dataset_name=dataset_name,
                preset=preset,
                total_combinations=total_combinations,
                varied_parameters=json.dumps(varied_parameters),
                parameter_values=json.dumps(parameter_values),
                parent_experiment_id=parent_experiment_id,
                total_steps=total_steps,
                status=ExecutionStatus.PENDING.value,
                start_time=datetime.utcnow()
            )
            session.add(variation)
            session.commit()
            session.refresh(variation)
            return variation
    
    def update_variation_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update variation status.
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if failed
            
        Returns:
            True if updated successfully
        """
        with self.get_session() as session:
            variation = session.query(Variation).filter_by(job_id=job_id).first()
            if not variation:
                logger.warning(f"Variation {job_id} not found")
                return False
            
            variation.status = status.value
            variation.updated_at = datetime.utcnow()
            
            if error_message:
                variation.error_message = error_message
            
            # Handle completion
            if status in [ExecutionStatus.DONE, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                variation.end_time = datetime.utcnow()
                if variation.start_time:
                    duration = (variation.end_time - variation.start_time).total_seconds()
                    variation.duration_seconds = duration
                
                if status == ExecutionStatus.DONE:
                    variation.success = True
                elif status == ExecutionStatus.CANCELLED:
                    variation.success = False
            
            session.commit()
            return True
    
    def set_variation_output(self, job_id: str, output_path: str) -> bool:
        """Set output path for variation.
        
        Args:
            job_id: Job identifier
            output_path: Path to output model
            
        Returns:
            True if updated successfully
        """
        with self.get_session() as session:
            variation = session.query(Variation).filter_by(job_id=job_id).first()
            if not variation:
                return False
            
            variation.output_path = output_path
            variation.updated_at = datetime.utcnow()
            session.commit()
            return True
    
    def get_variation(self, job_id: str) -> Optional[Variation]:
        """Get variation by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Variation object or None
        """
        with self.get_session() as session:
            return session.query(Variation).filter_by(job_id=job_id).first()
    
    def get_variations(self, experiment_name: Optional[str] = None,
                      parent_experiment_id: Optional[str] = None,
                      status: Optional[ExecutionStatus] = None,
                      limit: int = 100) -> List[Variation]:
        """Get variations with filters.
        
        Args:
            experiment_name: Filter by experiment name
            parent_experiment_id: Filter by parent experiment
            status: Filter by status
            limit: Maximum results
            
        Returns:
            List of Variation objects
        """
        with self.get_session() as session:
            query = session.query(Variation)
            
            if experiment_name:
                query = query.filter_by(experiment_name=experiment_name)
            
            if parent_experiment_id:
                query = query.filter_by(parent_experiment_id=parent_experiment_id)
            
            if status:
                query = query.filter_by(status=status.value)
            
            return query.order_by(desc(Variation.created_at)).limit(limit).all()
    
    # ===== General Operations =====
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all jobs (executions and variations) sorted by creation time.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        with self.get_session() as session:
            # Get executions
            executions = session.query(Execution)\
                .order_by(desc(Execution.created_at))\
                .limit(limit).all()
            
            for exec in executions:
                job = exec.to_dict()
                job['type'] = 'execution'
                jobs.append(job)
            
            # Get variations
            variations = session.query(Variation)\
                .order_by(desc(Variation.created_at))\
                .limit(limit).all()
            
            for var in variations:
                job = var.to_dict()
                job['type'] = 'variation'
                jobs.append(job)
        
        # Sort by created_at
        jobs.sort(key=lambda x: x['created_at'] or '', reverse=True)
        return jobs[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_session() as session:
            stats = {
                'total_executions': session.query(Execution).count(),
                'total_variations': session.query(Variation).count(),
                'executions_by_status': {},
                'variations_by_status': {},
                'success_rate': 0.0,
                'average_duration': 0.0
            }
            
            # Count by status
            for status in ExecutionStatus:
                exec_count = session.query(Execution)\
                    .filter_by(status=status.value).count()
                var_count = session.query(Variation)\
                    .filter_by(status=status.value).count()
                
                if exec_count > 0:
                    stats['executions_by_status'][status.value] = exec_count
                if var_count > 0:
                    stats['variations_by_status'][status.value] = var_count
            
            # Calculate success rate
            total_completed = (
                session.query(Execution).filter_by(success=True).count() +
                session.query(Variation).filter_by(success=True).count()
            )
            total_failed = (
                session.query(Execution).filter_by(success=False)\
                    .filter(Execution.end_time != None).count() +
                session.query(Variation).filter_by(success=False)\
                    .filter(Variation.end_time != None).count()
            )
            
            if total_completed + total_failed > 0:
                stats['success_rate'] = total_completed / (total_completed + total_failed)
            
            # Calculate average duration
            exec_durations = [e.duration_seconds for e in 
                            session.query(Execution).filter(Execution.duration_seconds != None).all()]
            var_durations = [v.duration_seconds for v in 
                           session.query(Variation).filter(Variation.duration_seconds != None).all()]
            
            all_durations = exec_durations + var_durations
            if all_durations:
                stats['average_duration'] = sum(all_durations) / len(all_durations)
            
            return stats
    
    def clear_all_records(self) -> Dict[str, int]:
        """Clear all records from the database.
        
        Returns:
            Dictionary with counts of deleted records by type
        """
        with self.get_session() as session:
            # Count records before deletion
            exec_count = session.query(Execution).count()
            var_count = session.query(Variation).count()
            
            # Delete all records
            session.query(Execution).delete()
            session.query(Variation).delete()
            session.commit()
            
            return {
                'executions': exec_count,
                'variations': var_count,
                'total': exec_count + var_count
            }
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """Delete records older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        
        with self.get_session() as session:
            # Delete old executions
            exec_deleted = session.query(Execution)\
                .filter(Execution.created_at < cutoff_date)\
                .delete()
            
            # Delete old variations
            var_deleted = session.query(Variation)\
                .filter(Variation.created_at < cutoff_date)\
                .delete()
            
            session.commit()
            deleted = exec_deleted + var_deleted
        
        logger.info(f"Deleted {deleted} records older than {days} days")
        return deleted
    
    def cleanup_stale_processes(self) -> int:
        """Clean up processes that are stuck in active states but no longer running.
        
        This method detects and marks as failed any executions or variations that are
        in active states (training, preparing, etc.) but their associated processes
        are no longer alive.
        
        Returns:
            Number of stale processes cleaned up
        """
        from .process_monitor import ProcessStatusMonitor
        
        monitor = ProcessStatusMonitor(self)
        cleaned_count = monitor.manual_cleanup()
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} stale processes")
        
        return cleaned_count
    
    def start_process_monitoring(self, check_interval: int = 30):
        """Start automatic process monitoring in background.
        
        Args:
            check_interval: Interval in seconds between checks
        """
        from .process_monitor import ProcessStatusMonitor
        
        if not hasattr(self, '_process_monitor'):
            self._process_monitor = ProcessStatusMonitor(self, check_interval)
            self._process_monitor.start_monitoring()
            logger.info("Started automatic process monitoring")
        else:
            logger.warning("Process monitoring is already running")
    
    def stop_process_monitoring(self):
        """Stop automatic process monitoring."""
        if hasattr(self, '_process_monitor'):
            self._process_monitor.stop_monitoring()
            delattr(self, '_process_monitor')
            logger.info("Stopped automatic process monitoring")
        else:
            logger.warning("Process monitoring is not running")