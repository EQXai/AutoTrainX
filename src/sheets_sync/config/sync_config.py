"""Configuration class for Google Sheets synchronization."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# from ..base import ConfigurationError
# Define ConfigurationError locally to avoid dependency on base module
class ConfigurationError(Exception):
    """Configuration validation error."""
    def __init__(self, config_key: str, message: str):
        self.config_key = config_key
        self.message = message
        super().__init__(f"Configuration error for '{config_key}': {message}")


@dataclass
class AuthConfig:
    """Authentication configuration."""
    credentials_path: Optional[str] = None
    token_path: Optional[str] = None
    service_account_path: Optional[str] = None
    auth_type: str = "oauth2"  # "oauth2" or "service_account"
    
    def validate(self) -> None:
        """Validate authentication configuration."""
        if self.auth_type == "oauth2":
            if not self.credentials_path:
                raise ConfigurationError("credentials_path", "OAuth2 credentials path is required")
            if not os.path.exists(self.credentials_path):
                raise ConfigurationError("credentials_path", f"Credentials file not found: {self.credentials_path}")
        
        elif self.auth_type == "service_account":
            if not self.service_account_path:
                raise ConfigurationError("service_account_path", "Service account path is required")
            if not os.path.exists(self.service_account_path):
                raise ConfigurationError("service_account_path", f"Service account file not found: {self.service_account_path}")
        
        else:
            raise ConfigurationError("auth_type", f"Invalid auth type: {self.auth_type}")


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_100_seconds: int = 100
    burst_limit: int = 10
    
    def validate(self) -> None:
        """Validate rate limit configuration."""
        if self.requests_per_minute <= 0:
            raise ConfigurationError("requests_per_minute", "Must be positive")
        if self.requests_per_100_seconds <= 0:
            raise ConfigurationError("requests_per_100_seconds", "Must be positive")
        if self.burst_limit <= 0:
            raise ConfigurationError("burst_limit", "Must be positive")


@dataclass
class QueueConfig:
    """Queue configuration."""
    max_size: int = 10000
    cleanup_interval_seconds: int = 3600
    max_completed_age_seconds: int = 3600
    
    def validate(self) -> None:
        """Validate queue configuration."""
        if self.max_size <= 0:
            raise ConfigurationError("max_size", "Must be positive")
        if self.cleanup_interval_seconds <= 0:
            raise ConfigurationError("cleanup_interval_seconds", "Must be positive")
        if self.max_completed_age_seconds <= 0:
            raise ConfigurationError("max_completed_age_seconds", "Must be positive")


@dataclass
class WorkerConfig:
    """Worker configuration."""
    realtime_workers: int = 2
    background_workers: int = 3
    realtime_poll_interval: float = 0.5
    background_poll_interval: float = 2.0
    background_batch_size: int = 10
    
    def validate(self) -> None:
        """Validate worker configuration."""
        if self.realtime_workers < 0:
            raise ConfigurationError("realtime_workers", "Must be non-negative")
        if self.background_workers < 0:
            raise ConfigurationError("background_workers", "Must be non-negative")
        if self.realtime_workers + self.background_workers == 0:
            raise ConfigurationError("workers", "Must have at least one worker")
        if self.realtime_poll_interval <= 0:
            raise ConfigurationError("realtime_poll_interval", "Must be positive")
        if self.background_poll_interval <= 0:
            raise ConfigurationError("background_poll_interval", "Must be positive")
        if self.background_batch_size <= 0:
            raise ConfigurationError("background_batch_size", "Must be positive")


@dataclass
class SpreadsheetConfig:
    """Spreadsheet configuration."""
    spreadsheet_id: Optional[str] = None
    create_if_missing: bool = True
    spreadsheet_title: str = "AutoTrainX Data"
    executions_sheet_name: str = "Executions"
    variations_sheet_name: str = "Variations"
    summary_sheet_name: str = "Summary"
    
    def validate(self) -> None:
        """Validate spreadsheet configuration."""
        if not self.spreadsheet_title.strip():
            raise ConfigurationError("spreadsheet_title", "Cannot be empty")
        if not self.executions_sheet_name.strip():
            raise ConfigurationError("executions_sheet_name", "Cannot be empty")
        if not self.variations_sheet_name.strip():
            raise ConfigurationError("variations_sheet_name", "Cannot be empty")


@dataclass
class TableSyncConfig:
    """Configuration for table synchronization."""
    enabled: bool = True
    insert_priority: str = "medium"
    update_priority: str = "medium"
    delete_priority: str = "high"
    enable_batching: bool = False
    debounce_seconds: float = 0.0
    
    def validate(self) -> None:
        """Validate table sync configuration."""
        valid_priorities = ["low", "medium", "high", "critical"]
        
        if self.insert_priority not in valid_priorities:
            raise ConfigurationError("insert_priority", f"Must be one of: {valid_priorities}")
        if self.update_priority not in valid_priorities:
            raise ConfigurationError("update_priority", f"Must be one of: {valid_priorities}")
        if self.delete_priority not in valid_priorities:
            raise ConfigurationError("delete_priority", f"Must be one of: {valid_priorities}")
        if self.debounce_seconds < 0:
            raise ConfigurationError("debounce_seconds", "Must be non-negative")


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enabled: bool = True
    health_check_interval_seconds: int = 60
    metrics_retention_hours: int = 24
    alert_on_failures: bool = True
    max_consecutive_failures: int = 5
    
    def validate(self) -> None:
        """Validate monitoring configuration."""
        if self.health_check_interval_seconds <= 0:
            raise ConfigurationError("health_check_interval_seconds", "Must be positive")
        if self.metrics_retention_hours <= 0:
            raise ConfigurationError("metrics_retention_hours", "Must be positive")
        if self.max_consecutive_failures <= 0:
            raise ConfigurationError("max_consecutive_failures", "Must be positive")


@dataclass
class SheetsSyncConfig:
    """Main configuration class for Google Sheets synchronization."""
    
    # Core configuration
    enabled: bool = False
    
    # Sub-configurations
    auth: AuthConfig = field(default_factory=AuthConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)
    workers: WorkerConfig = field(default_factory=WorkerConfig)
    spreadsheet: SpreadsheetConfig = field(default_factory=SpreadsheetConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Table-specific configurations
    table_configs: Dict[str, TableSyncConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Set up default table configurations
        if not self.table_configs:
            self.table_configs = {
                "executions": TableSyncConfig(
                    enabled=True,
                    insert_priority="high",
                    update_priority="medium",
                    delete_priority="low",
                    enable_batching=False,
                    debounce_seconds=2.0
                ),
                "variations": TableSyncConfig(
                    enabled=True,
                    insert_priority="high",
                    update_priority="medium",
                    delete_priority="low",
                    enable_batching=True,
                    debounce_seconds=1.0
                )
            }
    
    def validate(self) -> None:
        """Validate the entire configuration."""
        if self.enabled:
            self.auth.validate()
            self.rate_limit.validate()
            self.queue.validate()
            self.workers.validate()
            self.spreadsheet.validate()
            self.monitoring.validate()
            
            for table_name, table_config in self.table_configs.items():
                try:
                    table_config.validate()
                except ConfigurationError as e:
                    raise ConfigurationError(f"table_configs.{table_name}.{e.config_key}", e.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, dict):
                return {k: dataclass_to_dict(v) for k, v in obj.items()}
            else:
                return obj
        
        return dataclass_to_dict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SheetsSyncConfig':
        """Create configuration from dictionary."""
        # Handle flat configuration structure from config.json
        if 'spreadsheet_id' in data or 'credentials_path' in data:
            # Convert flat structure to nested structure
            nested_data = cls._convert_flat_to_nested(data)
            return cls.from_dict(nested_data)
        
        # Extract main fields
        enabled = data.get('enabled', False)
        
        # Create sub-configurations
        auth = AuthConfig(**data.get('auth', {}))
        rate_limit = RateLimitConfig(**data.get('rate_limit', {}))
        queue = QueueConfig(**data.get('queue', {}))
        workers = WorkerConfig(**data.get('workers', {}))
        spreadsheet = SpreadsheetConfig(**data.get('spreadsheet', {}))
        monitoring = MonitoringConfig(**data.get('monitoring', {}))
        
        # Create table configurations
        table_configs = {}
        table_data = data.get('table_configs', {})
        for table_name, table_dict in table_data.items():
            table_configs[table_name] = TableSyncConfig(**table_dict)
        
        return cls(
            enabled=enabled,
            auth=auth,
            rate_limit=rate_limit,
            queue=queue,
            workers=workers,
            spreadsheet=spreadsheet,
            monitoring=monitoring,
            table_configs=table_configs
        )
    
    @classmethod
    def _convert_flat_to_nested(cls, flat_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat configuration to nested structure."""
        nested = {
            'enabled': flat_data.get('enabled', False),
            'auth': {},
            'spreadsheet': {},
            'rate_limit': {},
            'queue': {},
            'workers': {},
            'monitoring': {}
        }
        
        # Map spreadsheet_id
        if 'spreadsheet_id' in flat_data:
            nested['spreadsheet']['spreadsheet_id'] = flat_data['spreadsheet_id']
        
        # Map credentials_path to auth
        if 'credentials_path' in flat_data:
            # Determine auth type based on file content
            nested['auth']['service_account_path'] = flat_data['credentials_path']
            nested['auth']['auth_type'] = 'service_account'
        
        # Map sync_settings if present
        if 'sync_settings' in flat_data:
            settings = flat_data['sync_settings']
            
            # Map batch settings to queue
            if 'batch_size' in settings:
                nested['queue']['max_size'] = settings['batch_size'] * 10  # Allow buffer for queue
            # Note: batch_interval and retry attempts are worker settings, not queue settings
                
            # Map rate limiting
            if 'rate_limiting' in settings:
                nested['rate_limit'] = settings['rate_limiting']
                
            # Map worker settings
            if 'worker_settings' in settings:
                worker_settings = settings['worker_settings']
                # Map to appropriate worker counts
                max_workers = worker_settings.get('max_concurrent_operations', 3)
                nested['workers'] = {
                    'realtime_workers': 1 if worker_settings.get('realtime_worker_enabled', True) else 0,
                    'background_workers': max_workers - 1 if worker_settings.get('background_worker_enabled', True) else 0
                }
            
            # Map batch settings to workers
            if 'batch_size' in settings:
                nested['workers']['background_batch_size'] = settings['batch_size']
        
        # Map sheet structure if present
        if 'sheet_structure' in flat_data:
            structure = flat_data['sheet_structure']
            if 'executions_sheet' in structure:
                nested['spreadsheet']['executions_sheet_name'] = structure['executions_sheet']
            if 'variations_sheet' in structure:
                nested['spreadsheet']['variations_sheet_name'] = structure['variations_sheet']
        
        return nested
    
    @classmethod
    def from_file(cls, config_path: str) -> 'SheetsSyncConfig':
        """Load configuration from JSON file."""
        if not os.path.exists(config_path):
            raise ConfigurationError("config_file", f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Extract sheets sync configuration
            # Try both possible keys for backward compatibility
            sheets_config = data.get('google_sheets_sync', data.get('sheets_sync', {}))
            
            return cls.from_dict(sheets_config)
            
        except json.JSONDecodeError as e:
            raise ConfigurationError("config_file", f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise ConfigurationError("config_file", f"Error loading config file: {str(e)}")
    
    def save_to_file(self, config_path: str, merge_with_existing: bool = True) -> None:
        """Save configuration to JSON file."""
        config_data = {}
        
        # Load existing configuration if merging
        if merge_with_existing and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                # If loading fails, start with empty dict
                config_data = {}
        
        # Update with sheets sync configuration
        # Use google_sheets_sync to match the existing config structure
        config_data['google_sheets_sync'] = self.to_dict()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write configuration
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
    
    def get_table_config(self, table_name: str) -> TableSyncConfig:
        """Get configuration for a specific table."""
        return self.table_configs.get(table_name, TableSyncConfig())
    
    def set_table_config(self, table_name: str, config: TableSyncConfig) -> None:
        """Set configuration for a specific table."""
        self.table_configs[table_name] = config
    
    def is_table_enabled(self, table_name: str) -> bool:
        """Check if sync is enabled for a table."""
        if not self.enabled:
            return False
        
        table_config = self.get_table_config(table_name)
        return table_config.enabled
    
    def get_enabled_tables(self) -> List[str]:
        """Get list of enabled table names."""
        if not self.enabled:
            return []
        
        return [
            table_name for table_name, config in self.table_configs.items()
            if config.enabled
        ]