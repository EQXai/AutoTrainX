"""Transaction management utilities for AutoTrainX."""

from typing import Optional, Callable, Any, TypeVar, List
from contextlib import contextmanager
from functools import wraps
import time
import logging
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransactionManager:
    """Advanced transaction management with retry logic and deadlock handling."""
    
    @staticmethod
    @contextmanager
    def atomic_transaction(session: Session, read_only: bool = False):
        """Create an atomic transaction block with automatic rollback on failure.
        
        Args:
            session: Database session
            read_only: If True, sets transaction to read-only mode
        """
        # Set transaction isolation level
        if read_only:
            session.execute("BEGIN DEFERRED")  # Read-only transaction
        else:
            session.execute("BEGIN IMMEDIATE")  # Write transaction
        
        try:
            yield session
            if not read_only:
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            if read_only:
                session.rollback()  # Always rollback read-only transactions
    
    @staticmethod
    def with_retry(max_attempts: int = 3, delay: float = 0.1, backoff: float = 2.0):
        """Decorator for retrying database operations on transient failures.
        
        Args:
            max_attempts: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            backoff: Backoff multiplier for exponential backoff
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except OperationalError as e:
                        last_exception = e
                        if "database is locked" in str(e) and attempt < max_attempts - 1:
                            logger.warning(
                                f"Database locked, retrying in {current_delay}s "
                                f"(attempt {attempt + 1}/{max_attempts})"
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            raise
                    except Exception as e:
                        # Don't retry on non-transient errors
                        raise
                
                if last_exception:
                    raise last_exception
            
            return wrapper
        return decorator
    
    @staticmethod
    def batch_operation(session: Session, items: List[Any], 
                       batch_size: int = 100, operation: str = 'insert'):
        """Perform batch database operations efficiently.
        
        Args:
            session: Database session
            items: Items to process
            batch_size: Size of each batch
            operation: Type of operation ('insert', 'update', 'delete')
        """
        total_items = len(items)
        processed = 0
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            
            try:
                if operation == 'insert':
                    session.bulk_insert_mappings(type(batch[0]), batch)
                elif operation == 'update':
                    session.bulk_update_mappings(type(batch[0]), batch)
                elif operation == 'delete':
                    for item in batch:
                        session.delete(item)
                
                session.flush()  # Flush after each batch
                processed += len(batch)
                
                # Log progress for large batches
                if total_items > 1000:
                    logger.info(f"Processed {processed}/{total_items} items")
                    
            except Exception as e:
                logger.error(f"Batch operation failed at batch {i//batch_size}: {e}")
                session.rollback()
                raise
        
        session.commit()
        return processed


class OptimisticLock:
    """Implement optimistic locking for concurrent updates."""
    
    @staticmethod
    def update_with_version_check(session: Session, model_class, 
                                 job_id: str, updates: dict) -> bool:
        """Update a record with optimistic locking using version/timestamp.
        
        Args:
            session: Database session
            model_class: Model class (Execution or Variation)
            job_id: Job identifier
            updates: Dictionary of updates to apply
            
        Returns:
            True if update successful, False if version conflict
        """
        # Get current record with version
        record = session.query(model_class).filter_by(job_id=job_id).first()
        if not record:
            return False
        
        # Store current version
        current_version = record.updated_at
        
        # Apply updates
        for key, value in updates.items():
            setattr(record, key, value)
        
        # Update timestamp
        record.updated_at = datetime.utcnow()
        
        # Try to commit with version check
        try:
            # Use SQL to ensure atomic version check
            result = session.query(model_class).filter(
                model_class.job_id == job_id,
                model_class.updated_at == current_version
            ).update(updates)
            
            session.commit()
            return result > 0  # True if row was updated
            
        except Exception as e:
            session.rollback()
            logger.error(f"Optimistic lock update failed: {e}")
            return False


class TransactionMetrics:
    """Track transaction performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'retry_count': 0,
            'total_duration': 0.0,
            'lock_timeouts': 0
        }
    
    @contextmanager
    def track_transaction(self, operation_name: str):
        """Track a transaction's performance."""
        start_time = time.time()
        
        try:
            self.metrics['total_transactions'] += 1
            yield
            self.metrics['successful_transactions'] += 1
        except OperationalError as e:
            self.metrics['failed_transactions'] += 1
            if "database is locked" in str(e):
                self.metrics['lock_timeouts'] += 1
            raise
        except Exception:
            self.metrics['failed_transactions'] += 1
            raise
        finally:
            duration = time.time() - start_time
            self.metrics['total_duration'] += duration
            
            if duration > 1.0:  # Log slow transactions
                logger.warning(f"Slow transaction '{operation_name}': {duration:.2f}s")
    
    def get_metrics(self) -> dict:
        """Get transaction metrics."""
        metrics = self.metrics.copy()
        
        if metrics['total_transactions'] > 0:
            metrics['average_duration'] = (
                metrics['total_duration'] / metrics['total_transactions']
            )
            metrics['success_rate'] = (
                metrics['successful_transactions'] / metrics['total_transactions']
            )
        else:
            metrics['average_duration'] = 0.0
            metrics['success_rate'] = 0.0
        
        return metrics