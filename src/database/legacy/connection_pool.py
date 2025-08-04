"""Enhanced connection pooling for AutoTrainX database."""

from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager
import threading
import time
import logging

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class PooledDatabaseManager:
    """Enhanced database manager with connection pooling and monitoring."""
    
    def __init__(self, db_path: Path, pool_config: Optional[Dict[str, Any]] = None):
        """Initialize pooled database manager.
        
        Args:
            db_path: Path to SQLite database
            pool_config: Optional pool configuration
        """
        self.db_path = db_path
        
        # Default pool configuration
        default_config = {
            'pool_size': 5,  # Number of connections to maintain
            'max_overflow': 10,  # Maximum overflow connections
            'pool_timeout': 30,  # Timeout for getting connection from pool
            'pool_recycle': 3600,  # Recycle connections after 1 hour
            'pool_pre_ping': True,  # Test connections before using
        }
        
        if pool_config:
            default_config.update(pool_config)
        
        # Create engine with pooling
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={'check_same_thread': False},
            poolclass=pool.QueuePool,
            **default_config
        )
        
        # Apply connection optimizations
        self._setup_connection_events()
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Connection statistics
        self._stats = {
            'connections_created': 0,
            'connections_closed': 0,
            'active_connections': 0,
            'connection_errors': 0,
            'last_error': None
        }
        self._stats_lock = threading.Lock()
    
    def _setup_connection_events(self):
        """Setup SQLAlchemy event handlers for connection lifecycle."""
        
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            """Configure each new connection."""
            # Enable WAL mode for better concurrency
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            dbapi_conn.execute("PRAGMA busy_timeout=10000")  # 10 second timeout
            dbapi_conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            dbapi_conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            dbapi_conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            
            with self._stats_lock:
                self._stats['connections_created'] += 1
                self._stats['active_connections'] += 1
        
        @event.listens_for(self.engine, "close")
        def on_close(dbapi_conn, connection_record):
            """Track connection closure."""
            with self._stats_lock:
                self._stats['connections_closed'] += 1
                self._stats['active_connections'] -= 1
        
        @event.listens_for(self.engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            """Validate connection on checkout from pool."""
            # Test connection is alive
            try:
                dbapi_conn.execute("SELECT 1")
            except Exception as e:
                # Connection is dead, invalidate it
                connection_proxy._pool.dispose()
                with self._stats_lock:
                    self._stats['connection_errors'] += 1
                    self._stats['last_error'] = str(e)
                raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            with self._stats_lock:
                self._stats['connection_errors'] += 1
                self._stats['last_error'] = str(e)
            raise
        finally:
            session.close()
    
    @contextmanager
    def bulk_session(self) -> Session:
        """Get a session optimized for bulk operations."""
        session = self.SessionLocal()
        # Disable autoflush for bulk operations
        session.autoflush = False
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        pool = self.engine.pool
        with self._stats_lock:
            return {
                'size': pool.size(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'total': pool.size() + pool.overflow(),
                'stats': self._stats.copy()
            }
    
    def dispose_pool(self):
        """Dispose of the connection pool."""
        self.engine.dispose()
        logger.info("Connection pool disposed")


class ConnectionMonitor:
    """Monitor database connections and performance."""
    
    def __init__(self, manager: PooledDatabaseManager):
        self.manager = manager
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self, interval: int = 60):
        """Start monitoring connections."""
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring connections."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, interval: int):
        """Monitor loop that logs connection statistics."""
        while self._monitoring:
            try:
                status = self.manager.get_pool_status()
                
                # Log if connections are exhausted
                if status['checked_out'] >= status['size']:
                    logger.warning(
                        f"Connection pool exhausted: {status['checked_out']}/{status['size']} "
                        f"(+{status['overflow']} overflow)"
                    )
                
                # Log periodic stats
                logger.debug(
                    f"DB Pool: {status['checked_out']}/{status['size']} active, "
                    f"{status['stats']['connections_created']} created, "
                    f"{status['stats']['connection_errors']} errors"
                )
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            time.sleep(interval)