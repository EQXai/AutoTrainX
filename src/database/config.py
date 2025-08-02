"""Database configuration management."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings:
    """Centralized database configuration settings."""
    
    def __init__(self):
        """Initialize database settings from environment or defaults."""
        # Load from environment or use defaults
        self.db_type = os.environ.get('AUTOTRAINX_DB_TYPE', 'sqlite').lower()
        self.config_file = os.environ.get('AUTOTRAINX_DB_CONFIG')
        
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
        # Map of environment variables to config keys
        env_mapping = {
            'AUTOTRAINX_DB_PATH': 'path',
            'AUTOTRAINX_DB_HOST': 'host',
            'AUTOTRAINX_DB_PORT': 'port',
            'AUTOTRAINX_DB_NAME': 'database',
            'AUTOTRAINX_DB_USER': 'username',
            'AUTOTRAINX_DB_PASSWORD': 'password',
            'AUTOTRAINX_DB_ECHO': 'echo',
            'AUTOTRAINX_DB_POOL_SIZE': 'pool.size',
            'AUTOTRAINX_DB_POOL_OVERFLOW': 'pool.max_overflow',
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Handle nested keys
                if '.' in config_key:
                    keys = config_key.split('.')
                    target = self._config
                    for key in keys[:-1]:
                        target = target.setdefault(key, {})
                    # Convert types as needed
                    if keys[-1] in ['port', 'size', 'max_overflow']:
                        value = int(value)
                    elif keys[-1] == 'echo':
                        value = value.lower() == 'true'
                    target[keys[-1]] = value
                else:
                    # Convert types as needed
                    if config_key == 'port':
                        value = int(value)
                    elif config_key == 'echo':
                        value = value.lower() == 'true'
                    self._config[config_key] = value
    
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
        """Get connection pool configuration."""
        return self._config.get('pool', {})
    
    def is_echo_enabled(self) -> bool:
        """Check if SQL echo is enabled."""
        return self._config.get('echo', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary."""
        return self._config.copy()


# Global settings instance
db_settings = DatabaseSettings()