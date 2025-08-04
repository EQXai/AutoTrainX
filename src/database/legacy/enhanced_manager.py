"""Enhanced database manager with all optimizations applied."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, desc, and_, or_, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Execution, Variation
from .enums import ExecutionStatus, PipelineMode
from .connection_pool import PooledDatabaseManager, ConnectionMonitor
from .optimizations import QueryOptimizer
from .schema_improvements import SchemaOptimizer
from .transactions import TransactionManager, TransactionMetrics, OptimisticLock

logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """Enhanced database manager with optimizations and monitoring."""
    
    def __init__(self, db_path: Optional[Path] = None, enable_monitoring: bool = True):
        """Initialize enhanced database manager.
        
        Args:
            db_path: Path to SQLite database file
            enable_monitoring: Enable connection and performance monitoring
        """
        if db_path is None:
            db_dir = Path(__file__).parent.parent.parent / "DB"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "executions.db"
        
        self.db_path = db_path
        
        # Initialize pooled connection manager
        self.pool_manager = PooledDatabaseManager(
            db_path,
            pool_config={
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True
            }
        )
        
        # Create tables and apply optimizations
        Base.metadata.create_all(self.pool_manager.engine)
        SchemaOptimizer.apply_optimizations(self.pool_manager.engine)
        SchemaOptimizer.create_materialized_view(self.pool_manager.engine)
        
        # Initialize components
        self.query_optimizer = QueryOptimizer()
        self.transaction_metrics = TransactionMetrics()
        
        # Start monitoring if enabled
        self.monitor = None
        if enable_monitoring:
            self.monitor = ConnectionMonitor(self.pool_manager)
            self.monitor.start_monitoring(interval=60)
        
        logger.info(f"Enhanced database manager initialized: {db_path}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        with self.pool_manager.get_session() as session:
            yield session
    
    @contextmanager
    def bulk_session(self) -> Session:
        """Get a session optimized for bulk operations."""
        with self.pool_manager.bulk_session() as session:
            yield session
    
    # ===== Optimized Execution Operations =====
    
    @TransactionManager.with_retry(max_attempts=3, delay=0.1)
    def create_execution(self, job_id: str, pipeline_mode: str, 
                        dataset_name: str, preset: str,
                        total_steps: Optional[int] = None) -> Execution:
        """Create execution with retry logic."""
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
                    session.flush()
                    session.refresh(execution)
                    return execution
    
    @TransactionManager.with_retry(max_attempts=3, delay=0.1)
    def update_execution_status(self, job_id: str, status: ExecutionStatus,
                               error_message: Optional[str] = None) -> bool:
        """Update execution status with optimistic locking."""
        with self.transaction_metrics.track_transaction("update_execution_status"):
            with self.get_session() as session:
                updates = {
                    'status': status.value,
                    'updated_at': datetime.utcnow()
                }
                
                if error_message:
                    updates['error_message'] = error_message
                
                if status in [ExecutionStatus.DONE, ExecutionStatus.FAILED]:
                    updates['end_time'] = datetime.utcnow()
                    updates['success'] = (status == ExecutionStatus.DONE)
                
                return OptimisticLock.update_with_version_check(
                    session, Execution, job_id, updates
                )
    
    def get_executions_optimized(self, status: Optional[ExecutionStatus] = None,
                                dataset_name: Optional[str] = None,
                                limit: int = 100) -> List[Execution]:
        """Get executions using optimized query."""
        with self.get_session() as session:
            with TransactionManager.atomic_transaction(session, read_only=True):
                query = session.query(Execution)
                
                # Use composite index for status + created_at
                if status:
                    query = query.filter_by(status=status.value)
                
                # Use dataset index if filtering by dataset
                if dataset_name:
                    query = query.filter_by(dataset_name=dataset_name)
                
                # Force index usage with hint
                query = query.order_by(desc(Execution.created_at))
                
                return query.limit(limit).all()
    
    def batch_update_executions(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update multiple executions efficiently."""
        with self.bulk_session() as session:
            with TransactionManager.atomic_transaction(session):
                return TransactionManager.batch_operation(
                    session, updates, batch_size=100, operation='update'
                )
    
    # ===== Optimized Statistics =====
    
    def get_statistics_optimized(self) -> Dict[str, Any]:
        """Get database statistics using optimized queries."""
        with self.get_session() as session:
            with TransactionManager.atomic_transaction(session, read_only=True):
                return self.query_optimizer.get_statistics_optimized(session)
    
    def get_active_jobs_optimized(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get active jobs using optimized UNION query."""
        with self.get_session() as session:
            with TransactionManager.atomic_transaction(session, read_only=True):
                return self.query_optimizer.get_active_jobs_optimized(session, limit)
    
    # ===== Cache Management =====
    
    def refresh_job_cache(self):
        """Refresh the job summary cache for faster queries."""
        SchemaOptimizer.refresh_job_summary_cache(self.pool_manager.engine)
    
    def get_cached_jobs(self, status: Optional[str] = None, 
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs from the cache table."""
        with self.get_session() as session:
            query = text("""
                SELECT * FROM job_summary_cache
                WHERE (:status IS NULL OR status = :status)
                ORDER BY last_updated DESC
                LIMIT :limit
            """)
            
            result = session.execute(query, {"status": status, "limit": limit})
            return [dict(row) for row in result]
    
    # ===== Monitoring and Metrics =====
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        return {
            'connection_pool': self.pool_manager.get_pool_status(),
            'transaction_metrics': self.transaction_metrics.get_metrics(),
            'database_stats': self.get_statistics_optimized()
        }
    
    def vacuum_database(self):
        """Perform database maintenance."""
        with self.pool_manager.engine.connect() as conn:
            # Analyze tables for query optimization
            conn.execute(text("ANALYZE;"))
            
            # Vacuum to reclaim space
            conn.execute(text("VACUUM;"))
            
            # Optimize query planner
            conn.execute(text("PRAGMA optimize;"))
            
            conn.commit()
        
        logger.info("Database maintenance completed")
    
    def cleanup_old_records_optimized(self, days: int = 90) -> int:
        """Delete old records using optimized batch deletion."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        
        with self.bulk_session() as session:
            with TransactionManager.atomic_transaction(session):
                # Use batch deletion for better performance
                exec_deleted = session.execute(
                    text("""
                        DELETE FROM executions 
                        WHERE created_at < :cutoff 
                        AND job_id IN (
                            SELECT job_id FROM executions 
                            WHERE created_at < :cutoff 
                            LIMIT 1000
                        )
                    """),
                    {"cutoff": cutoff_date}
                ).rowcount
                
                var_deleted = session.execute(
                    text("""
                        DELETE FROM variations 
                        WHERE created_at < :cutoff 
                        AND job_id IN (
                            SELECT job_id FROM variations 
                            WHERE created_at < :cutoff 
                            LIMIT 1000
                        )
                    """),
                    {"cutoff": cutoff_date}
                ).rowcount
                
                deleted = exec_deleted + var_deleted
        
        # Vacuum after large deletion
        if deleted > 100:
            self.vacuum_database()
        
        logger.info(f"Deleted {deleted} records older than {days} days")
        return deleted
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.monitor:
            self.monitor.stop_monitoring()
        self.pool_manager.dispose_pool()