"""Connection pool manager with multi-database support."""

import logging
import threading
import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, Engine, event, pool
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool

from .factory import DatabaseFactory, DatabaseConfig
from .config import db_settings
from .utils.singleton_logger import singleton_logger

logger = logging.getLogger(__name__)


class PooledDatabaseManager:
    """Database manager with advanced connection pooling."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None, 
                 pool_config: Optional[Dict[str, Any]] = None):
        """Initialize pooled database manager.
        
        Args:
            config: Database configuration
            pool_config: Override pool configuration
        """
        if config is None:
            # Create config from environment/settings
            if db_settings.db_type == 'sqlite':
                db_path = db_settings.get_connection_url().replace('sqlite:///', '')
                config = DatabaseConfig(
                    db_type='sqlite',
                    db_path=db_path,
                    echo=db_settings.is_echo_enabled()
                )
            else:
                config = DatabaseConfig(
                    db_type='postgresql',
                    db_url=db_settings.get_connection_url(),
                    echo=db_settings.is_echo_enabled()
                )
        
        self.config = config
        self.dialect = DatabaseFactory.get_dialect(config.db_type)
        
        # Override pool config if provided
        if pool_config:
            config.options['pool_config'] = pool_config
        
        # Create engine with factory
        self.engine = DatabaseFactory.create_engine(config)
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Track pool statistics
        self._pool_stats = {
            'connections_created': 0,
            'connections_recycled': 0,
            'connections_invalidated': 0,
            'connection_errors': 0,
        }
        
        # Register pool event listeners
        self._register_pool_events()
        
        singleton_logger.debug_once(f"Pooled database manager initialized with {config.db_type}")
    
    def _register_pool_events(self):
        """Register event listeners for pool monitoring."""
        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Track new connections."""
            self._pool_stats['connections_created'] += 1
            connection_record.info['connect_time'] = time.time()
            logger.debug(f"New connection created: {id(dbapi_conn)}")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Track connection checkouts."""
            checkout_time = time.time()
            connection_record.info['checkout_time'] = checkout_time
            logger.debug(f"Connection checked out: {id(dbapi_conn)}")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Track connection checkins."""
            if 'checkout_time' in connection_record.info:
                duration = time.time() - connection_record.info['checkout_time']
                logger.debug(f"Connection checked in after {duration:.3f}s: {id(dbapi_conn)}")
                del connection_record.info['checkout_time']
        
        @event.listens_for(self.engine, "invalidate")
        def receive_invalidate(dbapi_conn, connection_record, exception):
            """Track connection invalidations."""
            self._pool_stats['connections_invalidated'] += 1
            if exception:
                self._pool_stats['connection_errors'] += 1
                logger.warning(f"Connection invalidated due to error: {exception}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    @contextmanager
    def bulk_session(self) -> Session:
        """Get a session optimized for bulk operations."""
        session = self.SessionLocal()
        try:
            # Disable autoflush for bulk operations
            session.autoflush = False
            # Use bulk operations
            session.bulk_insert_mappings = True
            session.bulk_update_mappings = True
            yield session
        finally:
            session.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed pool status."""
        pool = self.engine.pool
        
        status = {
            'type': type(pool).__name__,
            'database_type': self.config.db_type,
        }
        
        # Pool statistics (available for QueuePool)
        if hasattr(pool, 'size'):
            status.update({
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'total': pool.total(),
            })
        
        # Add our custom statistics
        status.update(self._pool_stats)
        
        # Also add stats under 'stats' key for backward compatibility
        status['stats'] = self._pool_stats.copy()
        
        return status
    
    def reset_pool(self):
        """Reset the connection pool."""
        logger.info("Resetting connection pool")
        self.engine.dispose()
        self._pool_stats['connections_recycled'] += self._pool_stats.get('connections_created', 0)
        logger.info("Connection pool reset complete")
    
    def close(self):
        """Close the database manager and cleanup resources."""
        logger.info("Closing pooled database manager")
        self.engine.dispose()


class ConnectionMonitor:
    """Monitor database connections and performance."""
    
    def __init__(self, manager: PooledDatabaseManager):
        """Initialize connection monitor.
        
        Args:
            manager: The database manager to monitor
        """
        self.manager = manager
        self._monitoring = False
        self._monitor_thread = None
        self._metrics = {
            'total_queries': 0,
            'slow_queries': 0,
            'errors': 0,
            'last_check': None,
        }
    
    def start_monitoring(self, interval: int = 60):
        """Start monitoring in a background thread.
        
        Args:
            interval: Check interval in seconds
        """
        if self._monitoring:
            logger.warning("Monitoring already started")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        singleton_logger.info_once(f"Connection monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Connection monitoring stopped")
    
    def _monitor_loop(self, interval: int):
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._check_pool_health()
                self._metrics['last_check'] = datetime.utcnow()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self._metrics['errors'] += 1
    
    def _check_pool_health(self):
        """Check connection pool health."""
        status = self.manager.get_pool_status()
        
        # Log pool status
        logger.debug(f"Pool status: {status}")
        
        # Check for potential issues
        if status.get('checked_out', 0) > status.get('size', 0) * 0.8:
            logger.warning("Connection pool usage high: %d/%d connections in use",
                         status['checked_out'], status['size'])
        
        if status.get('connection_errors', 0) > 10:
            logger.error("High number of connection errors: %d",
                        status['connection_errors'])
        
        # Check database-specific health
        try:
            with self.manager.get_session() as session:
                if self.manager.config.db_type == 'sqlite':
                    # Check WAL size for SQLite
                    from sqlalchemy import text
                    result = session.execute(text("PRAGMA wal_checkpoint(PASSIVE)")).fetchone()
                    if result and result[1] > 1000:  # More than 1000 pages
                        logger.warning(f"SQLite WAL size large: {result[1]} pages")
                else:
                    # PostgreSQL health check
                    from sqlalchemy import text
                    result = session.execute(text("""
                        SELECT count(*) 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)).scalar()
                    if result > 50:
                        logger.warning(f"High number of active PostgreSQL connections: {result}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._metrics['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get monitoring metrics."""
        metrics = self._metrics.copy()
        metrics['pool_status'] = self.manager.get_pool_status()
        return metrics