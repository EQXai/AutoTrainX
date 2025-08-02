"""Database factory for creating engines with appropriate dialects."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.pool import QueuePool, NullPool

from .dialects import AbstractDialect, SQLiteDialect, PostgreSQLDialect

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration container."""
    
    def __init__(self, 
                 db_type: str,
                 db_url: Optional[str] = None,
                 db_path: Optional[Path] = None,
                 **kwargs):
        """Initialize database configuration.
        
        Args:
            db_type: Type of database ('sqlite' or 'postgresql')
            db_url: Full database URL (for PostgreSQL)
            db_path: Path to database file (for SQLite)
            **kwargs: Additional configuration options
        """
        self.db_type = db_type.lower()
        self.db_url = db_url
        self.db_path = db_path
        self.options = kwargs
        
        # Validate configuration
        if self.db_type == 'sqlite' and not db_path:
            raise ValueError("SQLite requires db_path")
        elif self.db_type == 'postgresql' and not db_url:
            raise ValueError("PostgreSQL requires db_url")
        elif self.db_type not in ['sqlite', 'postgresql']:
            raise ValueError(f"Unsupported database type: {db_type}")


class DatabaseFactory:
    """Factory for creating database engines with appropriate dialects."""
    
    _dialects: Dict[str, AbstractDialect] = {
        'sqlite': SQLiteDialect(),
        'postgresql': PostgreSQLDialect(),
    }
    
    @classmethod
    def create_engine(cls, config: DatabaseConfig) -> Engine:
        """Create a database engine based on configuration.
        
        Args:
            config: Database configuration
            
        Returns:
            Configured SQLAlchemy engine
        """
        # Only show DB creation messages in debug mode or if explicitly requested
        verbose = config.options.get('verbose', False) or logger.isEnabledFor(logging.DEBUG)
        
        if verbose:
            print(f"🔧 Creating {config.db_type.upper()} engine...")
        
        dialect = cls._dialects.get(config.db_type)
        if not dialect:
            raise ValueError(f"Unsupported database type: {config.db_type}")
        
        # Build connection URL
        if config.db_type == 'sqlite':
            url = f"sqlite:///{config.db_path}"
        else:
            url = config.db_url
        
        if verbose:
            print(f"📍 Connection: {url[:50]}...")
        
        # Get dialect-specific configurations
        connect_args = dialect.get_connection_args()
        pool_config = dialect.get_pool_config()
        
        # Override with user-provided options
        connect_args.update(config.options.get('connect_args', {}))
        pool_config.update(config.options.get('pool_config', {}))
        
        # Choose appropriate pool class
        if config.db_type == 'sqlite':
            # SQLite doesn't benefit much from connection pooling
            poolclass = NullPool if config.options.get('no_pool', False) else QueuePool
        else:
            poolclass = QueuePool
        
        # Create engine with proper parameter mapping
        engine_kwargs = {
            'connect_args': connect_args,
            'poolclass': poolclass,
            'echo': config.options.get('echo', False),
        }
        
        # Map pool config parameters correctly
        if poolclass == QueuePool:
            if 'size' in pool_config:
                engine_kwargs['pool_size'] = pool_config.pop('size')
            if 'timeout' in pool_config:
                engine_kwargs['pool_timeout'] = pool_config.pop('timeout')
            if 'recycle' in pool_config:
                engine_kwargs['pool_recycle'] = pool_config.pop('recycle')
            if 'max_overflow' in pool_config:
                engine_kwargs['max_overflow'] = pool_config.pop('max_overflow')
            if 'pool_pre_ping' in pool_config:
                engine_kwargs['pool_pre_ping'] = pool_config.pop('pool_pre_ping')
        
        # Log engine configuration details silently
        engine = create_engine(url, **engine_kwargs)
        # Engine created
        
        # Skip connection event configuration for now to avoid recursion
        # Connection events configured
        
        # Apply engine-level configuration
        # Apply dialect configuration
        try:
            dialect.configure_engine(engine)
        except Exception as e:
            if verbose:
                print(f"[DatabaseFactory] Warning: Could not configure engine: {e}")
            logger.warning(f"Could not configure engine: {e}")
        
        # Use logging instead of print for this message
        logger.info(f"✅ {config.db_type.upper()} database ready")
        
        if verbose:
            print(f"✅ Database engine initialized successfully")
        return engine
    
    @classmethod
    def get_dialect(cls, db_type: str) -> AbstractDialect:
        """Get the dialect implementation for a database type.
        
        Args:
            db_type: Type of database
            
        Returns:
            Dialect implementation
        """
        dialect = cls._dialects.get(db_type.lower())
        if not dialect:
            raise ValueError(f"Unsupported database type: {db_type}")
        return dialect
    
    @classmethod
    def create_from_env(cls) -> Engine:
        """Create engine from environment variables.
        
        Environment variables:
            DATABASE_TYPE: 'sqlite' or 'postgresql'
            DATABASE_URL: Full database URL (for PostgreSQL)
            DATABASE_PATH: Path to database file (for SQLite)
            DATABASE_ECHO: Enable SQL echo (true/false)
        
        Returns:
            Configured engine
        """
        db_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
        
        if db_type == 'sqlite':
            db_path = os.environ.get('DATABASE_PATH')
            if not db_path:
                # Default to project DB directory
                db_dir = Path(__file__).parent.parent.parent / "DB"
                db_dir.mkdir(exist_ok=True)
                db_path = db_dir / "executions.db"
            config = DatabaseConfig(db_type='sqlite', db_path=Path(db_path))
        else:
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                raise ValueError("DATABASE_URL environment variable required for PostgreSQL")
            config = DatabaseConfig(db_type='postgresql', db_url=db_url)
        
        # Add echo option if specified
        if os.environ.get('DATABASE_ECHO', '').lower() == 'true':
            config.options['echo'] = True
        
        return cls.create_engine(config)