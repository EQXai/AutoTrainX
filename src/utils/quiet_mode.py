"""
Quiet mode utilities for AutoTrainX
Prevents database initialization logs from interfering with UI output
"""
import logging
import sys
import contextlib
from io import StringIO
from typing import Generator

class QuietLogger:
    """Context manager to temporarily suppress specific log messages"""
    
    def __init__(self, 
                 logger_names: list = None, 
                 level: int = logging.WARNING,
                 suppress_stdout: bool = False):
        """
        Args:
            logger_names: List of logger names to quiet (default: database loggers)
            level: Minimum log level to show (WARNING and above by default)
            suppress_stdout: Whether to also suppress stdout
        """
        self.logger_names = logger_names or [
            'src.database.factory',
            'src.database.manager_v2',
            'sqlalchemy.engine',
            'sqlalchemy.pool'
        ]
        self.new_level = level
        self.original_levels = {}
        self.suppress_stdout = suppress_stdout
        self.original_stdout = None
        self.stdout_buffer = None
        
    def __enter__(self):
        # Save original log levels and set to new level
        for logger_name in self.logger_names:
            logger = logging.getLogger(logger_name)
            self.original_levels[logger_name] = logger.level
            logger.setLevel(self.new_level)
        
        # Optionally suppress stdout
        if self.suppress_stdout:
            self.original_stdout = sys.stdout
            self.stdout_buffer = StringIO()
            sys.stdout = self.stdout_buffer
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original log levels
        for logger_name, original_level in self.original_levels.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(original_level)
        
        # Restore stdout if suppressed
        if self.suppress_stdout and self.original_stdout:
            sys.stdout = self.original_stdout
    
    def get_captured_output(self) -> str:
        """Get captured stdout content if suppress_stdout was True"""
        if self.stdout_buffer:
            return self.stdout_buffer.getvalue()
        return ""

class DatabaseQuietMode(QuietLogger):
    """Specialized quiet mode for database operations"""
    
    def __init__(self, completely_silent: bool = False):
        """
        Args:
            completely_silent: If True, suppress all database output including stdout
        """
        super().__init__(
            logger_names=[
                'src.database.factory',
                'src.database.manager_v2',
                'src.database.config',
                'sqlalchemy.engine',
                'sqlalchemy.pool',
                'sqlalchemy.dialects'
            ],
            level=logging.ERROR if completely_silent else logging.WARNING,
            suppress_stdout=completely_silent
        )

@contextlib.contextmanager
def quiet_database_init() -> Generator[None, None, None]:
    """Context manager to suppress database initialization output"""
    with DatabaseQuietMode(completely_silent=True):
        yield

@contextlib.contextmanager
def quiet_database_operations() -> Generator[None, None, None]:
    """Context manager to suppress routine database operation logs"""
    with DatabaseQuietMode(completely_silent=False):
        yield

# Decorator versions
def quiet_db_init(func):
    """Decorator to suppress database output during function execution"""
    def wrapper(*args, **kwargs):
        with quiet_database_init():
            return func(*args, **kwargs)
    return wrapper

def quiet_db_ops(func):
    """Decorator to suppress database logs during function execution"""
    def wrapper(*args, **kwargs):
        with quiet_database_operations():
            return func(*args, **kwargs)
    return wrapper