"""Singleton logger to prevent duplicate initialization messages."""

import logging
from typing import Set

logger = logging.getLogger(__name__)


class SingletonLogger:
    """Logger that tracks messages to avoid duplicates."""
    
    _instance = None
    _logged_messages: Set[str] = set()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def log_once(self, level: int, message: str, *args):
        """Log a message only if it hasn't been logged before.
        
        Args:
            level: Logging level (e.g., logging.INFO)
            message: Message to log
            *args: Additional arguments for string formatting
        """
        # Create a unique key for this message
        key = f"{level}:{message}"
        
        if key not in self._logged_messages:
            self._logged_messages.add(key)
            logger.log(level, message, *args)
    
    def info_once(self, message: str, *args):
        """Log info message only once."""
        self.log_once(logging.INFO, message, *args)
    
    def debug_once(self, message: str, *args):
        """Log debug message only once."""
        self.log_once(logging.DEBUG, message, *args)
    
    def reset(self):
        """Reset logged messages (useful for testing)."""
        self._logged_messages.clear()


# Global instance
singleton_logger = SingletonLogger()