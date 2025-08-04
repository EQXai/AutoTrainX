"""Enhanced database manager with multi-database support and optimizations."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import json
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, desc, and_, or_, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from .models import Base, Execution, Variation, JobSummaryCache
from .enums import ExecutionStatus, PipelineMode
from .connection_pool import ConnectionMonitor
from .optimizations import QueryOptimizer
from .schema_improvements import SchemaOptimizer
from .transactions import TransactionManager, TransactionMetrics, OptimisticLock
from .factory import DatabaseFactory, DatabaseConfig
from .config import db_settings
from .performance_indexes import PerformanceIndexManager
from .batch_operations import BatchOperationsMixin
from .query_cache import CacheMixin
from .optimized_queries import OptimizedQueriesMixin
from .utils.singleton_logger import singleton_logger

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager(BatchOperationsMixin, CacheMixin, OptimizedQueriesMixin):
    """Enhanced database manager with optimizations and monitoring."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None, enable_monitoring: bool = True):
        """Initialize enhanced database manager.
        
        Args:
            config: Database configuration. If None, uses environment/default.
            enable_monitoring: Enable connection and performance monitoring
        """
        # Initialize parent classes (including CacheMixin)
        super().__init__()
        
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
        
        # Create tables and apply optimizations
        Base.metadata.create_all(self.engine)
        
        # Apply schema optimizations based on database type
        if config.db_type == 'sqlite':
            SchemaOptimizer.apply_optimizations(self.engine)
            SchemaOptimizer.create_materialized_view(self.engine)
        else:
            # PostgreSQL-specific optimizations
            self._apply_postgresql_optimizations()
        
        # Apply performance indexes
        PerformanceIndexManager.create_performance_indexes(self.engine)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize components
        self.query_optimizer = QueryOptimizer()
        self.transaction_metrics = TransactionMetrics()
        
        # Start monitoring if enabled
        self.monitor = None
        if enable_monitoring:
            self.monitor = ConnectionMonitor(self)
            self.monitor.start_monitoring(interval=60)
        
        singleton_logger.info_once(f"Enhanced database manager initialized with {config.db_type}")
    
    def _apply_postgresql_optimizations(self):
        """Apply PostgreSQL-specific optimizations."""
        with self.engine.connect() as conn:
            # Create indexes with CONCURRENTLY option (if not exists)
            # Note: CONCURRENTLY can't be used in a transaction
            conn.execute(text("COMMIT"))  # End any open transaction
            
            # Create GIN index on JSON columns for better performance
            if self.dialect.supports_json_indexing():
                try:
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                        idx_variations_varied_params_gin 
                        ON variations USING gin(varied_parameters)
                    """))
                    conn.execute(text("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS 
                        idx_variations_param_values_gin 
                        ON variations USING gin(parameter_values)
                    """))
                except Exception as e:
                    logger.warning(f"Could not create GIN indexes: {e}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @contextmanager
    def bulk_session(self) -> Session:
        """Get a session optimized for bulk operations."""
        session = self.SessionLocal()
        try:
            # Disable autoflush for bulk operations
            session.autoflush = False
            yield session
        finally:
            session.close()
    
    # ===== Optimized Execution Operations =====
    
    def _retry_on_lock(self, func, max_attempts: int = 3, delay: float = 0.1):
        """Retry function on database lock errors."""
        for attempt in range(max_attempts):
            try:
                return func()
            except OperationalError as e:
                if self.dialect.handle_concurrent_access_error(e):
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                raise
            except Exception:
                raise
    
    def create_execution(self, job_id: str, pipeline_mode: str, 
                        dataset_name: str, preset: str,
                        total_steps: Optional[int] = None) -> Execution:
        """Create execution with retry logic."""
        def _create():
            with self.transaction_metrics.track_transaction("create_execution"):
                with self.get_session() as session:
                    with TransactionManager.atomic_transaction(session):
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
                    
                    # Update cache outside of transaction
                    self._update_job_cache(session, execution, 'execution')
                    
                    return execution
        
        return self._retry_on_lock(_create)
    
    def update_execution_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None,
                               output_path: Optional[str] = None) -> bool:
        """Update execution status with optimistic locking."""
        def _update():
            with self.transaction_metrics.track_transaction("update_execution_status"):
                with self.get_session() as session:
                    with TransactionManager.atomic_transaction(session):
                        execution = session.query(Execution).filter_by(job_id=job_id).first()
                        if not execution:
                            return False
                        
                        execution.status = status.value
                        execution.updated_at = datetime.utcnow()
                        
                        if output_path:
                            execution.output_path = output_path
                        
                        if status == ExecutionStatus.FAILED and error_message:
                            execution.error_message = error_message
                            execution.success = False
                            execution.end_time = datetime.utcnow()
                            if execution.start_time:
                                execution.duration_seconds = (
                                    execution.end_time - execution.start_time
                                ).total_seconds()
                        elif status == ExecutionStatus.DONE:
                            execution.success = True
                            execution.end_time = datetime.utcnow()
                            if execution.start_time:
                                execution.duration_seconds = (
                                    execution.end_time - execution.start_time
                                ).total_seconds()
                        
                        session.commit()
                    
                    # Update cache outside of transaction
                    self._update_job_cache(session, execution, 'execution')
                    
                    return True
        
        return self._retry_on_lock(_update)
    
    def update_variation_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update variation status with retry logic.
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if failed
            
        Returns:
            True if updated successfully
        """
        def _update():
            with self.get_session() as session:
                with TransactionManager.atomic_transaction(session):
                    variation = session.query(Variation).filter_by(job_id=job_id).first()
                    if not variation:
                        logger.warning(f"Variation {job_id} not found")
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
                    elif status == ExecutionStatus.DONE:
                        variation.success = True
                        variation.end_time = datetime.utcnow()
                        if variation.start_time:
                            variation.duration_seconds = (
                                variation.end_time - variation.start_time
                            ).total_seconds()
                    elif status == ExecutionStatus.TRAINING:
                        variation.start_time = datetime.utcnow()
                    
                    session.commit()
                
                # Update cache outside of transaction
                self._update_job_cache(session, variation, 'variation')
                
                return True
        
        return self._retry_on_lock(_update)
    
    def set_variation_output(self, job_id: str, output_path: str) -> bool:
        """Set output path for variation.
        
        Args:
            job_id: Job identifier
            output_path: Path to output model
            
        Returns:
            True if updated successfully
        """
        def _update():
            with self.get_session() as session:
                with TransactionManager.atomic_transaction(session):
                    variation = session.query(Variation).filter_by(job_id=job_id).first()
                    if not variation:
                        logger.warning(f"Variation {job_id} not found")
                        return False
                    
                    variation.output_path = output_path
                    variation.updated_at = datetime.utcnow()
                    session.commit()
                
                # Update cache outside of transaction
                self._update_job_cache(session, variation, 'variation')
                
                return True
        
        return self._retry_on_lock(_update)
    
    def set_execution_output(self, job_id: str, output_path: str) -> bool:
        """Set output path for execution.
        
        Args:
            job_id: Job identifier
            output_path: Path to output model
            
        Returns:
            True if updated successfully
        """
        def _update():
            with self.get_session() as session:
                with TransactionManager.atomic_transaction(session):
                    execution = session.query(Execution).filter_by(job_id=job_id).first()
                    if not execution:
                        logger.warning(f"Execution {job_id} not found")
                        return False
                    
                    execution.output_path = output_path
                    execution.updated_at = datetime.utcnow()
                    session.commit()
                
                # Update cache outside of transaction
                self._update_job_cache(session, execution, 'execution')
                
                return True
        
        return self._retry_on_lock(_update)
    
    # ===== Query Methods =====
    
    def get_execution(self, job_id: str) -> Optional[Execution]:
        """Get execution by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Execution object or None
        """
        with self.get_session() as session:
            return session.query(Execution).filter_by(job_id=job_id).first()
    
    def get_variation(self, job_id: str) -> Optional[Variation]:
        """Get variation by job ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Variation object or None
        """
        with self.get_session() as session:
            return session.query(Variation).filter_by(job_id=job_id).first()
    
    # ===== Cache Management =====
    
    def _update_job_cache(self, session: Session, job: Union[Execution, Variation], job_type: str):
        """Update job summary cache."""
        cache_entry = session.query(JobSummaryCache).filter_by(job_id=job.job_id).first()
        
        if not cache_entry:
            cache_entry = JobSummaryCache(
                job_id=job.job_id,
                job_type=job_type
            )
            session.add(cache_entry)
        
        cache_entry.status = job.status
        cache_entry.dataset_name = job.dataset_name
        cache_entry.preset = job.preset
        cache_entry.start_time = job.start_time
        cache_entry.duration_seconds = getattr(job, 'duration_seconds', None)
        cache_entry.success = getattr(job, 'success', None)
        cache_entry.last_updated = datetime.utcnow()
        
        session.commit()
    
    def refresh_job_cache(self):
        """Refresh the entire job summary cache."""
        with self.bulk_session() as session:
            # Clear existing cache
            session.query(JobSummaryCache).delete()
            
            # Add all executions
            for execution in session.query(Execution).all():
                self._update_job_cache(session, execution, 'execution')
            
            # Add all variations
            for variation in session.query(Variation).all():
                self._update_job_cache(session, variation, 'variation')
            
            session.commit()
            logger.info("Job summary cache refreshed")
    
    # ===== Performance Queries =====
    
    def get_recent_jobs_optimized(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs using cached data for better performance."""
        with self.get_session() as session:
            # Use cache table for better performance
            cache_entries = session.query(JobSummaryCache) \
                .order_by(desc(JobSummaryCache.last_updated)) \
                .limit(limit) \
                .all()
            
            results = []
            for entry in cache_entries:
                results.append({
                    'job_id': entry.job_id,
                    'job_type': entry.job_type,
                    'status': entry.status,
                    'dataset_name': entry.dataset_name,
                    'preset': entry.preset,
                    'start_time': entry.start_time.isoformat() if entry.start_time else None,
                    'duration_seconds': entry.duration_seconds,
                    'success': entry.success,
                })
            
            return results
    
    def get_dataset_stats(self, dataset_name: str) -> Dict[str, Any]:
        """Get statistics for a specific dataset."""
        with self.get_session() as session:
            # Use raw SQL for complex aggregations
            if self.config.db_type == 'postgresql':
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE success = true) as successful,
                        COUNT(*) FILTER (WHERE success = false) as failed,
                        AVG(duration_seconds) as avg_duration,
                        MIN(start_time) as first_run,
                        MAX(start_time) as last_run
                    FROM job_summary_cache
                    WHERE dataset_name = :dataset_name
                """)
            else:  # SQLite
                query = text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                        AVG(duration_seconds) as avg_duration,
                        MIN(start_time) as first_run,
                        MAX(start_time) as last_run
                    FROM job_summary_cache
                    WHERE dataset_name = :dataset_name
                """)
            
            result = session.execute(query, {'dataset_name': dataset_name}).fetchone()
            
            return {
                'dataset_name': dataset_name,
                'total_jobs': result.total or 0,
                'successful_jobs': result.successful or 0,
                'failed_jobs': result.failed or 0,
                'average_duration': result.avg_duration,
                'first_run': result.first_run,
                'last_run': result.last_run,
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_session() as session:
            # Count records
            total_executions = session.query(Execution).count()
            total_variations = session.query(Variation).count()
            
            # Status breakdown
            exec_by_status = {}
            var_by_status = {}
            
            for status in ExecutionStatus:
                exec_count = session.query(Execution).filter_by(status=status.value).count()
                var_count = session.query(Variation).filter_by(status=status.value).count()
                
                if exec_count > 0:
                    exec_by_status[status.value] = exec_count
                if var_count > 0:
                    var_by_status[status.value] = var_count
            
            # Calculate success rate
            total_successful = (
                session.query(Execution).filter_by(success=True).count() +
                session.query(Variation).filter_by(success=True).count()
            )
            total_failed = (
                session.query(Execution).filter_by(success=False).count() +
                session.query(Variation).filter_by(success=False).count()
            )
            total_completed = total_successful + total_failed
            
            success_rate = (total_successful / total_completed * 100) if total_completed > 0 else 0.0
            
            return {
                'total_executions': total_executions,
                'total_variations': total_variations,
                'total_jobs': total_executions + total_variations,
                'executions_by_status': exec_by_status,
                'variations_by_status': var_by_status,
                'success_rate': success_rate,
                'total_successful': total_successful,
                'total_failed': total_failed,
            }
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all jobs (executions and variations) sorted by creation time.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        with self.get_session() as session:
            # Get executions
            executions = session.query(Execution)\
                .order_by(desc(Execution.created_at))\
                .limit(limit // 2).all()
            
            for exec in executions:
                job = exec.to_dict()
                job['type'] = 'execution'
                jobs.append(job)
            
            # Get variations
            variations = session.query(Variation)\
                .order_by(desc(Variation.created_at))\
                .limit(limit // 2).all()
            
            for var in variations:
                job = var.to_dict()
                job['type'] = 'variation'
                jobs.append(job)
        
        # Sort combined list by creation time
        jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jobs[:limit]
    
    # ===== Maintenance Operations =====
    
    def perform_maintenance(self):
        """Perform database maintenance operations."""
        logger.info("Starting database maintenance")
        
        with self.engine.connect() as conn:
            if self.config.db_type == 'sqlite':
                # SQLite maintenance
                conn.execute(text("VACUUM"))
                conn.execute(text("ANALYZE"))
                conn.execute(text("PRAGMA optimize"))
            else:
                # PostgreSQL maintenance
                conn.execute(text("VACUUM ANALYZE"))
                # Update table statistics
                conn.execute(text("ANALYZE"))
            
            conn.commit()
        
        # Refresh cache
        self.refresh_job_cache()
        
        logger.info("Database maintenance completed")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        pool = self.engine.pool
        status = {
            'size': getattr(pool, 'size', lambda: 0)() if hasattr(pool, 'size') else 0,
            'checked_in': getattr(pool, 'checkedin', lambda: 0)() if hasattr(pool, 'checkedin') else 0,
            'checked_out': getattr(pool, 'checkedout', lambda: 0)() if hasattr(pool, 'checkedout') else 0,
            'overflow': getattr(pool, 'overflow', lambda: 0)() if hasattr(pool, 'overflow') else 0,
            'total': getattr(pool, 'total', lambda: 0)() if hasattr(pool, 'total') else 0,
        }
        
        # Add empty stats dict for compatibility with monitor
        status['stats'] = {
            'connections_created': 0,
            'connections_recycled': 0,
            'connections_invalidated': 0,
            'connection_errors': 0,
        }
        
        return status
    
    def clear_all_records(self) -> Dict[str, int]:
        """Clear all records from the database.
        
        WARNING: This permanently deletes all data!
        
        Returns:
            Dictionary with counts of deleted records
        """
        deleted_counts = {
            'executions': 0,
            'variations': 0,
            'cache': 0
        }
        
        with self.get_session() as session:
            # Delete all executions
            deleted_counts['executions'] = session.query(Execution).delete()
            
            # Delete all variations
            deleted_counts['variations'] = session.query(Variation).delete()
            
            # Delete cache entries
            deleted_counts['cache'] = session.query(JobSummaryCache).delete()
            
            # Commit the deletions
            session.commit()
            
        # Invalidate all caches
        self.invalidate_cache()
        
        logger.warning(
            f"Cleared all database records: "
            f"{deleted_counts['executions']} executions, "
            f"{deleted_counts['variations']} variations, "
            f"{deleted_counts['cache']} cache entries"
        )
        
        return deleted_counts