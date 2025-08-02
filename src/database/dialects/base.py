"""Abstract base class for database dialects."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from sqlalchemy import TypeDecorator
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.type_api import TypeEngine


class AbstractDialect(ABC):
    """Abstract base class for database-specific implementations."""
    
    @abstractmethod
    def get_json_type(self) -> Type[TypeEngine]:
        """Get the appropriate JSON column type for this dialect.
        
        Returns:
            SQLAlchemy type for JSON storage
        """
        pass
    
    @abstractmethod
    def get_autoincrement_type(self) -> Type[TypeEngine]:
        """Get the appropriate autoincrement integer type.
        
        Returns:
            SQLAlchemy type for autoincrement columns
        """
        pass
    
    @abstractmethod
    def configure_connection(self, connection: Connection) -> None:
        """Configure a new database connection with dialect-specific settings.
        
        Args:
            connection: SQLAlchemy connection to configure
        """
        pass
    
    @abstractmethod
    def configure_engine(self, engine: Engine) -> None:
        """Configure the engine after creation.
        
        Args:
            engine: SQLAlchemy engine to configure
        """
        pass
    
    @abstractmethod
    def get_connection_args(self) -> Dict[str, Any]:
        """Get dialect-specific connection arguments.
        
        Returns:
            Dictionary of connection arguments
        """
        pass
    
    @abstractmethod
    def get_pool_config(self) -> Dict[str, Any]:
        """Get recommended connection pool configuration.
        
        Returns:
            Dictionary of pool configuration parameters
        """
        pass
    
    @abstractmethod
    def handle_concurrent_access_error(self, error: Exception) -> bool:
        """Check if error is a concurrent access issue that should be retried.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error is retryable, False otherwise
        """
        pass
    
    @abstractmethod
    def get_table_info_query(self, table_name: str) -> str:
        """Get SQL query to retrieve table schema information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            SQL query string
        """
        pass
    
    @abstractmethod
    def get_index_info_query(self, table_name: str) -> str:
        """Get SQL query to retrieve index information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            SQL query string
        """
        pass
    
    @abstractmethod
    def supports_json_indexing(self) -> bool:
        """Check if this dialect supports indexing on JSON columns.
        
        Returns:
            True if JSON indexing is supported
        """
        pass
    
    @abstractmethod
    def get_lock_timeout_setting(self, timeout_ms: int) -> Optional[str]:
        """Get SQL statement to set lock timeout.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            SQL statement or None if not supported
        """
        pass
    
    @abstractmethod
    def get_datetime_type(self) -> Type[TypeEngine]:
        """Get the appropriate datetime column type.
        
        Returns:
            SQLAlchemy type for datetime storage
        """
        pass
    
    @abstractmethod
    def format_datetime_for_insert(self, dt) -> Any:
        """Format a datetime object for insertion.
        
        Args:
            dt: datetime object
            
        Returns:
            Formatted datetime value
        """
        pass