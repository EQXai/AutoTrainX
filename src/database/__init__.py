"""Database module for AutoTrainX execution tracking with multi-database support."""

from .enums import ExecutionStatus, PipelineMode

# Import consolidated modules
from .models import Execution, Variation, Base
from .manager import EnhancedDatabaseManager
from .connection_pool import PooledDatabaseManager, ConnectionMonitor
from .factory import DatabaseFactory, DatabaseConfig
from .config import db_settings
from .transactions import TransactionManager, TransactionMetrics, OptimisticLock
from .schema_improvements_v2 import SchemaOptimizer

# Alias for backward compatibility
DatabaseManager = EnhancedDatabaseManager

__all__ = [
    # Enums
    'ExecutionStatus',
    'PipelineMode',
    
    # Models
    'Execution',
    'Variation',
    'Base',
    
    # Managers
    'DatabaseManager',
    'EnhancedDatabaseManager',
    'PooledDatabaseManager',
    'ConnectionMonitor',
    
    # Factory and Config
    'DatabaseFactory',
    'DatabaseConfig',
    'db_settings',
    
    # Transactions
    'TransactionManager',
    'TransactionMetrics',
    'OptimisticLock',
    
    # Optimizations
    'SchemaOptimizer',
]