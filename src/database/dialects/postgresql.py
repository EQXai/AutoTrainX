"""PostgreSQL dialect implementation."""

from typing import Any, Dict, Optional, Type
from datetime import datetime
from sqlalchemy import Integer, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.exc import OperationalError
import psycopg2

from .base import AbstractDialect


class PostgreSQLDialect(AbstractDialect):
    """PostgreSQL-specific database dialect implementation."""
    
    def get_json_type(self) -> Type[TypeEngine]:
        """PostgreSQL uses native JSONB type."""
        return JSONB
    
    def get_autoincrement_type(self) -> Type[TypeEngine]:
        """PostgreSQL uses SERIAL or IDENTITY for autoincrement."""
        # Using Integer with autoincrement=True will create SERIAL
        return Integer
    
    def configure_connection(self, connection: Connection) -> None:
        """Configure PostgreSQL connection with optimal settings."""
        # Set statement timeout to 30 seconds by default
        connection.execute(text("SET statement_timeout = '30s'"))
        # Set lock timeout to 10 seconds
        connection.execute(text("SET lock_timeout = '10s'"))
        # Set timezone to UTC
        connection.execute(text("SET timezone = 'UTC'"))
        # Enable JIT compilation for complex queries
        connection.execute(text("SET jit = 'on'"))
        # Set work memory for better sort/hash performance
        connection.execute(text("SET work_mem = '16MB'"))
    
    def configure_engine(self, engine: Engine) -> None:
        """Configure PostgreSQL engine after creation."""
        # PostgreSQL handles most optimizations automatically
        # We can add ANALYZE for statistics if needed
        with engine.connect() as conn:
            # Update table statistics
            conn.execute(text("ANALYZE"))
            conn.commit()
    
    def get_connection_args(self) -> Dict[str, Any]:
        """PostgreSQL-specific connection arguments."""
        return {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",  # 30 seconds in ms
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    
    def get_pool_config(self) -> Dict[str, Any]:
        """PostgreSQL benefits from connection pooling."""
        return {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo_pool': False,
        }
    
    def handle_concurrent_access_error(self, error: Exception) -> bool:
        """Check if error is a PostgreSQL concurrent access issue."""
        if isinstance(error, OperationalError):
            # Check for PostgreSQL error codes
            if hasattr(error.orig, 'pgcode'):
                # Common retryable PostgreSQL errors
                retryable_codes = {
                    '40001',  # serialization_failure
                    '40P01',  # deadlock_detected
                    '55P03',  # lock_not_available
                    '57014',  # query_canceled (often due to statement timeout)
                }
                return error.orig.pgcode in retryable_codes
            
            # Fallback to string matching
            error_msg = str(error).lower()
            return any(msg in error_msg for msg in [
                "deadlock detected",
                "could not serialize access",
                "lock timeout",
                "statement timeout",
            ])
        
        # Check for psycopg2 specific errors
        if isinstance(error, psycopg2.OperationalError):
            return True
            
        return False
    
    def get_table_info_query(self, table_name: str) -> str:
        """Get PostgreSQL table schema query."""
        return f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
    
    def get_index_info_query(self, table_name: str) -> str:
        """Get PostgreSQL index information query."""
        return f"""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = '{table_name}'
        """
    
    def supports_json_indexing(self) -> bool:
        """PostgreSQL supports GIN indexes on JSONB columns."""
        return True
    
    def get_lock_timeout_setting(self, timeout_ms: int) -> Optional[str]:
        """PostgreSQL uses SET lock_timeout."""
        return f"SET lock_timeout = '{timeout_ms}ms'"
    
    def get_datetime_type(self) -> Type[TypeEngine]:
        """PostgreSQL uses TIMESTAMP WITH TIME ZONE."""
        return TIMESTAMP(timezone=True)
    
    def format_datetime_for_insert(self, dt) -> Any:
        """PostgreSQL handles datetime objects natively."""
        return dt