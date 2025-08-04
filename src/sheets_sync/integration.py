"""Integration helper for AutoTrainX Google Sheets sync."""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from .service import SheetsSyncService
from .config import ConfigManager


logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class AutoTrainXSheetsIntegration:
    """Helper class for integrating Google Sheets sync with AutoTrainX."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize integration helper.
        
        Args:
            base_path: Base path for AutoTrainX (None for auto-detection)
        """
        self.base_path = base_path
        self.service: Optional[SheetsSyncService] = None
        self._integration_task: Optional[asyncio.Task] = None
    
    async def setup_basic_sync(self, spreadsheet_id: str, auth_type: str = "oauth2",
                              credentials_path: Optional[str] = None,
                              service_account_path: Optional[str] = None) -> Dict[str, Any]:
        """Set up basic Google Sheets synchronization.
        
        Args:
            spreadsheet_id: ID of the Google Spreadsheet to sync to
            auth_type: Authentication type ("oauth2" or "service_account")
            credentials_path: Path to OAuth2 credentials JSON file
            service_account_path: Path to service account JSON file
            
        Returns:
            Setup result information
        """
        try:
            logger.info("Setting up Google Sheets synchronization...")
            
            # Initialize service
            self.service = SheetsSyncService(self.base_path)
            
            # Configure authentication
            auth_config = {"auth_type": auth_type}
            if auth_type == "oauth2" and credentials_path:
                auth_config["credentials_path"] = credentials_path
            elif auth_type == "service_account" and service_account_path:
                auth_config["service_account_path"] = service_account_path
            
            # Update configuration
            config_updates = {
                "enabled": True,
                "auth": auth_config,
                "spreadsheet": {"spreadsheet_id": spreadsheet_id}
            }
            
            await self.service.update_configuration(config_updates)
            
            # Initialize and start service
            await self.service.initialize()
            await self.service.start()
            
            logger.info("Google Sheets synchronization set up successfully")
            
            return {
                "success": True,
                "message": "Google Sheets sync enabled",
                "spreadsheet_id": spreadsheet_id,
                "auth_type": auth_type,
                "service_status": self.service.get_service_status()
            }
            
        except Exception as e:
            logger.error(f"Failed to set up Google Sheets sync: {e}")
            return {
                "success": False,
                "message": f"Setup failed: {str(e)}",
                "error": str(e)
            }
    
    async def disable_sync(self) -> Dict[str, Any]:
        """Disable Google Sheets synchronization.
        
        Returns:
            Disable result information
        """
        try:
            if self.service:
                await self.service.update_configuration({"enabled": False})
                await self.service.stop()
            
            logger.info("Google Sheets synchronization disabled")
            
            return {
                "success": True,
                "message": "Google Sheets sync disabled"
            }
            
        except Exception as e:
            logger.error(f"Failed to disable Google Sheets sync: {e}")
            return {
                "success": False,
                "message": f"Disable failed: {str(e)}",
                "error": str(e)
            }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status.
        
        Returns:
            Current sync status information
        """
        if not self.service:
            return {
                "initialized": False,
                "running": False,
                "message": "Service not initialized"
            }
        
        try:
            status = self.service.get_service_status()
            health = await self.service.get_health_status()
            
            return {
                **status,
                "health": health,
                "configuration": self.service.get_configuration_summary()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to get status: {str(e)}"
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Google Sheets.
        
        Returns:
            Connection test results
        """
        if not self.service:
            return {
                "success": False,
                "message": "Service not initialized"
            }
        
        return await self.service.test_connection()
    
    async def trigger_manual_sync(self, table_name: str = "executions") -> Dict[str, Any]:
        """Trigger manual synchronization.
        
        Args:
            table_name: Name of the table to sync
            
        Returns:
            Manual sync results
        """
        if not self.service:
            return {
                "success": False,
                "message": "Service not initialized"
            }
        
        return await self.service.trigger_manual_sync(table_name)
    
    def get_configuration_help(self) -> Dict[str, Any]:
        """Get help information for configuration.
        
        Returns:
            Configuration help information
        """
        return {
            "auth_types": {
                "oauth2": {
                    "description": "OAuth2 authentication using user consent",
                    "required_files": ["credentials.json (from Google Cloud Console)"],
                    "setup_steps": [
                        "1. Go to Google Cloud Console",
                        "2. Enable Google Sheets API",
                        "3. Create OAuth2 credentials",
                        "4. Download credentials.json file",
                        "5. Provide path to credentials file"
                    ]
                },
                "service_account": {
                    "description": "Service account authentication for automated access",
                    "required_files": ["service-account-key.json"],
                    "setup_steps": [
                        "1. Go to Google Cloud Console",
                        "2. Enable Google Sheets API",
                        "3. Create service account",
                        "4. Generate service account key",
                        "5. Download key JSON file",
                        "6. Share spreadsheet with service account email",
                        "7. Provide path to key file"
                    ]
                }
            },
            "spreadsheet_setup": [
                "1. Create a new Google Spreadsheet or use existing one",
                "2. Copy the spreadsheet ID from the URL",
                "3. If using service account, share spreadsheet with service account email",
                "4. Provide spreadsheet ID to the sync setup"
            ],
            "config_file_location": str(Path(self.base_path or ".") / "settings" / "config.json"),
            "example_config": {
                "sheets_sync": {
                    "enabled": True,
                    "auth": {
                        "auth_type": "oauth2",
                        "credentials_path": "/path/to/credentials.json"
                    },
                    "spreadsheet": {
                        "spreadsheet_id": "your-spreadsheet-id-here"
                    }
                }
            }
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.service:
            await self.service.stop()
        
        if self._integration_task:
            self._integration_task.cancel()
            try:
                await self._integration_task
            except asyncio.CancelledError:
                pass


# Convenience functions for easy integration

async def setup_sheets_sync(spreadsheet_id: str, auth_type: str = "oauth2",
                           credentials_path: Optional[str] = None,
                           service_account_path: Optional[str] = None,
                           base_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to set up Google Sheets sync.
    
    Args:
        spreadsheet_id: ID of the Google Spreadsheet
        auth_type: Authentication type ("oauth2" or "service_account")
        credentials_path: Path to OAuth2 credentials file
        service_account_path: Path to service account key file
        base_path: Base path for AutoTrainX
        
    Returns:
        Setup result information
    """
    integration = AutoTrainXSheetsIntegration(base_path)
    
    return await integration.setup_basic_sync(
        spreadsheet_id=spreadsheet_id,
        auth_type=auth_type,
        credentials_path=credentials_path,
        service_account_path=service_account_path
    )


async def get_sheets_sync_status(base_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get sync status.
    
    Args:
        base_path: Base path for AutoTrainX
        
    Returns:
        Current sync status
    """
    integration = AutoTrainXSheetsIntegration(base_path)
    integration.service = SheetsSyncService(base_path)
    
    try:
        await integration.service.initialize()
        return await integration.get_sync_status()
    except Exception as e:
        return {
            "error": str(e),
            "message": f"Failed to get status: {str(e)}"
        }
    finally:
        await integration.cleanup()


def get_setup_help() -> Dict[str, Any]:
    """Get help information for setting up Google Sheets sync.
    
    Returns:
        Setup help information
    """
    integration = AutoTrainXSheetsIntegration()
    return integration.get_configuration_help()


async def test_connection(base_path: Optional[str] = None) -> bool:
    """Test connection to Google Sheets.
    
    Args:
        base_path: Base path for AutoTrainX
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Simple direct test
        import json
        from pathlib import Path
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Get config
        config_path = Path(base_path or ".") / "settings" / "config.json"
        try:
            with open(config_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    logger.error("Config file is empty")
                    return False
                config = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return False
        except FileNotFoundError:
            logger.error("Config file not found")
            return False
        
        sheets_config = config.get('google_sheets_sync', {})
        spreadsheet_id = sheets_config.get('spreadsheet_id')
        
        if not spreadsheet_id:
            logger.error("No spreadsheet ID configured")
            return False
            
        # Create credentials using secure config
        from ..configuration.secure_config import secure_config
        
        google_creds = secure_config.google_credentials
        if not google_creds:
            logger.error("Google credentials not configured in environment")
            return False
            
        # Create credentials from dict instead of file
        credentials = service_account.Credentials.from_service_account_info(
            google_creds,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Try to access spreadsheet
        try:
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            if not spreadsheet:
                logger.error("Empty response from Google Sheets API")
                return False
            logger.info(f"Successfully accessed spreadsheet: {spreadsheet.get('properties', {}).get('title', 'Unknown')}")
            return True
        except Exception as api_error:
            logger.error(f"Google Sheets API error: {api_error}")
            return False
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


async def manual_full_sync(base_path: Optional[str] = None) -> SyncResult:
    """Perform manual full synchronization of all records.
    
    Args:
        base_path: Base path for AutoTrainX
        
    Returns:
        Sync result information
    """
    try:
        # Direct implementation for manual sync
        import json
        from pathlib import Path
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Get configuration
        config_path = Path(base_path or ".") / "settings" / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        sheets_config = config.get('google_sheets_sync', {})
        spreadsheet_id = sheets_config.get('spreadsheet_id')
        
        if not spreadsheet_id:
            return SyncResult(
                success=False,
                message="No spreadsheet ID configured",
                data=None
            )
        
        # Create credentials using secure config
        from ..configuration.secure_config import secure_config
        
        google_creds = secure_config.google_credentials
        if not google_creds:
            logger.error("Google credentials not configured in environment")
            return SyncResult(
                success=False,
                records_synced=0,
                errors=["Google credentials not configured"]
            )
            
        # Create credentials from dict instead of file
        credentials = service_account.Credentials.from_service_account_info(
            google_creds,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        # Get database records
        from src.database import DatabaseManager
        db_manager = DatabaseManager()
        
        # Sync executions
        executions_synced = 0
        executions = db_manager.list_executions()
        
        if executions:
            # Sort executions by created_at ascending (oldest first)
            executions.sort(key=lambda x: x.created_at if x.created_at else datetime.min)
            # Prepare headers
            headers = ['job_id', 'status', 'pipeline_mode', 'dataset_name', 'preset', 
                      'total_steps', 'start_time', 'end_time', 'duration_seconds', 
                      'success', 'error_message', 'output_path', 'created_at', 'updated_at']
            
            # Prepare data
            values = [headers]
            for exec in executions:
                row = [
                    exec.job_id,
                    exec.status,
                    exec.pipeline_mode,
                    exec.dataset_name,
                    exec.preset,
                    str(exec.total_steps) if exec.total_steps else '',
                    exec.start_time.isoformat() if exec.start_time else '',
                    exec.end_time.isoformat() if exec.end_time else '',
                    str(exec.duration_seconds) if exec.duration_seconds else '',
                    'TRUE' if exec.success else 'FALSE',
                    exec.error_message or '',
                    exec.output_path or '',
                    exec.created_at.isoformat() if exec.created_at else '',
                    exec.updated_at.isoformat() if exec.updated_at else ''
                ]
                values.append(row)
                executions_synced += 1
            
            # Clear existing data and write new data
            sheet_name = sheets_config.get('sheet_structure', {}).get('executions_sheet', 'Executions')
            
            # Create sheet if it doesn't exist
            try:
                spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheet_exists = any(s['properties']['title'] == sheet_name for s in spreadsheet.get('sheets', []))
                
                if not sheet_exists:
                    # Add new sheet
                    request = {
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': [request]}
                    ).execute()
            except:
                pass  # If error, assume sheet exists
            
            # Clear and update sheet
            range_name = f"{sheet_name}!A:Z"
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
        
        # Sync variations
        variations_synced = 0
        variations = db_manager.list_variations()
        
        if variations:
            # Sort variations by created_at ascending (oldest first)
            variations.sort(key=lambda x: x.created_at if x.created_at else datetime.min)
            # Similar process for variations
            headers = ['job_id', 'status', 'variation_id', 'experiment_name', 'dataset_name',
                      'preset', 'total_steps', 'total_combinations', 'varied_parameters',
                      'parameter_values', 'start_time', 'end_time', 'duration_seconds',
                      'success', 'error_message', 'output_path', 'parent_experiment_id',
                      'created_at', 'updated_at']
            
            values = [headers]
            for var in variations:
                row = [
                    var.job_id,
                    var.status,
                    var.variation_id,
                    var.experiment_name,
                    var.dataset_name,
                    var.preset,
                    str(var.total_steps) if var.total_steps else '',
                    str(var.total_combinations) if var.total_combinations else '',
                    var.varied_parameters or '',
                    var.parameter_values or '',
                    var.start_time.isoformat() if var.start_time else '',
                    var.end_time.isoformat() if var.end_time else '',
                    str(var.duration_seconds) if var.duration_seconds else '',
                    'TRUE' if var.success else 'FALSE',
                    var.error_message or '',
                    var.output_path or '',
                    var.parent_experiment_id or '',
                    var.created_at.isoformat() if var.created_at else '',
                    var.updated_at.isoformat() if var.updated_at else ''
                ]
                values.append(row)
                variations_synced += 1
            
            # Update variations sheet
            sheet_name = sheets_config.get('sheet_structure', {}).get('variations_sheet', 'Variations')
            
            # Create sheet if needed
            try:
                spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                sheet_exists = any(s['properties']['title'] == sheet_name for s in spreadsheet.get('sheets', []))
                
                if not sheet_exists:
                    request = {
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={'requests': [request]}
                    ).execute()
            except:
                pass
            
            # Clear and update
            range_name = f"{sheet_name}!A:Z"
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': values}
            ).execute()
        
        total_synced = executions_synced + variations_synced
        
        return SyncResult(
            success=True,
            message=f"Successfully synced {total_synced} records to Google Sheets",
            data={
                "total_synced": total_synced,
                "executions_synced": executions_synced,
                "variations_synced": variations_synced
            }
        )
        
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        import traceback
        traceback.print_exc()
        return SyncResult(
            success=False,
            message=f"Manual sync failed: {str(e)}",
            data=None
        )


async def get_sheets_sync_service(base_path: Optional[str] = None) -> Optional[SheetsSyncService]:
    """Get an initialized sheets sync service instance.
    
    Args:
        base_path: Base path for AutoTrainX
        
    Returns:
        Initialized SheetsSyncService or None if not configured
    """
    try:
        service = SheetsSyncService(base_path)
        await service.initialize()
        
        # Check if sync is enabled
        config = service.config_manager.get_config()
        if not config.enabled:
            await service.stop()
            return None
            
        return service
        
    except Exception as e:
        logger.error(f"Failed to get sync service: {e}")
        return None