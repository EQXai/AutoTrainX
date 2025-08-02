"""Database module for AutoTrainX execution tracking with multi-database support."""

from .enums import ExecutionStatus, PipelineMode

# Import v2 modules with backward compatibility
try:
    from .models_v2 import Execution, Variation, Base
    from .manager_v2 import DatabaseManager
    from .enhanced_manager_v2 import EnhancedDatabaseManager
    from .connection_pool_v2 import PooledDatabaseManager, ConnectionMonitor
    from .factory import DatabaseFactory, DatabaseConfig
    from .config import db_settings
    from .transactions_v2 import TransactionManager, TransactionMetrics, OptimisticLock
    from .schema_improvements_v2 import SchemaOptimizer
except ImportError:
    # Fallback to original modules if v2 not available
    from .models import Execution, Variation, Base
    from .manager import DatabaseManager
    from .enhanced_manager import EnhancedDatabaseManager
    from .connection_pool import PooledDatabaseManager, ConnectionMonitor
    from .transactions import TransactionManager, TransactionMetrics, OptimisticLock
    from .schema_improvements import SchemaOptimizer
    
    # Provide dummy factory and config for compatibility
    class DatabaseFactory:
        pass
    
    class DatabaseConfig:
        pass
    
    class db_settings:
        db_type = 'sqlite'

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