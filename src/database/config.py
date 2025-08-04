"""Database configuration management."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging
import sys

logger = logging.getLogger(__name__)

# Add parent directory to path to import secure_config
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from configuration.secure_config import secure_config
except ImportError as e:
    logger.warning(f"Failed to import secure_config: {e}")
    # Fallback if secure_config is not available
    class SecureConfigFallback:
        @property
        def database_config(self):
            return {
                'host': os.getenv('DATABASE_HOST', 'localhost'),
                'port': int(os.getenv('DATABASE_PORT', '5432')),
                'name': os.getenv('DATABASE_NAME', 'autotrainx'),
                'user': os.getenv('DATABASE_USER', 'autotrainx'),
                'password': os.getenv('DATABASE_PASSWORD'),  # No default password for security
                'echo': os.getenv('DATABASE_ECHO', 'false').lower() == 'true',
                'pool_size': int(os.getenv('DATABASE_POOL_SIZE', '10'))
            }
    secure_config = SecureConfigFallback()


class DatabaseSettings:
    """Centralized database configuration settings."""
    
    def __init__(self):
        """Initialize database settings from environment or defaults."""
        # Load from environment or use defaults
        self.db_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
        self.config_file = os.environ.get('DATABASE_CONFIG')
        
        # Load base configuration
        self._config = self._load_default_config()
        
        # Override with file config if specified
        if self.config_file and Path(self.config_file).exists():
            self._load_config_file(self.config_file)
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration based on database type."""
        base_path = Path(__file__).parent.parent.parent
        
        if self.db_type == 'sqlite':
            return {
                'type': 'sqlite',
                'path': str(base_path / 'DB' / 'executions.db'),
                'dataset_paths_db': str(base_path / 'DB' / 'dataset_paths.db'),
                'echo': False,
                'pool': {
                    'size': 5,
                    'max_overflow': 10,
                    'timeout': 30,
                    'recycle': 3600,
                },
            }
        elif self.db_type == 'postgresql':
            return {
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'autotrainx',
                'username': 'autotrainx',
                'password': None,
                'echo': False,
                'pool': {
                    'size': 10,
                    'max_overflow': 20,
                    'timeout': 30,
                    'recycle': 3600,
                },
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _load_config_file(self, path: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(path, 'r') as f:
                file_config = json.load(f)
                self._config.update(file_config)
                logger.info(f"Loaded database config from {path}")
        except Exception as e:
            logger.error(f"Failed to load config file {path}: {e}")
    
    def _load_env_overrides(self) -> None:
        """Override configuration with environment variables."""
        # Use secure config for database settings
        logger.debug(f"secure_config type: {type(secure_config).__name__}")
        db_config = secure_config.database_config
        logger.debug(f"db_config from secure_config: {db_config}")
        
        # Apply secure configuration
        if self.db_type == 'postgresql':
            self._config['host'] = db_config['host']
            self._config['port'] = db_config['port']
            self._config['database'] = db_config['name']
            self._config['username'] = db_config['user']
            self._config['password'] = db_config['password']
            self._config['echo'] = db_config['echo']
            self._config['pool']['size'] = db_config['pool_size']
        
        # No legacy support - all variables come from secure_config
    
    def get_connection_url(self) -> str:
        """Get database connection URL."""
        if self.db_type == 'sqlite':
            return f"sqlite:///{self._config['path']}"
        else:
            # Build PostgreSQL URL
            user = self._config['username']
            password = self._config.get('password', '')
            host = self._config['host']
            port = self._config['port']
            database = self._config['database']
            
            if password:
                return f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                return f"postgresql://{user}@{host}:{port}/{database}"
    
    def get_dataset_paths_url(self) -> str:
        """Get dataset paths database URL."""
        if self.db_type == 'sqlite':
            return f"sqlite:///{self._config['dataset_paths_db']}"
        else:
            # For PostgreSQL, use same database but different schema
            base_url = self.get_connection_url()
            # Could append schema parameter if needed
            return base_url
    
    def get_pool_config(self) -> Dict[str, Any]:
        """Get optimized connection pool configuration."""
        pool_config = self._config.get('pool', {})
        
        # Apply optimized defaults based on database type
        if self.db_type == 'sqlite':
            defaults = {
                'size': 1,  # SQLite is single-threaded
                'timeout': 30,
                'recycle': -1,  # Disable recycling
                'max_overflow': 0,
            }
        else:  # PostgreSQL
            defaults = {
                'size': 20,  # Increased for better concurrency
                'timeout': 30,
                'recycle': 3600,  # 1 hour
                'max_overflow': 30,  # Allow more overflow connections
                'pool_pre_ping': True,  # Validate connections
                'echo_pool': False,  # Disable pool echo by default
            }
        
        # Merge with user config
        for key, value in defaults.items():
            if key not in pool_config:
                pool_config[key] = value
        
        return pool_config
    
    def is_echo_enabled(self) -> bool:
        """Check if SQL echo is enabled."""
        return self._config.get('echo', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        return self._config.copy()


# Global settings instance
# This will be initialized when the module is imported
db_settings = DatabaseSettings()

# Function to reinitialize settings after environment changes
def reload_db_settings():
    """Reload database settings after environment variables change."""
    global db_settings
    db_settings = DatabaseSettings()
    return db_settings