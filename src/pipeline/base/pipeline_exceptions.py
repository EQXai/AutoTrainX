"""Custom exceptions for pipeline operations."""


class PipelineException(Exception):
    """Base exception for all pipeline-related errors."""
    pass


class ValidationError(PipelineException):
    """Raised when input validation fails."""
    pass


class ExecutionError(PipelineException):
    """Raised when pipeline execution fails."""
    pass