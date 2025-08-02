"""Schema improvements with multi-database support."""

import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy import Engine, text, inspect
from sqlalchemy.exc import OperationalError

from .factory import DatabaseFactory

logger = logging.getLogger(__name__)


class SchemaOptimizer:
    """Schema optimization for different database types."""
    
    @staticmethod
    def apply_optimizations(engine: Engine):
        """Apply database-specific schema optimizations.
        
        Args:
            engine: SQLAlchemy engine
        """
        db_type = engine.dialect.name
        
        if db_type == 'sqlite':
            SchemaOptimizer._apply_sqlite_optimizations(engine)
        elif db_type == 'postgresql':
            SchemaOptimizer._apply_postgresql_optimizations(engine)
        else:
            logger.warning(f"No optimizations available for database type: {db_type}")
    
    @staticmethod
    def _apply_sqlite_optimizations(engine: Engine):
        """Apply SQLite-specific optimizations."""
        logger.info("Applying SQLite schema optimizations")
        
        with engine.connect() as conn:
            # Enable incremental auto-vacuum
            conn.execute(text("PRAGMA auto_vacuum = INCREMENTAL"))
            
            # Create additional indexes for performance
            indexes = [
                # Composite indexes for common queries
                ("idx_exec_status_created", "executions", ["status", "created_at"]),
                ("idx_exec_dataset_status", "executions", ["dataset_name", "status"]),
                ("idx_exec_created_success", "executions", ["created_at", "success"]),
                ("idx_var_status_created", "variations", ["status", "created_at"]),
                ("idx_var_dataset_status", "variations", ["dataset_name", "status"]),
                ("idx_var_created_success", "variations", ["created_at", "success"]),
                ("idx_var_experiment_status", "variations", ["experiment_name", "status", "created_at"]),
            ]
            
            for idx_name, table_name, columns in indexes:
                try:
                    # Check if index exists
                    result = conn.execute(text(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name='{idx_name}'
                    """)).fetchone()
                    
                    if not result:
                        cols = ", ".join(columns)
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS {idx_name} 
                            ON {table_name} ({cols})
                        """))
                        logger.info(f"Created index: {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create index {idx_name}: {e}")
            
            # Create partial indexes for performance
            partial_indexes = [
                ("idx_exec_stats", "executions", "status, success, duration_seconds", 
                 "WHERE duration_seconds IS NOT NULL"),
                ("idx_var_stats", "variations", "status, success, duration_seconds", 
                 "WHERE duration_seconds IS NOT NULL"),
            ]
            
            for idx_name, table_name, columns, where_clause in partial_indexes:
                try:
                    result = conn.execute(text(f"""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name='{idx_name}'
                    """)).fetchone()
                    
                    if not result:
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS {idx_name} 
                            ON {table_name} ({columns}) {where_clause}
                        """))
                        logger.info(f"Created partial index: {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create partial index {idx_name}: {e}")
            
            # Analyze tables for query optimizer
            conn.execute(text("ANALYZE"))
            conn.commit()
    
    @staticmethod
    def _apply_postgresql_optimizations(engine: Engine):
        """Apply PostgreSQL-specific optimizations."""
        logger.info("Applying PostgreSQL schema optimizations")
        
        with engine.connect() as conn:
            # Create B-tree indexes for common queries
            indexes = [
                ("idx_exec_status_created", "executions", ["status", "created_at DESC"]),
                ("idx_exec_dataset_status", "executions", ["dataset_name", "status"]),
                ("idx_exec_created_success", "executions", ["created_at DESC", "success"]),
                ("idx_var_status_created", "variations", ["status", "created_at DESC"]),
                ("idx_var_dataset_status", "variations", ["dataset_name", "status"]),
                ("idx_var_created_success", "variations", ["created_at DESC", "success"]),
                ("idx_var_experiment_status", "variations", ["experiment_name", "status", "created_at DESC"]),
            ]
            
            # Start a new transaction for index creation
            trans = conn.begin()
            
            for idx_name, table_name, columns in indexes:
                try:
                    # Check if index exists
                    result = conn.execute(text(f"""
                        SELECT indexname FROM pg_indexes 
                        WHERE schemaname = 'public' 
                        AND indexname = '{idx_name}'
                    """)).fetchone()
                    
                    if not result:
                        cols = ", ".join(columns)
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS {idx_name} 
                            ON {table_name} ({cols})
                        """))
                        logger.info(f"Created index: {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create index {idx_name}: {e}")
            
            # Create partial indexes
            partial_indexes = [
                ("idx_exec_stats", "executions", "status, success, duration_seconds", 
                 "WHERE duration_seconds IS NOT NULL"),
                ("idx_var_stats", "variations", "status, success, duration_seconds", 
                 "WHERE duration_seconds IS NOT NULL"),
                ("idx_exec_running", "executions", "job_id, status", 
                 "WHERE status IN ('pending', 'training')"),
                ("idx_var_running", "variations", "job_id, status", 
                 "WHERE status IN ('pending', 'training')"),
            ]
            
            for idx_name, table_name, columns, where_clause in partial_indexes:
                try:
                    result = conn.execute(text(f"""
                        SELECT indexname FROM pg_indexes 
                        WHERE schemaname = 'public' 
                        AND indexname = '{idx_name}'
                    """)).fetchone()
                    
                    if not result:
                        conn.execute(text(f"""
                            CREATE INDEX IF NOT EXISTS {idx_name} 
                            ON {table_name} ({columns}) {where_clause}
                        """))
                        logger.info(f"Created partial index: {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create partial index {idx_name}: {e}")
            
            trans.commit()
            
            # Update table statistics
            conn.execute(text("ANALYZE"))
            conn.commit()
    
    @staticmethod
    def create_materialized_view(engine: Engine):
        """Create materialized view or equivalent for job summaries.
        
        Args:
            engine: SQLAlchemy engine
        """
        db_type = engine.dialect.name
        
        if db_type == 'sqlite':
            SchemaOptimizer._create_sqlite_cache_table(engine)
        elif db_type == 'postgresql':
            SchemaOptimizer._create_postgresql_materialized_view(engine)
    
    @staticmethod
    def _create_sqlite_cache_table(engine: Engine):
        """Create cache table for SQLite (materialized view equivalent)."""
        logger.info("Creating SQLite job summary cache table")
        
        with engine.connect() as conn:
            # Create cache table if not exists
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
                )
            """))
            
            # Create index on cache table
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_summary_status_updated 
                ON job_summary_cache (status, last_updated DESC)
            """))
            
            conn.commit()
            logger.info("SQLite cache table created")
    
    @staticmethod
    def _create_postgresql_materialized_view(engine: Engine):
        """Create materialized view for PostgreSQL."""
        logger.info("Creating PostgreSQL materialized view")
        
        with engine.connect() as conn:
            # Create materialized view
            try:
                # Check if materialized view exists
                result = conn.execute(text("""
                    SELECT matviewname FROM pg_matviews 
                    WHERE schemaname = 'public' 
                    AND matviewname = 'job_summary_view'
                """)).fetchone()
                
                if not result:
                    conn.execute(text("""
                        CREATE MATERIALIZED VIEW IF NOT EXISTS job_summary_view AS
                        SELECT 
                            job_id,
                            'execution' as job_type,
                            status,
                            dataset_name,
                            preset,
                            start_time,
                            duration_seconds,
                            success,
                            updated_at as last_updated
                        FROM executions
                        UNION ALL
                        SELECT 
                            job_id,
                            'variation' as job_type,
                            status,
                            dataset_name,
                            preset,
                            start_time,
                            duration_seconds,
                            success,
                            updated_at as last_updated
                        FROM variations
                    """))
                    
                    # Create indexes on materialized view
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_job_summary_status 
                        ON job_summary_view (status, last_updated DESC)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_job_summary_dataset 
                        ON job_summary_view (dataset_name, status)
                    """))
                    
                    conn.commit()
                    logger.info("PostgreSQL materialized view created")
                else:
                    # Refresh existing view
                    conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY job_summary_view"))
                    conn.commit()
                    logger.info("PostgreSQL materialized view refreshed")
                    
            except Exception as e:
                logger.error(f"Error creating materialized view: {e}")
                # Fall back to creating a regular table
                SchemaOptimizer._create_postgresql_cache_table(engine)
    
    @staticmethod
    def _create_postgresql_cache_table(engine: Engine):
        """Create cache table for PostgreSQL (fallback from materialized view)."""
        logger.info("Creating PostgreSQL job summary cache table")
        
        with engine.connect() as conn:
            # Create cache table similar to SQLite
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS job_summary_cache (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    start_time TIMESTAMP WITH TIME ZONE,
                    duration_seconds FLOAT,
                    success BOOLEAN,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_summary_status_updated 
                ON job_summary_cache (status, last_updated DESC)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_summary_dataset_status 
                ON job_summary_cache (dataset_name, status)
            """))
            
            conn.commit()
            logger.info("PostgreSQL cache table created")
    
    @staticmethod
    def optimize_for_read_heavy_workload(engine: Engine):
        """Optimize database for read-heavy workloads.
        
        Args:
            engine: SQLAlchemy engine
        """
        db_type = engine.dialect.name
        
        if db_type == 'sqlite':
            with engine.connect() as conn:
                # Increase page cache for better read performance
                conn.execute(text("PRAGMA cache_size = -128000"))  # 128MB
                # Use memory for temp tables
                conn.execute(text("PRAGMA temp_store = MEMORY"))
                # Optimize query planner
                conn.execute(text("PRAGMA optimize"))
                conn.commit()
                
        elif db_type == 'postgresql':
            with engine.connect() as conn:
                # These would typically be set at the server level
                # Here we set session-level parameters
                conn.execute(text("SET random_page_cost = 1.1"))  # SSD optimized
                conn.execute(text("SET effective_cache_size = '4GB'"))
                conn.execute(text("SET shared_buffers = '256MB'"))
                conn.commit()