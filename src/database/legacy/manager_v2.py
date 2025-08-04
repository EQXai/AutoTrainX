"""Database manager with multi-database support."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
import logging

from sqlalchemy import desc, and_, or_, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from datetime import timedelta

from .models_v2 import Base, Execution, Variation
from .enums import ExecutionStatus, PipelineMode
from .factory import DatabaseFactory, DatabaseConfig
from .config import db_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for database operations with multi-database support."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize database manager.
        
        Args:
            config: Database configuration. If None, uses environment/default.
        """
        if config is None:
            # Create config from environment/settings
            if db_settings.db_type == 'sqlite':
                db_path = Path(db_settings.get_connection_url().replace('sqlite:///', ''))
                config = DatabaseConfig(
                    db_type='sqlite',
                    db_path=db_path,
                    echo=db_settings.is_echo_enabled(),
                    pool_config=db_settings.get_pool_config()
                )
            else:
                config = DatabaseConfig(
                    db_type='postgresql',
                    db_url=db_settings.get_connection_url(),
                    echo=db_settings.is_echo_enabled(),
                    pool_config=db_settings.get_pool_config()
                )
        
        self.config = config
        self.dialect = DatabaseFactory.get_dialect(config.db_type)
        
        # Create engine using factory
        self.engine = DatabaseFactory.create_engine(config)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        logger.info(f"✅ Database ready ({config.db_type})")
    
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
    
    def set_execution_output(self, job_id: str, output_path: str) -> bool:
        """Set the output path for an execution.
        
        Args:
            job_id: Job identifier
            output_path: Path to output directory
            
        Returns:
            True if updated, False if not found
        """
        with self.get_session() as session:
            execution = session.query(Execution).filter_by(job_id=job_id).first()
            if not execution:
                return False
            
            execution.output_path = output_path
            execution.updated_at = datetime.utcnow()
            session.commit()
            return True
    
    def update_execution_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update execution status.
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if failed
            
        Returns:
            True if updated, False if not found
        """
        with self.get_session() as session:
            execution = session.query(Execution).filter_by(job_id=job_id).first()
            if not execution:
                return False
            
            execution.status = status.value
            execution.updated_at = datetime.utcnow()
            
            if status == ExecutionStatus.FAILED and error_message:
                execution.error_message = error_message
                execution.success = False
                execution.end_time = datetime.utcnow()
                if execution.start_time:
                    execution.duration_seconds = (
                        execution.end_time - execution.start_time
                    ).total_seconds()
            elif status == ExecutionStatus.COMPLETED:
                execution.success = True
                execution.end_time = datetime.utcnow()
                if execution.start_time:
                    execution.duration_seconds = (
                        execution.end_time - execution.start_time
                    ).total_seconds()
            
            session.commit()
            return True
    
    def get_execution(self, job_id: str) -> Optional[Execution]:
        """Get execution by job ID."""
        with self.get_session() as session:
            return session.query(Execution).filter_by(job_id=job_id).first()
    
    def list_executions(self, 
                       status: Optional[str] = None,
                       dataset_name: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Execution]:
        """List executions with optional filters."""
        with self.get_session() as session:
            query = session.query(Execution)
            
            if status:
                query = query.filter(Execution.status == status)
            if dataset_name:
                query = query.filter(Execution.dataset_name == dataset_name)
            
            return query.order_by(desc(Execution.created_at)) \
                       .limit(limit) \
                       .offset(offset) \
                       .all()
    
    # ===== Variation CRUD Operations =====
    
    def create_variation(self, job_id: str, variation_id: str,
                        experiment_name: str, dataset_name: str,
                        preset: str, total_combinations: int,
                        varied_parameters: Dict[str, Any],
                        parameter_values: Dict[str, Any],
                        parent_experiment_id: Optional[str] = None) -> Variation:
        """Create a new variation record."""
        with self.get_session() as session:
            variation = Variation(
                job_id=job_id,
                variation_id=variation_id,
                experiment_name=experiment_name,
                dataset_name=dataset_name,
                preset=preset,
                total_combinations=total_combinations,
                varied_parameters=varied_parameters,
                parameter_values=parameter_values,
                parent_experiment_id=parent_experiment_id,
                status=ExecutionStatus.PENDING.value,
                start_time=datetime.utcnow()
            )
            session.add(variation)
            session.commit()
            session.refresh(variation)
            return variation
    
    def update_variation_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update variation status."""
        with self.get_session() as session:
            variation = session.query(Variation).filter_by(job_id=job_id).first()
            if not variation:
                return False
            
            variation.status = status.value
            variation.updated_at = datetime.utcnow()
            
            if status == ExecutionStatus.FAILED and error_message:
                variation.error_message = error_message
                variation.success = False
                variation.end_time = datetime.utcnow()
                if variation.start_time:
                    variation.duration_seconds = (
                        variation.end_time - variation.start_time
                    ).total_seconds()
            elif status == ExecutionStatus.COMPLETED:
                variation.success = True
                variation.end_time = datetime.utcnow()
                if variation.start_time:
                    variation.duration_seconds = (
                        variation.end_time - variation.start_time
                    ).total_seconds()
            
            session.commit()
            return True
    
    def get_variation(self, job_id: str) -> Optional[Variation]:
        """Get variation by job ID."""
        with self.get_session() as session:
            return session.query(Variation).filter_by(job_id=job_id).first()
    
    def list_variations(self,
                       experiment_name: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 100,
                       offset: int = 0) -> List[Variation]:
        """List variations with optional filters."""
        with self.get_session() as session:
            query = session.query(Variation)
            
            if experiment_name:
                query = query.filter(Variation.experiment_name == experiment_name)
            if status:
                query = query.filter(Variation.status == status)
            
            return query.order_by(desc(Variation.created_at)) \
                       .limit(limit) \
                       .offset(offset) \
                       .all()
    
    # ===== Utility Methods =====
    
    def get_recent_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs across both executions and variations."""
        with self.get_session() as session:
            # Get recent executions
            executions = session.query(Execution) \
                .order_by(desc(Execution.created_at)) \
                .limit(limit) \
                .all()
            
            # Get recent variations
            variations = session.query(Variation) \
                .order_by(desc(Variation.created_at)) \
                .limit(limit) \
                .all()
            
            # Combine and sort
            all_jobs = []
            
            for exec in executions:
                job_dict = exec.to_dict()
                job_dict['job_type'] = 'execution'
                all_jobs.append(job_dict)
            
            for var in variations:
                job_dict = var.to_dict()
                job_dict['job_type'] = 'variation'
                all_jobs.append(job_dict)
            
            # Sort by created_at
            all_jobs.sort(key=lambda x: x['created_at'] or '', reverse=True)
            
            return all_jobs[:limit]
    
    def get_job_stats(self) -> Dict[str, Any]:
        """Get overall job statistics."""
        with self.get_session() as session:
            # Execution stats
            exec_total = session.query(Execution).count()
            exec_success = session.query(Execution).filter_by(success=True).count()
            exec_failed = session.query(Execution).filter_by(success=False).count()
            exec_running = session.query(Execution).filter(
                Execution.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PENDING.value
                ])
            ).count()
            
            # Variation stats
            var_total = session.query(Variation).count()
            var_success = session.query(Variation).filter_by(success=True).count()
            var_failed = session.query(Variation).filter_by(success=False).count()
            var_running = session.query(Variation).filter(
                Variation.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PENDING.value
                ])
            ).count()
            
            return {
                'executions': {
                    'total': exec_total,
                    'success': exec_success,
                    'failed': exec_failed,
                    'running': exec_running,
                },
                'variations': {
                    'total': var_total,
                    'success': var_success,
                    'failed': var_failed,
                    'running': var_running,
                },
                'total': {
                    'total': exec_total + var_total,
                    'success': exec_success + var_success,
                    'failed': exec_failed + var_failed,
                    'running': exec_running + var_running,
                }
            }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up old records."""
        with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old executions
            exec_deleted = session.query(Execution).filter(
                Execution.created_at < cutoff_date
            ).delete()
            
            # Delete old variations
            var_deleted = session.query(Variation).filter(
                Variation.created_at < cutoff_date
            ).delete()
            
            session.commit()
            
            total_deleted = exec_deleted + var_deleted
            logger.info(f"Cleaned up {total_deleted} old records")
            
            return total_deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self.get_session() as session:
            # Count records
            total_executions = session.query(Execution).count()
            total_variations = session.query(Variation).count()
            
            # Status breakdown for executions
            exec_by_status = {}
            for status in ExecutionStatus:
                count = session.query(Execution).filter_by(status=status.value).count()
                if count > 0:
                    exec_by_status[status.value] = count
            
            # Status breakdown for variations
            var_by_status = {}
            for status in ExecutionStatus:
                count = session.query(Variation).filter_by(status=status.value).count()
                if count > 0:
                    var_by_status[status.value] = count
            
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
            
            success_rate = 0
            if total_completed + total_failed > 0:
                success_rate = total_completed / (total_completed + total_failed)
            
            # Calculate average duration
            exec_durations = [e.duration_seconds for e in 
                            session.query(Execution).filter(Execution.duration_seconds != None).all()]
            var_durations = [v.duration_seconds for v in 
                           session.query(Variation).filter(Variation.duration_seconds != None).all()]
            
            all_durations = exec_durations + var_durations
            average_duration = 0
            if all_durations:
                average_duration = sum(all_durations) / len(all_durations)
            
            return {
                'total_executions': total_executions,
                'total_variations': total_variations,
                'executions_by_status': exec_by_status,
                'variations_by_status': var_by_status,
                'success_rate': success_rate,
                'average_duration': average_duration
            }
    
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