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

from .models_v2 import Base, Execution, Variation, JobSummaryCache
from .enums import ExecutionStatus, PipelineMode
from .connection_pool import ConnectionMonitor
from .optimizations import QueryOptimizer
from .schema_improvements import SchemaOptimizer
from .transactions import TransactionManager, TransactionMetrics, OptimisticLock
from .factory import DatabaseFactory, DatabaseConfig
from .config import db_settings

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """Enhanced database manager with optimizations and monitoring."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None, enable_monitoring: bool = True):
        """Initialize enhanced database manager.
        
        Args:
            config: Database configuration. If None, uses environment/default.
            enable_monitoring: Enable connection and performance monitoring
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
        
        # Create tables and apply optimizations
        Base.metadata.create_all(self.engine)
        
        # Apply schema optimizations based on database type
        if config.db_type == 'sqlite':
            SchemaOptimizer.apply_optimizations(self.engine)
            SchemaOptimizer.create_materialized_view(self.engine)
        else:
            # PostgreSQL-specific optimizations
            self._apply_postgresql_optimizations()
        
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
        
        logger.info(f"Enhanced database manager initialized with {config.db_type}")
    
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
                        session.refresh(execution)
                        
                        # Update cache
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
                    execution = session.query(Execution).filter_by(job_id=job_id).first()
                    if not execution:
                        return False
                    
                    # Optimistic locking check
                    with OptimisticLock(execution, 'updated_at'):
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
                        elif status == ExecutionStatus.COMPLETED:
                            execution.success = True
                            execution.end_time = datetime.utcnow()
                            if execution.start_time:
                                execution.duration_seconds = (
                                    execution.end_time - execution.start_time
                                ).total_seconds()
                        
                        session.commit()
                        
                        # Update cache
                        self._update_job_cache(session, execution, 'execution')
                        
                        return True
        
        return self._retry_on_lock(_update)
    
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
        return {
            'size': getattr(pool, 'size', 0),
            'checked_in': getattr(pool, 'checkedin', 0),
            'checked_out': getattr(pool, 'checkedout', 0),
            'overflow': getattr(pool, 'overflow', 0),
            'total': getattr(pool, 'total', 0),
        }