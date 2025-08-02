"""
Enhanced logging system with structured logging and context
"""
import logging
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from contextvars import ContextVar
import structlog
from pythonjsonlogger import jsonlogger

# Context variables for request tracing
request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
job_id: ContextVar[Optional[str]] = ContextVar('job_id', default=None)

class AutoTrainXProcessor:
    """Custom processor for AutoTrainX context"""
    
    def __call__(self, logger, method_name, event_dict):
        # Add context variables
        if request_id.get():
            event_dict['request_id'] = request_id.get()
        if user_id.get():
            event_dict['user_id'] = user_id.get()
        if job_id.get():
            event_dict['job_id'] = job_id.get()
            
        # Add service info
        event_dict['service'] = 'autotrainx'
        event_dict['timestamp'] = datetime.utcnow().isoformat()
        
        return event_dict

class PerformanceLogger:
    """Context manager for performance monitoring"""
    
    def __init__(self, operation: str, logger: structlog.BoundLogger):
        self.operation = operation
        self.logger = logger
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info("operation_started", operation=self.operation)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                "operation_failed",
                operation=self.operation,
                duration=duration,
                error=str(exc_val),
                traceback=traceback.format_exc()
            )
        else:
            self.logger.info(
                "operation_completed",
                operation=self.operation,
                duration=duration
            )

class DatabaseLogger:
    """Specialized logger for database operations"""
    
    def __init__(self):
        self.logger = structlog.get_logger("database")
    
    def log_query(self, query: str, params: Dict = None, duration: float = None):
        self.logger.info(
            "database_query",
            query=query[:200] + "..." if len(query) > 200 else query,
            params=params,
            duration=duration
        )
    
    def log_connection_pool(self, active: int, total: int, overflow: int):
        self.logger.info(
            "connection_pool_status",
            active_connections=active,
            total_connections=total,
            overflow_connections=overflow
        )

class TrainingLogger:
    """Specialized logger for training operations"""
    
    def __init__(self):
        self.logger = structlog.get_logger("training")
    
    def log_training_start(self, job_id: str, dataset: str, preset: str, config: Dict):
        self.logger.info(
            "training_started",
            job_id=job_id,
            dataset=dataset,
            preset=preset,
            config=config
        )
    
    def log_training_progress(self, job_id: str, step: int, total_steps: int, loss: float = None):
        progress_pct = (step / total_steps) * 100 if total_steps > 0 else 0
        self.logger.info(
            "training_progress",
            job_id=job_id,
            step=step,
            total_steps=total_steps,
            progress_percent=progress_pct,
            loss=loss
        )
    
    def log_training_complete(self, job_id: str, success: bool, duration: float, model_path: str = None):
        self.logger.info(
            "training_completed",
            job_id=job_id,
            success=success,
            duration=duration,
            model_path=model_path
        )

def setup_logging(log_level: str = "INFO", log_dir: Path = None, enable_json: bool = True):
    """Setup structured logging for AutoTrainX"""
    
    # Create log directory
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        AutoTrainXProcessor(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if enable_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Add file handlers if log_dir provided
    if log_dir:
        # Main application log
        app_handler = logging.FileHandler(log_dir / "autotrainx.log")
        if enable_json:
            app_handler.setFormatter(jsonlogger.JsonFormatter())
        
        # Error log
        error_handler = logging.FileHandler(log_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        if enable_json:
            error_handler.setFormatter(jsonlogger.JsonFormatter())
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)

def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)

def with_context(**kwargs):
    """Decorator to add context to logger"""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            # Set context variables
            tokens = []
            if 'request_id' in kwargs:
                tokens.append(request_id.set(kwargs['request_id']))
            if 'user_id' in kwargs:
                tokens.append(user_id.set(kwargs['user_id']))
            if 'job_id' in kwargs:
                tokens.append(job_id.set(kwargs['job_id']))
            
            try:
                return func(*args, **func_kwargs)
            finally:
                # Reset context
                for token in tokens:
                    token.var.set(token.old_value)
        return wrapper
    return decorator

# Pre-configured loggers
db_logger = DatabaseLogger()
training_logger = TrainingLogger()

# Example usage functions
def log_api_request(method: str, path: str, status_code: int, duration: float):
    """Log API request"""
    logger = get_logger("api")
    logger.info(
        "api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration=duration
    )

def log_system_metric(metric_name: str, value: Union[int, float], unit: str = None):
    """Log system metrics"""
    logger = get_logger("metrics")
    logger.info(
        "system_metric",
        metric=metric_name,
        value=value,
        unit=unit
    )