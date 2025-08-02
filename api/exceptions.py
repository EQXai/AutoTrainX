"""
Custom exceptions and error handling for the AutoTrainX API.

This module defines custom exception classes and error response utilities
for consistent error handling across the API.
"""

from typing import Dict, Any, Optional
from fastapi import status


class AutoTrainXAPIException(Exception):
    """Base exception class for AutoTrainX API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code
            error_code: Machine-readable error code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class JobNotFoundError(AutoTrainXAPIException):
    """Exception raised when a job is not found."""
    
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job with ID '{job_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="JOB_NOT_FOUND",
            details={"job_id": job_id}
        )


class JobAlreadyRunningError(AutoTrainXAPIException):
    """Exception raised when trying to start a job that's already running."""
    
    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job '{job_id}' is already running",
            status_code=status.HTTP_409_CONFLICT,
            error_code="JOB_ALREADY_RUNNING",
            details={"job_id": job_id}
        )


class JobCancellationError(AutoTrainXAPIException):
    """Exception raised when job cancellation fails."""
    
    def __init__(self, job_id: str, reason: str):
        super().__init__(
            message=f"Failed to cancel job '{job_id}': {reason}",
            status_code=status.HTTP_409_CONFLICT,
            error_code="JOB_CANCELLATION_FAILED",
            details={"job_id": job_id, "reason": reason}
        )


class DatasetNotFoundError(AutoTrainXAPIException):
    """Exception raised when a dataset is not found."""
    
    def __init__(self, dataset_name: str):
        super().__init__(
            message=f"Dataset '{dataset_name}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="DATASET_NOT_FOUND",
            details={"dataset_name": dataset_name}
        )


class DatasetPreparationError(AutoTrainXAPIException):
    """Exception raised when dataset preparation fails."""
    
    def __init__(self, dataset_path: str, reason: str):
        super().__init__(
            message=f"Failed to prepare dataset at '{dataset_path}': {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="DATASET_PREPARATION_FAILED",
            details={"dataset_path": dataset_path, "reason": reason}
        )


class PresetNotFoundError(AutoTrainXAPIException):
    """Exception raised when a preset is not found."""
    
    def __init__(self, preset_name: str):
        super().__init__(
            message=f"Preset '{preset_name}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="PRESET_NOT_FOUND",
            details={"preset_name": preset_name}
        )


class InvalidPipelineModeError(AutoTrainXAPIException):
    """Exception raised when an invalid pipeline mode is specified."""
    
    def __init__(self, mode: str, valid_modes: list):
        super().__init__(
            message=f"Invalid pipeline mode '{mode}'. Valid modes: {', '.join(valid_modes)}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INVALID_PIPELINE_MODE",
            details={"mode": mode, "valid_modes": valid_modes}
        )


class TrainingExecutionError(AutoTrainXAPIException):
    """Exception raised when training execution fails."""
    
    def __init__(self, job_id: str, reason: str):
        super().__init__(
            message=f"Training execution failed for job '{job_id}': {reason}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="TRAINING_EXECUTION_FAILED",
            details={"job_id": job_id, "reason": reason}
        )


class DatabaseError(AutoTrainXAPIException):
    """Exception raised when database operations fail."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database operation '{operation}' failed: {reason}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details={"operation": operation, "reason": reason}
        )


class ConfigurationError(AutoTrainXAPIException):
    """Exception raised when configuration is invalid or missing."""
    
    def __init__(self, config_type: str, reason: str):
        super().__init__(
            message=f"Configuration error for '{config_type}': {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="CONFIGURATION_ERROR",
            details={"config_type": config_type, "reason": reason}
        )


class ResourceNotAvailableError(AutoTrainXAPIException):
    """Exception raised when required resources are not available."""
    
    def __init__(self, resource_type: str, resource_name: str):
        super().__init__(
            message=f"Required {resource_type} '{resource_name}' is not available",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RESOURCE_NOT_AVAILABLE",
            details={"resource_type": resource_type, "resource_name": resource_name}
        )


class ValidationError(AutoTrainXAPIException):
    """Exception raised when request validation fails."""
    
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation error for field '{field}': {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"field": field, "reason": reason}
        )


class RateLimitExceededError(AutoTrainXAPIException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, limit_type: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded for {limit_type}",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit_type": limit_type, "retry_after": retry_after}
        )


def create_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
        
    Returns:
        Standardized error response dictionary
    """
    from datetime import datetime
    
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }


def handle_pipeline_exception(e: Exception, context: str = "") -> AutoTrainXAPIException:
    """
    Convert pipeline exceptions to API exceptions.
    
    Args:
        e: Original exception
        context: Additional context information
        
    Returns:
        Appropriate AutoTrainXAPIException
    """
    # Import here to avoid circular imports
    from src.pipeline.base.pipeline_exceptions import (
        PipelineException,
        ValidationError as PipelineValidationError,
        ExecutionError as PipelineExecutionError
    )
    
    if isinstance(e, PipelineValidationError):
        return ValidationError(
            field="pipeline_validation",
            reason=str(e)
        )
    elif isinstance(e, PipelineExecutionError):
        return TrainingExecutionError(
            job_id=context,
            reason=str(e)
        )
    elif isinstance(e, PipelineException):
        return AutoTrainXAPIException(
            message=f"Pipeline error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PIPELINE_ERROR",
            details={"context": context}
        )
    else:
        # Handle unknown exceptions
        return AutoTrainXAPIException(
            message=f"Unexpected error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="UNEXPECTED_ERROR",
            details={"exception_type": type(e).__name__, "context": context}
        )