"""Logging configuration for AutoTrainX.

This module provides centralized logging configuration with:
- File and console output
- Rotation and archival
- Debug mode support
- Execution-specific log files
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class AutoTrainXFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, *args, use_color: bool = True, **kwargs):
        """Initialize formatter.
        
        Args:
            use_color: Whether to use color codes
        """
        super().__init__(*args, **kwargs)
        self.use_color = use_color and os.isatty(1)
    
    def format(self, record):
        """Format log record with optional color."""
        if self.use_color and record.levelname in self.COLORS:
            record.levelname_colored = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        else:
            record.levelname_colored = record.levelname
        
        return super().format(record)


class LoggingManager:
    """Manages logging configuration for AutoTrainX."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize logging manager.
        
        Args:
            base_path: Base path for log files
        """
        if base_path is None:
            from ..config import Config
            base_path = Config.get_default_base_path()
        
        self.base_path = Path(base_path)
        self.logs_dir = self.base_path / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
        # Create pipeline_log subdirectory
        self.pipeline_logs_dir = self.logs_dir / "pipeline_log"
        self.pipeline_logs_dir.mkdir(exist_ok=True)
        
        # Current execution log file
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.execution_log = self.pipeline_logs_dir / f"autotrainx_{self.execution_id}.log"
        
        # Main log file with rotation
        self.main_log = self.pipeline_logs_dir / "autotrainx.log"
        
        self._configured = False
    
    def configure_logging(self, 
                         log_level: str = "INFO",
                         console_output: bool = True,
                         file_output: bool = True,
                         debug_mode: bool = False) -> None:
        """Configure logging for the application.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            console_output: Enable console output
            file_output: Enable file output
            debug_mode: Enable debug mode (more verbose)
        """
        if self._configured and console_output:
            # If already configured and just enabling console, add console handler
            self._add_console_handler(log_level, debug_mode)
            return
        elif self._configured:
            return
        
        # Set log level
        level = getattr(logging, log_level.upper(), logging.INFO)
        if debug_mode:
            level = logging.DEBUG
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers
        root_logger.handlers = []
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # Different format for console (more concise)
            console_format = "%(levelname_colored)-8s %(message)s"
            console_formatter = AutoTrainXFormatter(
                console_format,
                use_color=True
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handlers
        if file_output:
            # Detailed format for files
            file_format = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(funcName)s:%(lineno)d - %(message)s"
            )
            file_formatter = logging.Formatter(file_format)
            
            # Main rotating log file
            rotating_handler = logging.handlers.RotatingFileHandler(
                self.main_log,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            rotating_handler.setLevel(level)
            rotating_handler.setFormatter(file_formatter)
            root_logger.addHandler(rotating_handler)
            
            # Execution-specific log file
            execution_handler = logging.FileHandler(self.execution_log)
            execution_handler.setLevel(logging.DEBUG if debug_mode else level)
            execution_handler.setFormatter(file_formatter)
            root_logger.addHandler(execution_handler)
        
        # Configure specific loggers
        self._configure_module_loggers(level, debug_mode)
        
        self._configured = True
        
        # Log initialization only if console output is enabled
        if console_output:
            logger = logging.getLogger(__name__)
            logger.info(f"Logging initialized - Level: {log_level}")
            logger.info(f"Execution ID: {self.execution_id}")
            if file_output:
                logger.info(f"Log file: {self.execution_log}")
    
    def _add_console_handler(self, log_level: str, debug_mode: bool) -> None:
        """Add console handler to existing logging configuration.
        
        Args:
            log_level: Logging level
            debug_mode: Whether debug mode is enabled
        """
        level = getattr(logging, log_level.upper(), logging.INFO)
        if debug_mode:
            level = logging.DEBUG
            
        root_logger = logging.getLogger()
        
        # Check if console handler already exists
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                return
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        console_format = "%(levelname_colored)-8s %(message)s"
        console_formatter = AutoTrainXFormatter(
            console_format,
            use_color=True
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def _configure_module_loggers(self, level: int, debug_mode: bool) -> None:
        """Configure module-specific loggers.
        
        Args:
            level: Base log level
            debug_mode: Whether debug mode is enabled
        """
        # Quiet down noisy libraries unless in debug mode
        if not debug_mode:
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('requests').setLevel(logging.WARNING)
            logging.getLogger('transformers').setLevel(logging.WARNING)
            logging.getLogger('torch').setLevel(logging.WARNING)
        
        # Set AutoTrainX modules to appropriate level
        logging.getLogger('src.pipeline').setLevel(level)
        logging.getLogger('src.scripts').setLevel(level)
        logging.getLogger('src.utils').setLevel(level)
    
    def get_execution_log_path(self) -> Path:
        """Get path to current execution log file.
        
        Returns:
            Path to execution log file
        """
        return self.execution_log
    
    def create_pipeline_logger(self, pipeline_id: str) -> logging.Logger:
        """Create a logger for a specific pipeline execution.
        
        Args:
            pipeline_id: Pipeline execution ID
            
        Returns:
            Configured logger instance
        """
        logger_name = f"pipeline.{pipeline_id}"
        logger = logging.getLogger(logger_name)
        
        # Add pipeline-specific handler
        pipeline_log = self.logs_dir / f"pipeline_{pipeline_id}.log"
        handler = logging.FileHandler(pipeline_log)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        ))
        logger.addHandler(handler)
        
        return logger


# Global logging manager
_logging_manager = None


def get_logging_manager(base_path: Optional[str] = None) -> LoggingManager:
    """Get global logging manager instance.
    
    Args:
        base_path: Base path for logs
        
    Returns:
        LoggingManager instance
    """
    global _logging_manager
    if _logging_manager is None:
        _logging_manager = LoggingManager(base_path)
    return _logging_manager


def setup_logging(log_level: str = None,
                 console: bool = True,
                 file: bool = True,
                 debug: bool = False,
                 base_path: Optional[str] = None) -> None:
    """Setup logging for AutoTrainX.
    
    Args:
        log_level: Log level from environment or default
        console: Enable console output
        file: Enable file output
        debug: Enable debug mode
        base_path: Base path for logs
    """
    # Get log level from environment if not provided
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Check debug mode from environment
    if not debug:
        debug = os.environ.get('DEBUG', '').lower() in ('true', '1', 'yes')
    
    manager = get_logging_manager(base_path)
    manager.configure_logging(
        log_level=log_level,
        console_output=console,
        file_output=file,
        debug_mode=debug
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)