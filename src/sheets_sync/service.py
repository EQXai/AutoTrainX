"""Simplified Google Sheets synchronization service for daemon.

This is a minimal version that only includes what's needed for the daemon.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .config import ConfigManager, SheetsSyncConfig

logger = logging.getLogger(__name__)


class SheetsSyncService:
    """Simplified Google Sheets sync service for daemon usage."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize service with minimal dependencies."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_manager = ConfigManager(self.base_path)
        self.config: Optional[SheetsSyncConfig] = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the service."""
        try:
            logger.info("Initializing simplified Google Sheets sync service...")
            
            # Load configuration
            self.config = self.config_manager.load_config()
            self._initialized = True
            
            logger.info("Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
            
    async def start(self) -> None:
        """Start the service (minimal implementation)."""
        if not self._initialized:
            await self.initialize()
            
        logger.info("Service started (simplified version)")
        
    async def stop(self) -> None:
        """Stop the service."""
        logger.info("Service stopped")
        self._initialized = False
        
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status."""
        return {
            "initialized": self._initialized,
            "base_path": str(self.base_path),
            "config_loaded": self.config is not None
        }
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            "healthy": self._initialized,
            "service": "simplified"
        }
        
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        if not self.config:
            return {"error": "No configuration loaded"}
            
        # Return basic config info from the Config class format
        config_data = self.config_manager._config
        if config_data and 'google_sheets_sync' in config_data:
            sheets_config = config_data['google_sheets_sync']
            return {
                "enabled": sheets_config.get('enabled', False),
                "spreadsheet_id": sheets_config.get('spreadsheet_id', 'Not configured')
            }
        return {"error": "Invalid configuration"}
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection (stub for daemon)."""
        return {
            "connected": False,
            "message": "Connection test not implemented in simplified service"
        }
        
    async def trigger_manual_sync(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Trigger manual sync (stub for daemon)."""
        return {
            "success": False,
            "message": "Manual sync should be triggered through integration.manual_full_sync()"
        }
        
    async def update_configuration(self, updates: Dict[str, Any]) -> None:
        """Update configuration (minimal implementation)."""
        logger.info(f"Configuration update requested: {updates}")
        # For daemon, we don't need full config updates
        pass