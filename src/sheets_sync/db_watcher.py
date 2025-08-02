"""Database watcher service for automatic Google Sheets synchronization.

This service monitors the database for changes and triggers synchronization 
to Google Sheets whenever data is modified. Supports both SQLite and PostgreSQL.
"""

import asyncio
import logging
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .integration import manual_full_sync
from ..config import Config
from ..database import DatabaseManager, db_settings

logger = logging.getLogger(__name__)


class DatabaseChangeHandler(FileSystemEventHandler):
    """Handles database file change events for SQLite."""
    
    def __init__(self, db_path: Path, sync_callback):
        """Initialize the database change handler.
        
        Args:
            db_path: Path to the database file
            sync_callback: Async callback to trigger synchronization
        """
        self.db_path = db_path
        self.sync_callback = sync_callback
        self._last_sync_time = None
        self._sync_interval = 3.0  # Minimum seconds between syncs
        self._pending_sync = False
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        # Check if the modified file is our database
        if Path(event.src_path).resolve() == self.db_path.resolve():
            # Debounce rapid changes
            current_time = datetime.now()
            if (self._last_sync_time is None or 
                (current_time - self._last_sync_time).total_seconds() >= self._sync_interval):
                
                self._last_sync_time = current_time
                logger.info("Database modification detected, triggering sync...")
                
                # Schedule sync callback
                asyncio.create_task(self.sync_callback())
            else:
                # Mark that we have a pending sync
                self._pending_sync = True
                logger.debug("Database modified, but sync is throttled")


class DatabaseWatcher:
    """Watches database for changes and triggers Google Sheets sync."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize the database watcher.
        
        Args:
            base_path: Base path for AutoTrainX project
        """
        self.base_path = Path(base_path or ".")
        self.observer = None
        self._running = False
        self._db_checksum = None
        self._sync_lock = asyncio.Lock()
        
        # Load configuration
        self.config = Config.load_config(str(self.base_path))
        self.sheets_config = self.config.get('google_sheets_sync', {})
        
        # Get database type from settings
        self.db_type = db_settings.db_type
        logger.info(f"Database type: {self.db_type}")
        
        # For SQLite, set up file path
        if self.db_type == "sqlite":
            self.db_path = self.base_path / "DB" / "executions.db"
            logger.info(f"SQLite database path: {self.db_path}")
        else:
            self.db_path = None
            logger.info(f"Using {self.db_type} database from connection settings")
        
    async def start(self):
        """Start watching the database for changes."""
        logger.info(f"Loading config from base_path: {self.base_path}")
        logger.info(f"Google Sheets config: {self.sheets_config}")
        
        if not self.sheets_config.get('enabled', False):
            logger.info("Google Sheets sync is disabled, not starting watcher")
            return
            
        if self.db_type == "sqlite" and self.db_path and not self.db_path.exists():
            logger.warning(f"SQLite database file not found: {self.db_path}")
            return
            
        if self._running:
            logger.warning("Database watcher is already running")
            return
            
        # Calculate initial checksum
        self._db_checksum = await self._calculate_db_checksum()
        
        # Set up monitoring based on database type
        if self.db_type == "sqlite" and self.db_path:
            # Use file system observer for SQLite
            self.observer = Observer()
            handler = DatabaseChangeHandler(self.db_path, self._handle_db_change)
            
            # Watch the parent directory of the database
            self.observer.schedule(handler, str(self.db_path.parent), recursive=False)
            self.observer.start()
            
            logger.info(f"Started watching SQLite database at: {self.db_path}")
        else:
            # For PostgreSQL and other databases, rely on periodic checking only
            logger.info(f"Started monitoring {self.db_type} database via periodic polling")
        
        self._running = True
        
        # Start periodic checksum verification
        asyncio.create_task(self._periodic_check())
        
    async def stop(self):
        """Stop watching the database."""
        if not self._running:
            return
            
        self._running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            
        logger.info("Stopped database watcher")
        
    async def _calculate_db_checksum(self) -> Optional[str]:
        """Calculate checksum of relevant database content."""
        try:
            # DatabaseManager handles connection based on current db_settings
            db_manager = DatabaseManager()
            
            # Get all records
            executions = db_manager.list_executions()
            variations = db_manager.list_variations()
            
            # Create a deterministic representation of the data
            data_repr = {
                'executions': [
                    {
                        'job_id': e.job_id,
                        'status': e.status,
                        'updated_at': e.updated_at.isoformat() if e.updated_at else None
                    } for e in executions
                ],
                'variations': [
                    {
                        'job_id': v.job_id,
                        'status': v.status,
                        'updated_at': v.updated_at.isoformat() if v.updated_at else None
                    } for v in variations
                ]
            }
            
            # Calculate checksum
            data_str = json.dumps(data_repr, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating database checksum: {e}")
            return None
            
    async def _periodic_check(self):
        """Periodically check database for changes that might be missed."""
        # Use shorter interval for non-SQLite databases
        check_interval = 10 if self.db_type == "sqlite" else 5
        
        while self._running:
            try:
                await asyncio.sleep(check_interval)
                
                # Calculate current checksum
                current_checksum = await self._calculate_db_checksum()
                
                if current_checksum and current_checksum != self._db_checksum:
                    logger.info(f"Database content change detected via checksum ({self.db_type})")
                    self._db_checksum = current_checksum
                    await self._handle_db_change()
                    
            except Exception as e:
                logger.error(f"Error in periodic check: {e}")
                
    async def _handle_db_change(self):
        """Handle database change by triggering sync."""
        async with self._sync_lock:
            try:
                logger.info(f"Triggering Google Sheets synchronization from {self.db_type} database...")
                
                # Perform full sync
                result = await manual_full_sync(str(self.base_path))
                
                if result.success:
                    logger.info(f"Sync completed: {result.message}")
                    if result.data:
                        logger.info(f"Synced {result.data.get('total_synced', 0)} records")
                else:
                    logger.error(f"Sync failed: {result.message}")
                    
            except Exception as e:
                logger.error(f"Error during sync: {e}")
                
    async def force_sync(self):
        """Force an immediate synchronization."""
        logger.info("Forcing immediate sync...")
        await self._handle_db_change()


class DatabaseWatcherService:
    """Service wrapper for database watcher."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize the service.
        
        Args:
            base_path: Base path for AutoTrainX project
        """
        self.watcher = DatabaseWatcher(base_path)
        self._service_task = None
        
    async def start(self):
        """Start the database watcher service."""
        await self.watcher.start()
        
    async def stop(self):
        """Stop the database watcher service."""
        await self.watcher.stop()
        
    async def run_forever(self):
        """Run the service forever."""
        await self.start()
        
        try:
            # Keep the service running
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()
            raise
            
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self.watcher._running


# Convenience functions

async def start_db_watcher(base_path: Optional[str] = None) -> DatabaseWatcherService:
    """Start the database watcher service.
    
    Args:
        base_path: Base path for AutoTrainX project
        
    Returns:
        DatabaseWatcherService instance
    """
    service = DatabaseWatcherService(base_path)
    await service.start()
    return service


async def stop_db_watcher(service: DatabaseWatcherService):
    """Stop the database watcher service.
    
    Args:
        service: Service instance to stop
    """
    if service:
        await service.stop()


def run_db_watcher_standalone(base_path: Optional[str] = None):
    """Run database watcher as a standalone process.
    
    Args:
        base_path: Base path for AutoTrainX project
    """
    import signal
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Log database configuration
    logger.info(f"Starting database watcher with {db_settings.db_type} backend")
    if db_settings.db_type == "postgresql":
        config = db_settings.to_dict()
        logger.info(f"PostgreSQL connection: {config.get('host')}:{config.get('port')}/{config.get('database')}")
    
    # Create service
    service = DatabaseWatcherService(base_path)
    
    # Handle shutdown signals
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping...")
        loop.create_task(service.stop())
        loop.stop()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run service
    logger.info("Starting database watcher service...")
    try:
        loop.run_until_complete(service.run_forever())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        loop.close()


if __name__ == "__main__":
    # Allow running as standalone script
    import sys
    base_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_db_watcher_standalone(base_path)