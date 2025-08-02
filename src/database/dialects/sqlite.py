"""SQLite dialect implementation."""

import json
from typing import Any, Dict, Optional, Type
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import TypeDecorator
from sqlalchemy.exc import OperationalError

from .base import AbstractDialect


class SQLiteDialect(AbstractDialect):
    """SQLite-specific database dialect implementation."""
    
    def get_json_type(self) -> Type[TypeEngine]:
        """SQLite stores JSON as TEXT."""
        return Text
    
    def get_autoincrement_type(self) -> Type[TypeEngine]:
        """SQLite uses INTEGER for autoincrement."""
        return Integer
    
    def configure_connection(self, connection: Connection) -> None:
        """Configure SQLite connection with optimal settings."""
        # Enable WAL mode for better concurrency
        connection.execute(text("PRAGMA journal_mode=WAL"))
        # Set busy timeout to 10 seconds
        connection.execute(text("PRAGMA busy_timeout=10000"))
        # Use NORMAL synchronous mode for better performance
        connection.execute(text("PRAGMA synchronous=NORMAL"))
        # Set page cache to 64MB
        connection.execute(text("PRAGMA cache_size=-64000"))
        # Use memory for temporary tables
        connection.execute(text("PRAGMA temp_store=MEMORY"))
        # Enable foreign keys (disabled by default in SQLite)
        connection.execute(text("PRAGMA foreign_keys=ON"))
    
    def configure_engine(self, engine: Engine) -> None:
        """Configure SQLite engine after creation."""
        # Apply database-level optimizations
        with engine.connect() as conn:
            # Enable incremental vacuum to prevent bloat
            conn.execute(text("PRAGMA auto_vacuum=INCREMENTAL"))
            # Run optimization
            conn.execute(text("PRAGMA optimize"))
            # Analyze tables for query planner
            conn.execute(text("ANALYZE"))
            conn.commit()
    
    def get_connection_args(self) -> Dict[str, Any]:
        """SQLite-specific connection arguments."""
        return {
            "check_same_thread": False,  # Allow multi-threading
            "timeout": 10.0,  # Connection timeout in seconds
        }
    
    def get_pool_config(self) -> Dict[str, Any]:
        """SQLite pool configuration."""
        # SQLite doesn't benefit much from connection pooling
        # but we still use it for consistency
        return {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
        }
    
    def handle_concurrent_access_error(self, error: Exception) -> bool:
        """Check if error is a SQLite database lock error."""
        if isinstance(error, OperationalError):
            error_msg = str(error).lower()
            return any(msg in error_msg for msg in [
                "database is locked",
                "database table is locked",
                "cannot operate on a closed database",
            ])
        return False
    
    def get_table_info_query(self, table_name: str) -> str:
        """Get SQLite table schema query."""
        return f"PRAGMA table_info({table_name})"
    
    def get_index_info_query(self, table_name: str) -> str:
        """Get SQLite index information query."""
        return f"PRAGMA index_list({table_name})"
    
    def supports_json_indexing(self) -> bool:
        """SQLite doesn't support native JSON indexing."""
        return False
    
    def get_lock_timeout_setting(self, timeout_ms: int) -> Optional[str]:
        """SQLite uses PRAGMA busy_timeout."""
        return f"PRAGMA busy_timeout={timeout_ms}"
    
    def get_datetime_type(self) -> Type[TypeEngine]:
        """SQLite stores datetime as TEXT in ISO format."""
        return DateTime
    
    def format_datetime_for_insert(self, dt) -> Any:
        """Format datetime for SQLite (ISO format string)."""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        return dt


class SQLiteJSONType(TypeDecorator):
    """Custom JSON type for SQLite that handles serialization."""
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Serialize to JSON string on save."""
        if value is not None:
            return json.dumps(value)
        return None
    
    def process_result_value(self, value, dialect):
        """Deserialize from JSON string on load."""
        if value is not None:
            return json.loads(value)
        return None