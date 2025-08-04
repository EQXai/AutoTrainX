"""Configuration manager for Google Sheets sync."""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from ...config import Config  # Import from existing AutoTrainX config
# from ..base import ConfigurationError
from .sync_config import SheetsSyncConfig, ConfigurationError  # Import ConfigurationError from sync_config
from .config_validator import ConfigValidator


logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages Google Sheets sync configuration."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            base_path: Base path for AutoTrainX (None for auto-detection)
        """
        self.base_path = base_path or Config.get_default_base_path()
        self._config: Optional[SheetsSyncConfig] = None
        self._config_path: Optional[str] = None
    
    def load_config(self, config_path: Optional[str] = None) -> SheetsSyncConfig:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file (None for default)
            
        Returns:
            Loaded configuration
            
        Raises:
            ConfigurationError: If configuration loading fails
        """
        if config_path is None:
            config_path = self._get_default_config_path()
        
        self._config_path = config_path
        
        try:
            if os.path.exists(config_path):
                logger.info(f"Loading sheets sync configuration from: {config_path}")
                self._config = SheetsSyncConfig.from_file(config_path)
            else:
                logger.info("No sheets sync configuration found, using defaults")
                self._config = SheetsSyncConfig()
            
            # Validate configuration
            issues = ConfigValidator.validate_config(self._config)
            if issues:
                logger.warning(f"Configuration validation issues: {issues}")
                # Don't fail on validation issues, just warn
            
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load sheets sync configuration: {e}")
            raise ConfigurationError("config_loading", f"Failed to load configuration: {str(e)}")
    
    def save_config(self, config: Optional[SheetsSyncConfig] = None, 
                   config_path: Optional[str] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save (None to use current)
            config_path: Path to save to (None for default)
            
        Raises:
            ConfigurationError: If configuration saving fails
        """
        if config is None:
            config = self._config
        
        if config is None:
            raise ConfigurationError("save_config", "No configuration to save")
        
        if config_path is None:
            config_path = self._config_path or self._get_default_config_path()
        
        try:
            logger.info(f"Saving sheets sync configuration to: {config_path}")
            config.save_to_file(config_path, merge_with_existing=True)
            
            self._config = config
            self._config_path = config_path
            
        except Exception as e:
            logger.error(f"Failed to save sheets sync configuration: {e}")
            raise ConfigurationError("save_config", f"Failed to save configuration: {str(e)}")
    
    def get_config(self) -> SheetsSyncConfig:
        """Get current configuration.
        
        Returns:
            Current configuration
        """
        if self._config is None:
            self._config = self.load_config()
        
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> SheetsSyncConfig:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
            
        Returns:
            Updated configuration
        """
        config = self.get_config()
        
        # Convert current config to dict, update, and create new config
        config_dict = config.to_dict()
        self._deep_update(config_dict, updates)
        
        # Create new configuration from updated dict
        new_config = SheetsSyncConfig.from_dict(config_dict)
        
        # Validate new configuration
        issues = ConfigValidator.validate_config(new_config)
        if issues:
            raise ConfigurationError("update_config", f"Configuration validation failed: {issues}")
        
        self._config = new_config
        return new_config
    
    def enable_sync(self, spreadsheet_id: Optional[str] = None) -> None:
        """Enable Google Sheets sync.
        
        Args:
            spreadsheet_id: ID of the spreadsheet to sync to
        """
        updates = {"enabled": True}
        
        if spreadsheet_id:
            updates["spreadsheet"] = {"spreadsheet_id": spreadsheet_id}
        
        self.update_config(updates)
        logger.info("Enabled Google Sheets sync")
    
    def disable_sync(self) -> None:
        """Disable Google Sheets sync."""
        self.update_config({"enabled": False})
        logger.info("Disabled Google Sheets sync")
    
    def configure_auth(self, auth_type: str, **auth_params) -> None:
        """Configure authentication settings.
        
        Args:
            auth_type: Type of authentication ("oauth2" or "service_account")
            **auth_params: Authentication parameters
        """
        auth_config = {"auth_type": auth_type}
        auth_config.update(auth_params)
        
        self.update_config({"auth": auth_config})
        logger.info(f"Configured {auth_type} authentication")
    
    def configure_spreadsheet(self, spreadsheet_id: str, **spreadsheet_params) -> None:
        """Configure spreadsheet settings.
        
        Args:
            spreadsheet_id: ID of the spreadsheet
            **spreadsheet_params: Additional spreadsheet parameters
        """
        spreadsheet_config = {"spreadsheet_id": spreadsheet_id}
        spreadsheet_config.update(spreadsheet_params)
        
        self.update_config({"spreadsheet": spreadsheet_config})
        logger.info(f"Configured spreadsheet: {spreadsheet_id}")
    
    def configure_table(self, table_name: str, **table_params) -> None:
        """Configure table-specific settings.
        
        Args:
            table_name: Name of the table
            **table_params: Table configuration parameters
        """
        updates = {
            "table_configs": {
                table_name: table_params
            }
        }
        
        self.update_config(updates)
        logger.info(f"Configured table settings for: {table_name}")
    
    def enable_table_sync(self, table_name: str) -> None:
        """Enable sync for a specific table.
        
        Args:
            table_name: Name of the table
        """
        self.configure_table(table_name, enabled=True)
    
    def disable_table_sync(self, table_name: str) -> None:
        """Disable sync for a specific table.
        
        Args:
            table_name: Name of the table
        """
        self.configure_table(table_name, enabled=False)
    
    def validate_current_config(self) -> List[str]:
        """Validate current configuration.
        
        Returns:
            List of validation issues
        """
        config = self.get_config()
        return ConfigValidator.validate_config(config)
    
    def get_config_recommendations(self) -> List[str]:
        """Get configuration recommendations.
        
        Returns:
            List of recommendations
        """
        config = self.get_config()
        return ConfigValidator.get_config_recommendations(config)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration.
        
        Returns:
            Configuration summary
        """
        config = self.get_config()
        
        return {
            "enabled": config.enabled,
            "auth_type": config.auth.auth_type,
            "spreadsheet_id": config.spreadsheet.spreadsheet_id,
            "enabled_tables": config.get_enabled_tables(),
            "total_workers": config.workers.realtime_workers + config.workers.background_workers,
            "monitoring_enabled": config.monitoring.enabled,
            "validation_issues": self.validate_current_config(),
            "recommendations": self.get_config_recommendations()
        }
    
    def reset_to_defaults(self) -> SheetsSyncConfig:
        """Reset configuration to defaults.
        
        Returns:
            New default configuration
        """
        self._config = SheetsSyncConfig()
        logger.info("Reset sheets sync configuration to defaults")
        return self._config
    
    def export_config(self, export_path: str, include_sensitive: bool = False) -> None:
        """Export configuration to a file.
        
        Args:
            export_path: Path to export configuration to
            include_sensitive: Whether to include sensitive information
        """
        config = self.get_config()
        config_dict = config.to_dict()
        
        if not include_sensitive:
            # Remove sensitive information
            if "auth" in config_dict:
                auth_dict = config_dict["auth"]
                for sensitive_key in ["credentials_path", "service_account_path", "token_path"]:
                    if sensitive_key in auth_dict:
                        auth_dict[sensitive_key] = "[REDACTED]"
        
        # Save as standalone sheets sync config
        standalone_config = {"sheets_sync": config_dict}
        
        import json
        with open(export_path, 'w') as f:
            json.dump(standalone_config, f, indent=2, default=str)
        
        logger.info(f"Exported configuration to: {export_path}")
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        return str(Path(self.base_path) / "settings" / "config.json")
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """Deep update a dictionary with another dictionary.
        
        Args:
            base_dict: Base dictionary to update
            update_dict: Dictionary with updates
        """
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    @property
    def config_path(self) -> Optional[str]:
        """Get current configuration file path."""
        return self._config_path
    
    @property
    def is_loaded(self) -> bool:
        """Check if configuration is loaded."""
        return self._config is not None