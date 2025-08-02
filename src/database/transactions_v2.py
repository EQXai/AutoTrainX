"""Transaction management with multi-database support."""

import logging
import time
from typing import Callable, Any, Optional, Dict
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

from .factory import DatabaseFactory

logger = logging.getLogger(__name__)


class TransactionManager:
    """Manage database transactions with retry logic and optimizations."""
    
    @staticmethod
    @contextmanager
    def atomic_transaction(session: Session):
        """Create an atomic transaction context.
        
        Args:
            session: Database session
            
        Yields:
            The session within a transaction
        """
        if not session.in_transaction():
            with session.begin():
                yield session
        else:
            yield session
    
    @staticmethod
    def with_retry(max_attempts: int = 3, delay: float = 0.1, 
                   backoff_factor: float = 2.0):
        """Decorator to retry database operations on lock/concurrency errors.
        
        Args:
            max_attempts: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            backoff_factor: Factor to multiply delay by after each retry
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                current_delay = delay
                
                # Get database type from the first session argument if available
                db_type = None
                for arg in args:
                    if hasattr(arg, 'bind') and hasattr(arg.bind, 'dialect'):
                        db_type = arg.bind.dialect.name
                        break
                
                # Get appropriate dialect for error handling
                dialect = None
                if db_type:
                    try:
                        dialect = DatabaseFactory.get_dialect(db_type)
                    except:
                        pass
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except OperationalError as e:
                        last_exception = e
                        
                        # Check if this is a retryable error
                        if dialect and dialect.handle_concurrent_access_error(e):
                            if attempt < max_attempts - 1:
                                logger.warning(
                                    f"Retryable database error on attempt {attempt + 1}/{max_attempts}: {e}"
                                )
                                time.sleep(current_delay)
                                current_delay *= backoff_factor
                                continue
                        
                        # Not retryable, raise immediately
                        raise
                    except Exception as e:
                        # Other exceptions are not retried
                        raise
                
                # Max attempts reached
                logger.error(f"Max retry attempts reached. Last error: {last_exception}")
                raise last_exception
            
            return wrapper
        return decorator
    
    @staticmethod
    def read_only_transaction(session: Session):
        """Mark a transaction as read-only for optimization.
        
        Args:
            session: Database session
        """
        db_type = session.bind.dialect.name
        
        if db_type == 'postgresql':
            session.execute("SET TRANSACTION READ ONLY")
        elif db_type == 'sqlite':
            # SQLite doesn't have explicit read-only transactions
            # but we can use deferred transaction mode
            session.execute("BEGIN DEFERRED")


class OptimisticLock:
    """Context manager for optimistic locking based on version/timestamp."""
    
    def __init__(self, model_instance: Any, version_field: str = 'updated_at'):
        """Initialize optimistic lock.
        
        Args:
            model_instance: SQLAlchemy model instance
            version_field: Field to use for version checking
        """
        self.model = model_instance
        self.version_field = version_field
        self.original_version = getattr(model_instance, version_field)
    
    def __enter__(self):
        """Enter context and record version."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Check version on exit."""
        if exc_type is None:  # No exception
            current_version = getattr(self.model, self.version_field)
            if current_version != self.original_version:
                raise IntegrityError(
                    "Optimistic lock failure: Record was modified by another process",
                    None, None
                )


class TransactionMetrics:
    """Collect metrics about transaction performance."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Dict[str, Any]] = {}
    
    @contextmanager
    def track_transaction(self, operation: str):
        """Track a transaction's performance.
        
        Args:
            operation: Name of the operation being tracked
        """
        start_time = time.time()
        
        try:
            yield
            # Success
            self._record_metric(operation, time.time() - start_time, success=True)
        except Exception as e:
            # Failure
            self._record_metric(operation, time.time() - start_time, success=False)
            raise
    
    def _record_metric(self, operation: str, duration: float, success: bool):
        """Record a metric for an operation.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            success: Whether the operation succeeded
        """
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'success_count': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0,
                'last_duration': 0.0,
                'last_success': None,
                'last_timestamp': None,
            }
        
        stats = self.metrics[operation]
        stats['count'] += 1
        stats['total_duration'] += duration
        stats['min_duration'] = min(stats['min_duration'], duration)
        stats['max_duration'] = max(stats['max_duration'], duration)
        stats['last_duration'] = duration
        stats['last_success'] = success
        stats['last_timestamp'] = datetime.utcnow()
        
        if success:
            stats['success_count'] += 1
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for operations.
        
        Args:
            operation: Specific operation to get stats for, or None for all
            
        Returns:
            Dictionary of statistics
        """
        if operation:
            stats = self.metrics.get(operation, {})
            if stats and stats['count'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['count']
                stats['success_rate'] = stats['success_count'] / stats['count']
            return stats
        else:
            # Return all stats
            all_stats = {}
            for op, stats in self.metrics.items():
                if stats['count'] > 0:
                    stats_copy = stats.copy()
                    stats_copy['avg_duration'] = stats['total_duration'] / stats['count']
                    stats_copy['success_rate'] = stats['success_count'] / stats['count']
                    all_stats[op] = stats_copy
            return all_stats
    
    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()


class DatabaseLockManager:
    """Manage database-level locks for different database types."""
    
    @staticmethod
    def acquire_advisory_lock(session: Session, lock_id: int, timeout: Optional[int] = None) -> bool:
        """Acquire an advisory lock (PostgreSQL only).
        
        Args:
            session: Database session
            lock_id: Numeric lock identifier
            timeout: Timeout in milliseconds (PostgreSQL only)
            
        Returns:
            True if lock acquired, False otherwise
        """
        db_type = session.bind.dialect.name
        
        if db_type == 'postgresql':
            if timeout:
                # Set lock timeout for this session
                session.execute(f"SET lock_timeout = {timeout}")
            
            try:
                # Try to acquire advisory lock
                result = session.execute(f"SELECT pg_try_advisory_lock({lock_id})").scalar()
                return bool(result)
            except OperationalError:
                return False
        else:
            # SQLite doesn't have advisory locks
            logger.warning("Advisory locks not supported on SQLite")
            return True
    
    @staticmethod
    def release_advisory_lock(session: Session, lock_id: int) -> bool:
        """Release an advisory lock (PostgreSQL only).
        
        Args:
            session: Database session
            lock_id: Numeric lock identifier
            
        Returns:
            True if lock released, False otherwise
        """
        db_type = session.bind.dialect.name
        
        if db_type == 'postgresql':
            result = session.execute(f"SELECT pg_advisory_unlock({lock_id})").scalar()
            return bool(result)
        else:
            # SQLite doesn't have advisory locks
            return True
    
    @staticmethod
    @contextmanager
    def with_advisory_lock(session: Session, lock_id: int, timeout: Optional[int] = None):
        """Context manager for advisory locks.
        
        Args:
            session: Database session
            lock_id: Numeric lock identifier
            timeout: Timeout in milliseconds
            
        Raises:
            OperationalError: If lock cannot be acquired
        """
        acquired = DatabaseLockManager.acquire_advisory_lock(session, lock_id, timeout)
        if not acquired:
            raise OperationalError("Could not acquire advisory lock", None, None)
        
        try:
            yield
        finally:
            DatabaseLockManager.release_advisory_lock(session, lock_id)