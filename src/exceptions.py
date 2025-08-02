"""
Custom exception hierarchy for AutoTrainX
"""
from enum import Enum
from typing import Dict, Any, Optional
import traceback

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    CONFIGURATION = "configuration"
    DATABASE = "database"
    TRAINING = "training"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    EXTERNAL_SERVICE = "external_service"

class AutoTrainXException(Exception):
    """Base exception for AutoTrainX"""
    
    def __init__(self, 
                 message: str,
                 error_code: str = None,
                 category: ErrorCategory = ErrorCategory.CONFIGURATION,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Dict[str, Any] = None,
                 cause: Exception = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or f"{category.value.upper()}_ERROR"
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.cause = cause
        self.stack_trace = traceback.format_exc()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "stack_trace": self.stack_trace if self.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None,
            "cause": str(self.cause) if self.cause else None
        }

# Configuration Errors
class ConfigurationError(AutoTrainXException):
    def __init__(self, message: str, config_key: str = None, **kwargs):
        context = {"config_key": config_key} if config_key else {}
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            **kwargs
        )

class MissingConfigError(ConfigurationError):
    def __init__(self, config_key: str, **kwargs):
        super().__init__(
            f"Required configuration '{config_key}' is missing",
            config_key=config_key,
            error_code="CONFIG_MISSING",
            **kwargs
        )

class InvalidConfigError(ConfigurationError):
    def __init__(self, config_key: str, value: Any, expected: str, **kwargs):
        super().__init__(
            f"Invalid configuration '{config_key}': got {value}, expected {expected}",
            config_key=config_key,
            error_code="CONFIG_INVALID",
            context={"value": value, "expected": expected},
            **kwargs
        )

# Database Errors
class DatabaseError(AutoTrainXException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_code="DB_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class DatabaseConnectionError(DatabaseError):
    def __init__(self, host: str, port: int, database: str, **kwargs):
        super().__init__(
            f"Failed to connect to database {database} at {host}:{port}",
            error_code="DB_CONNECTION_FAILED",
            severity=ErrorSeverity.CRITICAL,
            context={"host": host, "port": port, "database": database},
            **kwargs
        )

class DatabaseMigrationError(DatabaseError):
    def __init__(self, from_version: str, to_version: str, **kwargs):
        super().__init__(
            f"Database migration failed from {from_version} to {to_version}",
            error_code="DB_MIGRATION_FAILED",
            context={"from_version": from_version, "to_version": to_version},
            **kwargs
        )

# Training Errors
class TrainingError(AutoTrainXException):
    def __init__(self, message: str, job_id: str = None, **kwargs):
        context = {"job_id": job_id} if job_id else {}
        super().__init__(
            message,
            error_code="TRAINING_ERROR",
            category=ErrorCategory.TRAINING,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **kwargs
        )

class ModelNotFoundError(TrainingError):
    def __init__(self, model_path: str, **kwargs):
        super().__init__(
            f"Model not found at path: {model_path}",
            error_code="MODEL_NOT_FOUND",
            context={"model_path": model_path},
            **kwargs
        )

class DatasetValidationError(TrainingError):
    def __init__(self, dataset_path: str, issues: list, **kwargs):
        super().__init__(
            f"Dataset validation failed: {len(issues)} issues found",
            error_code="DATASET_INVALID",
            context={"dataset_path": dataset_path, "issues": issues},
            **kwargs
        )

class TrainingTimeoutError(TrainingError):
    def __init__(self, job_id: str, timeout_minutes: int, **kwargs):
        super().__init__(
            f"Training job {job_id} timed out after {timeout_minutes} minutes",
            job_id=job_id,
            error_code="TRAINING_TIMEOUT",
            context={"timeout_minutes": timeout_minutes},
            **kwargs
        )

# Filesystem Errors
class FilesystemError(AutoTrainXException):
    def __init__(self, message: str, path: str = None, **kwargs):
        context = {"path": path} if path else {}
        super().__init__(
            message,
            error_code="FS_ERROR",
            category=ErrorCategory.FILESYSTEM,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **kwargs
        )

class InsufficientDiskSpaceError(FilesystemError):
    def __init__(self, required_gb: float, available_gb: float, path: str, **kwargs):
        super().__init__(
            f"Insufficient disk space: need {required_gb}GB, only {available_gb}GB available",
            path=path,
            error_code="DISK_SPACE_LOW",
            severity=ErrorSeverity.HIGH,
            context={"required_gb": required_gb, "available_gb": available_gb},
            **kwargs
        )

# External Service Errors
class ExternalServiceError(AutoTrainXException):
    def __init__(self, service_name: str, message: str, **kwargs):
        super().__init__(
            f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            context={"service_name": service_name},
            **kwargs
        )

class ComfyUIError(ExternalServiceError):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            "ComfyUI",
            message,
            error_code="COMFYUI_ERROR",
            **kwargs
        )

class GoogleSheetsError(ExternalServiceError):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            "Google Sheets",
            message,
            error_code="SHEETS_ERROR",
            **kwargs
        )

# Validation Errors
class ValidationError(AutoTrainXException):
    def __init__(self, field: str, value: Any, message: str = None, **kwargs):
        message = message or f"Validation failed for field '{field}'"
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context={"field": field, "value": value},
            **kwargs
        )

# Utility functions
def handle_exception(func):
    """Decorator to handle and log exceptions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AutoTrainXException:
            # Re-raise AutoTrainX exceptions
            raise
        except Exception as e:
            # Convert standard exceptions to AutoTrainX exceptions
            raise AutoTrainXException(
                f"Unexpected error in {func.__name__}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                severity=ErrorSeverity.HIGH,
                cause=e
            )
    return wrapper

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      exceptions: tuple = (Exception,)):
    """Decorator to retry function on specific exceptions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        # Max retries reached
                        raise AutoTrainXException(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            error_code="MAX_RETRIES_EXCEEDED",
                            severity=ErrorSeverity.HIGH,
                            cause=last_exception,
                            context={"max_retries": max_retries, "attempts": attempt + 1}
                        )
            
        return wrapper
    return decorator