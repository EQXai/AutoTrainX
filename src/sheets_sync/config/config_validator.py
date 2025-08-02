"""Configuration validator for Google Sheets sync."""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# from ..base import ConfigurationError
from .sync_config import SheetsSyncConfig, ConfigurationError  # Import both from sync_config


logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates Google Sheets sync configuration."""
    
    @staticmethod
    def validate_config(config: SheetsSyncConfig) -> List[str]:
        """Validate configuration and return list of issues.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        try:
            # Basic validation
            config.validate()
            
            # Additional validation checks
            issues.extend(ConfigValidator._validate_auth_files(config))
            issues.extend(ConfigValidator._validate_spreadsheet_config(config))
            issues.extend(ConfigValidator._validate_worker_config(config))
            issues.extend(ConfigValidator._validate_table_configs(config))
            
        except ConfigurationError as e:
            issues.append(f"Configuration error: {e.message}")
        except Exception as e:
            issues.append(f"Unexpected validation error: {str(e)}")
        
        return issues
    
    @staticmethod
    def _validate_auth_files(config: SheetsSyncConfig) -> List[str]:
        """Validate authentication file configurations."""
        issues = []
        
        if not config.enabled:
            return issues
        
        auth_config = config.auth
        
        if auth_config.auth_type == "oauth2":
            # Check credentials file
            if auth_config.credentials_path:
                if not os.path.exists(auth_config.credentials_path):
                    issues.append(f"OAuth2 credentials file not found: {auth_config.credentials_path}")
                else:
                    # Validate credentials file format
                    try:
                        with open(auth_config.credentials_path, 'r') as f:
                            creds_data = json.load(f)
                        
                        if "client_id" not in creds_data.get("installed", {}):
                            issues.append("OAuth2 credentials file missing client_id")
                        if "client_secret" not in creds_data.get("installed", {}):
                            issues.append("OAuth2 credentials file missing client_secret")
                    
                    except json.JSONDecodeError:
                        issues.append("OAuth2 credentials file is not valid JSON")
                    except Exception as e:
                        issues.append(f"Error reading OAuth2 credentials file: {str(e)}")
            
            # Check token path directory
            if auth_config.token_path:
                token_dir = os.path.dirname(auth_config.token_path)
                if token_dir and not os.path.exists(token_dir):
                    issues.append(f"Token directory does not exist: {token_dir}")
        
        elif auth_config.auth_type == "service_account":
            # Check service account file
            if auth_config.service_account_path:
                if not os.path.exists(auth_config.service_account_path):
                    issues.append(f"Service account file not found: {auth_config.service_account_path}")
                else:
                    # Validate service account file format
                    try:
                        with open(auth_config.service_account_path, 'r') as f:
                            sa_data = json.load(f)
                        
                        required_fields = ["type", "project_id", "private_key_id", "private_key",
                                         "client_email", "client_id", "auth_uri", "token_uri"]
                        
                        for field in required_fields:
                            if field not in sa_data:
                                issues.append(f"Service account file missing required field: {field}")
                        
                        if sa_data.get("type") != "service_account":
                            issues.append("Service account file has incorrect type")
                    
                    except json.JSONDecodeError:
                        issues.append("Service account file is not valid JSON")
                    except Exception as e:
                        issues.append(f"Error reading service account file: {str(e)}")
        
        return issues
    
    @staticmethod
    def _validate_spreadsheet_config(config: SheetsSyncConfig) -> List[str]:
        """Validate spreadsheet configuration."""
        issues = []
        
        if not config.enabled:
            return issues
        
        spreadsheet_config = config.spreadsheet
        
        # Check for sheet name conflicts
        sheet_names = [
            spreadsheet_config.executions_sheet_name,
            spreadsheet_config.variations_sheet_name,
            spreadsheet_config.summary_sheet_name
        ]
        
        unique_names = set(sheet_names)
        if len(unique_names) != len(sheet_names):
            issues.append("Sheet names must be unique")
        
        # Validate sheet names (basic checks)
        for name in sheet_names:
            if len(name) > 100:  # Google Sheets limit
                issues.append(f"Sheet name too long (max 100 chars): {name}")
            
            if name.startswith("'") or name.endswith("'"):
                issues.append(f"Sheet name cannot start or end with single quote: {name}")
        
        return issues
    
    @staticmethod
    def _validate_worker_config(config: SheetsSyncConfig) -> List[str]:
        """Validate worker configuration."""
        issues = []
        
        if not config.enabled:
            return issues
        
        worker_config = config.workers
        
        # Check for reasonable worker counts
        total_workers = worker_config.realtime_workers + worker_config.background_workers
        
        if total_workers > 20:
            issues.append(f"Total worker count ({total_workers}) seems excessive (consider reducing)")
        
        # Check poll intervals
        if worker_config.realtime_poll_interval > 5.0:
            issues.append("Real-time poll interval is too high for responsive processing")
        
        if worker_config.background_poll_interval < 0.1:
            issues.append("Background poll interval is too low (may cause excessive CPU usage)")
        
        # Check batch size
        if worker_config.background_batch_size > 100:
            issues.append("Background batch size is very large (may cause memory issues)")
        
        return issues
    
    @staticmethod
    def _validate_table_configs(config: SheetsSyncConfig) -> List[str]:
        """Validate table-specific configurations."""
        issues = []
        
        if not config.enabled:
            return issues
        
        # Check if any tables are enabled
        enabled_tables = config.get_enabled_tables()
        if not enabled_tables:
            issues.append("No tables are enabled for sync")
        
        # Validate each table configuration
        for table_name, table_config in config.table_configs.items():
            prefix = f"Table '{table_name}'"
            
            # Check debounce settings
            if table_config.debounce_seconds > 60:
                issues.append(f"{prefix}: Debounce interval is very high ({table_config.debounce_seconds}s)")
            
            # Check batching with priorities
            if table_config.enable_batching and table_config.insert_priority == "critical":
                issues.append(f"{prefix}: Batching with critical priority may delay urgent operations")
        
        return issues
    
    @staticmethod
    def validate_file_permissions(config: SheetsSyncConfig) -> List[str]:
        """Validate file permissions for configuration files."""
        issues = []
        
        if not config.enabled:
            return issues
        
        files_to_check = []
        
        # Add auth files
        if config.auth.credentials_path:
            files_to_check.append(("OAuth2 credentials", config.auth.credentials_path))
        
        if config.auth.service_account_path:
            files_to_check.append(("Service account", config.auth.service_account_path))
        
        if config.auth.token_path:
            token_dir = os.path.dirname(config.auth.token_path)
            if token_dir:
                files_to_check.append(("Token directory", token_dir))
        
        # Check file permissions
        for file_type, file_path in files_to_check:
            if not os.path.exists(file_path):
                continue
            
            try:
                # Check read permissions
                if not os.access(file_path, os.R_OK):
                    issues.append(f"{file_type} file is not readable: {file_path}")
                
                # Check write permissions for token directory
                if file_type == "Token directory" and not os.access(file_path, os.W_OK):
                    issues.append(f"Token directory is not writable: {file_path}")
                
                # Check file permissions (warn if too permissive)
                if os.path.isfile(file_path):
                    stat_info = os.stat(file_path)
                    mode = stat_info.st_mode & 0o777
                    
                    if mode & 0o044:  # World/group readable
                        issues.append(f"{file_type} file has overly permissive permissions: {file_path}")
            
            except Exception as e:
                issues.append(f"Error checking permissions for {file_type} file: {str(e)}")
        
        return issues
    
    @staticmethod
    def get_config_recommendations(config: SheetsSyncConfig) -> List[str]:
        """Get configuration recommendations for optimization."""
        recommendations = []
        
        if not config.enabled:
            return recommendations
        
        # Worker recommendations
        worker_config = config.workers
        total_workers = worker_config.realtime_workers + worker_config.background_workers
        
        if total_workers < 2:
            recommendations.append("Consider using at least 2 workers for better performance")
        
        if worker_config.realtime_workers > 0 and worker_config.realtime_poll_interval > 1.0:
            recommendations.append("Consider reducing real-time poll interval for better responsiveness")
        
        # Queue recommendations
        queue_config = config.queue
        
        if queue_config.max_size < 1000:
            recommendations.append("Consider increasing queue size for handling traffic bursts")
        
        if queue_config.cleanup_interval_seconds > 7200:  # 2 hours
            recommendations.append("Consider more frequent queue cleanup to prevent memory growth")
        
        # Rate limit recommendations
        rate_config = config.rate_limit
        
        if rate_config.requests_per_minute > 90:
            recommendations.append("Consider reducing requests per minute to avoid API limits")
        
        # Table configuration recommendations
        enabled_tables = config.get_enabled_tables()
        
        if "executions" in enabled_tables and "variations" in enabled_tables:
            exec_config = config.get_table_config("executions")
            var_config = config.get_table_config("variations")
            
            if not var_config.enable_batching and exec_config.enable_batching:
                recommendations.append("Consider enabling batching for variations (they often come in groups)")
        
        # Monitoring recommendations
        if not config.monitoring.enabled:
            recommendations.append("Consider enabling monitoring for better observability")
        
        return recommendations