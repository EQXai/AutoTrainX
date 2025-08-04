"""Performance indexes for database optimization."""

import logging
from typing import List, Tuple
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


class PerformanceIndexManager:
    """Manages performance indexes for database optimization."""
    
    @staticmethod
    def create_performance_indexes(engine: Engine):
        """Create all performance indexes for the database.
        
        Args:
            engine: SQLAlchemy engine
        """
        db_type = engine.dialect.name
        
        if db_type == 'postgresql':
            PerformanceIndexManager._create_postgresql_indexes(engine)
        elif db_type == 'sqlite':
            PerformanceIndexManager._create_sqlite_indexes(engine)
        else:
            logger.warning(f"No performance indexes defined for database type: {db_type}")
    
    @staticmethod
    def _create_postgresql_indexes(engine: Engine):
        """Create PostgreSQL-specific performance indexes."""
        indexes = [
            # Covering indexes for common queries
            ("idx_exec_all_jobs", "executions", 
             "(job_id, status, dataset_name, preset, start_time, duration_seconds, success)"),
            
            ("idx_var_all_jobs", "variations", 
             "(job_id, status, dataset_name, preset, start_time, duration_seconds, success)"),
            
            # Index for cache statistics queries
            ("idx_cache_dataset_stats", "job_summary_cache",
             "(dataset_name, success, duration_seconds, start_time)",
             "WHERE duration_seconds IS NOT NULL"),
            
            # Indexes for cleanup operations
            ("idx_exec_cleanup", "executions",
             "(created_at, status)",
             "WHERE success = false"),
            
            ("idx_var_cleanup", "variations",
             "(created_at, status)", 
             "WHERE success = false"),
            
            # Indexes for status filtering
            ("idx_exec_status_filter", "executions",
             "(status, created_at DESC)",
             "WHERE status IN ('pending', 'training')"),
            
            ("idx_var_status_filter", "variations",
             "(status, created_at DESC)",
             "WHERE status IN ('pending', 'training')"),
            
            # Composite indexes for dataset queries
            ("idx_exec_dataset_perf", "executions",
             "(dataset_name, status, success, duration_seconds)"),
            
            ("idx_var_dataset_perf", "variations",
             "(dataset_name, status, success, duration_seconds)"),
            
            # Indexes for recent jobs queries
            ("idx_cache_recent", "job_summary_cache",
             "(last_updated DESC, job_id, job_type)"),
            
            # Index for job lookup
            ("idx_exec_job_lookup", "executions", "(job_id, status, updated_at)"),
            ("idx_var_job_lookup", "variations", "(job_id, status, updated_at)"),
        ]
        
        PerformanceIndexManager._create_indexes(engine, indexes, 'postgresql')
    
    @staticmethod
    def _create_sqlite_indexes(engine: Engine):
        """Create SQLite-specific performance indexes."""
        indexes = [
            # Covering indexes for common queries
            ("idx_exec_all_jobs", "executions", 
             "(job_id, status, dataset_name, preset, start_time, duration_seconds, success)"),
            
            ("idx_var_all_jobs", "variations", 
             "(job_id, status, dataset_name, preset, start_time, duration_seconds, success)"),
            
            # Index for cache statistics queries
            ("idx_cache_dataset_stats", "job_summary_cache",
             "(dataset_name, success, duration_seconds, start_time)",
             "WHERE duration_seconds IS NOT NULL"),
            
            # Indexes for cleanup operations
            ("idx_exec_cleanup", "executions",
             "(created_at, status)",
             "WHERE success = 0"),
            
            ("idx_var_cleanup", "variations",
             "(created_at, status)", 
             "WHERE success = 0"),
            
            # Indexes for status filtering
            ("idx_exec_status_filter", "executions",
             "(status, created_at DESC)",
             "WHERE status IN ('pending', 'training')"),
            
            ("idx_var_status_filter", "variations",
             "(status, created_at DESC)",
             "WHERE status IN ('pending', 'training')"),
            
            # Composite indexes for dataset queries
            ("idx_exec_dataset_perf", "executions",
             "(dataset_name, status, success, duration_seconds)"),
            
            ("idx_var_dataset_perf", "variations",
             "(dataset_name, status, success, duration_seconds)"),
            
            # Indexes for recent jobs queries
            ("idx_cache_recent", "job_summary_cache",
             "(last_updated DESC, job_id, job_type)"),
            
            # Index for job lookup
            ("idx_exec_job_lookup", "executions", "(job_id, status, updated_at)"),
            ("idx_var_job_lookup", "variations", "(job_id, status, updated_at)"),
        ]
        
        PerformanceIndexManager._create_indexes(engine, indexes, 'sqlite')
    
    @staticmethod
    def _create_indexes(engine: Engine, indexes: List[Tuple], db_type: str):
        """Create indexes with error handling.
        
        Args:
            engine: SQLAlchemy engine
            indexes: List of (name, table, columns, [where_clause]) tuples
            db_type: Database type
        """
        with engine.connect() as conn:
            for index_info in indexes:
                name, table, columns = index_info[:3]
                where_clause = index_info[3] if len(index_info) > 3 else ""
                
                try:
                    # Check if index exists
                    if db_type == 'postgresql':
                        check_sql = text("""
                            SELECT 1 FROM pg_indexes 
                            WHERE schemaname = 'public' 
                            AND indexname = :name
                        """)
                    else:  # sqlite
                        check_sql = text("""
                            SELECT 1 FROM sqlite_master 
                            WHERE type = 'index' 
                            AND name = :name
                        """)
                    
                    exists = conn.execute(check_sql, {"name": name}).fetchone()
                    
                    if not exists:
                        # Validate identifiers
                        if not all(c.isalnum() or c in "_" for c in name):
                            raise ValueError(f"Invalid index name: {name}")
                        if not all(c.isalnum() or c in "_" for c in table):
                            raise ValueError(f"Invalid table name: {table}")
                        
                        # Create index
                        create_sql = f"CREATE INDEX {name} ON {table} {columns}"
                        if where_clause:
                            create_sql += f" {where_clause}"
                        
                        conn.execute(text(create_sql))
                        conn.commit()
                        logger.info(f"Created performance index: {name}")
                    
                except OperationalError as e:
                    logger.warning(f"Could not create index {name}: {e}")
                except Exception as e:
                    logger.error(f"Error creating index {name}: {e}")
    
    @staticmethod
    def drop_redundant_indexes(engine: Engine):
        """Drop redundant indexes that are covered by new composite indexes.
        
        Args:
            engine: SQLAlchemy engine
        """
        redundant_indexes = [
            # These are now covered by composite indexes
            "idx_exec_status_created",
            "idx_var_status_created",
            "idx_exec_dataset_status",
            "idx_var_dataset_status",
        ]
        
        with engine.connect() as conn:
            for index_name in redundant_indexes:
                try:
                    conn.execute(text(f"DROP INDEX IF EXISTS {index_name}"))
                    conn.commit()
                    logger.info(f"Dropped redundant index: {index_name}")
                except Exception as e:
                    logger.warning(f"Could not drop index {index_name}: {e}")