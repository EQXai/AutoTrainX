"""Database schema improvements for AutoTrainX."""

from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


class SchemaOptimizer:
    """Schema optimization utilities."""
    
    @staticmethod
    def apply_optimizations(engine: Engine):
        """Apply database schema optimizations."""
        with engine.connect() as conn:
            # Create composite indexes for common query patterns
            composite_indexes = [
                # For filtering by status and ordering by created_at
                "CREATE INDEX IF NOT EXISTS idx_exec_status_created ON executions(status, created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_var_status_created ON variations(status, created_at DESC);",
                
                # For dataset-specific queries with status
                "CREATE INDEX IF NOT EXISTS idx_exec_dataset_status ON executions(dataset_name, status);",
                "CREATE INDEX IF NOT EXISTS idx_var_dataset_status ON variations(dataset_name, status);",
                
                # For time-based queries (cleanup operations)
                "CREATE INDEX IF NOT EXISTS idx_exec_created_success ON executions(created_at, success);",
                "CREATE INDEX IF NOT EXISTS idx_var_created_success ON variations(created_at, success);",
                
                # For experiment tracking
                "CREATE INDEX IF NOT EXISTS idx_var_experiment_status ON variations(experiment_name, status, created_at DESC);",
                
                # Covering index for statistics queries
                "CREATE INDEX IF NOT EXISTS idx_exec_stats ON executions(status, success, duration_seconds) WHERE duration_seconds IS NOT NULL;",
                "CREATE INDEX IF NOT EXISTS idx_var_stats ON variations(status, success, duration_seconds) WHERE duration_seconds IS NOT NULL;"
            ]
            
            for index_sql in composite_indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
            
            # Apply SQLite optimizations
            sqlite_optimizations = [
                # Increase page cache size (default is 2000 pages)
                "PRAGMA cache_size = -64000;",  # 64MB cache
                
                # Enable query planner optimizations
                "PRAGMA optimize;",
                
                # Auto vacuum to prevent database bloat
                "PRAGMA auto_vacuum = INCREMENTAL;",
                
                # Analyze tables for better query planning
                "ANALYZE executions;",
                "ANALYZE variations;"
            ]
            
            for pragma in sqlite_optimizations:
                try:
                    conn.execute(text(pragma))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Failed to apply optimization: {e}")
    
    @staticmethod
    def create_materialized_view(engine: Engine):
        """Create materialized view for job summaries."""
        # SQLite doesn't support materialized views, so we use a regular table
        # that we refresh periodically
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS job_summary_cache (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    start_time TIMESTAMP,
                    duration_seconds FLOAT,
                    success BOOLEAN,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_summary_status_updated 
                ON job_summary_cache(status, last_updated DESC);
            """))
            
            conn.commit()
    
    @staticmethod
    def refresh_job_summary_cache(engine: Engine):
        """Refresh the job summary cache."""
        with engine.connect() as conn:
            # Clear old cache
            conn.execute(text("DELETE FROM job_summary_cache;"))
            
            # Insert execution summaries
            conn.execute(text("""
                INSERT INTO job_summary_cache 
                (job_id, job_type, status, dataset_name, preset, start_time, duration_seconds, success)
                SELECT 
                    job_id, 'execution', status, dataset_name, preset, 
                    start_time, duration_seconds, success
                FROM executions;
            """))
            
            # Insert variation summaries
            conn.execute(text("""
                INSERT INTO job_summary_cache 
                (job_id, job_type, status, dataset_name, preset, start_time, duration_seconds, success)
                SELECT 
                    job_id, 'variation', status, dataset_name, preset, 
                    start_time, duration_seconds, success
                FROM variations;
            """))
            
            conn.commit()