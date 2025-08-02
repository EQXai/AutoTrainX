"""Google Sheets synchronization system for AutoTrainX.

This package provides real-time synchronization of training execution data
to Google Sheets for monitoring and analysis purposes.
"""

# Temporarily comment out .base imports until we refactor service.py
# from .base import SyncInterface, SyncResult, SyncException
from .config import SheetsSyncConfig
from .service import SheetsSyncService
from .integration import AutoTrainXSheetsIntegration, setup_sheets_sync, get_sheets_sync_status, get_setup_help, SyncResult
# from .start_watcher import start_integrated_watcher, stop_integrated_watcher  # Removed - daemon runs independently
from .db_watcher import DatabaseWatcher, DatabaseWatcherService

__all__ = [
    # 'SyncInterface',  # Temporarily disabled
    'SyncResult', 
    # 'SyncException',  # Temporarily disabled
    'SheetsSyncConfig',
    'SheetsSyncService',
    'AutoTrainXSheetsIntegration',
    'setup_sheets_sync',
    'get_sheets_sync_status',
    'get_setup_help',
    # 'start_integrated_watcher',  # Removed
    # 'stop_integrated_watcher',  # Removed
    'DatabaseWatcher',
    'DatabaseWatcherService'
]

__version__ = '1.0.0'