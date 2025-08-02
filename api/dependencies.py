"""
Dependency injection utilities for FastAPI.

This module provides dependency functions that can be injected into
FastAPI route handlers for consistent access to services and resources.
"""

import os
import logging
from typing import Optional
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, status
from dotenv import load_dotenv

from src.database.manager_v2 import DatabaseManager
from src.config import Config
from .exceptions import DatabaseError, ConfigurationError
from .services.cli_translator import CLITranslator
from .services.stats_reader import StatsReader

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger = logging.getLogger(__name__)
    logger.info(f"Loaded environment from {env_path}")
else:
    logger = logging.getLogger(__name__)
    logger.warning(f"No .env file found at {env_path}")


@lru_cache()
def get_config() -> Config:
    """
    Get application configuration.
    
    This function is cached to ensure the same configuration instance
    is used throughout the application lifecycle.
    
    Returns:
        Configuration instance
        
    Raises:
        ConfigurationError: If configuration cannot be loaded
    """
    try:
        # Use default configuration loading
        return Config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise ConfigurationError(
            config_type="application",
            reason=str(e)
        )


@lru_cache()
def get_cli_translator() -> CLITranslator:
    """
    Get CLI translator instance.
    
    This function is cached to ensure the same CLI translator instance
    is used throughout the application lifecycle.
    
    Returns:
        CLITranslator instance
        
    Raises:
        ConfigurationError: If CLI translator cannot be initialized
    """
    try:
        return CLITranslator()
    except Exception as e:
        logger.error(f"Failed to initialize CLI translator: {e}")
        raise ConfigurationError(
            config_type="cli_translator",
            reason=str(e)
        )


@lru_cache()
def get_stats_reader() -> StatsReader:
    """
    Get statistics reader instance.
    
    This function is cached to ensure the same stats reader instance
    is used throughout the application lifecycle.
    
    Returns:
        StatsReader instance
        
    Raises:
        ConfigurationError: If stats reader cannot be initialized
    """
    try:
        return StatsReader()
    except Exception as e:
        logger.error(f"Failed to initialize stats reader: {e}")
        raise ConfigurationError(
            config_type="stats_reader",
            reason=str(e)
        )


def validate_job_id(job_id: str) -> str:
    """
    Validate job ID format.
    
    Args:
        job_id: Job ID to validate
        
    Returns:
        Validated job ID
        
    Raises:
        HTTPException: If job ID is invalid
    """
    if not job_id or not job_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job ID cannot be empty"
        )
    
    # Basic format validation (adjust as needed)
    if len(job_id) < 3 or len(job_id) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job ID must be between 3 and 50 characters"
        )
    
    return job_id.strip()


def validate_dataset_name(dataset_name: str) -> str:
    """
    Validate dataset name format.
    
    Args:
        dataset_name: Dataset name to validate
        
    Returns:
        Validated dataset name
        
    Raises:
        HTTPException: If dataset name is invalid
    """
    if not dataset_name or not dataset_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dataset name cannot be empty"
        )
    
    # Basic format validation
    dataset_name = dataset_name.strip()
    if len(dataset_name) < 1 or len(dataset_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dataset name must be between 1 and 100 characters"
        )
    
    # Check for invalid characters (adjust as needed)
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    if any(char in dataset_name for char in invalid_chars):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dataset name cannot contain: {', '.join(invalid_chars)}"
        )
    
    return dataset_name


def validate_preset_name(preset_name: str) -> str:
    """
    Validate preset name format.
    
    Args:
        preset_name: Preset name to validate
        
    Returns:
        Validated preset name
        
    Raises:
        HTTPException: If preset name is invalid
    """
    if not preset_name or not preset_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Preset name cannot be empty"
        )
    
    return preset_name.strip()


def check_service_health(
    cli_translator: CLITranslator = Depends(get_cli_translator),
    stats_reader: StatsReader = Depends(get_stats_reader)
) -> dict:
    """
    Check the health of core services.
    
    Args:
        cli_translator: CLI translator dependency
        stats_reader: Stats reader dependency
        
    Returns:
        Dictionary with service health status
        
    Raises:
        HTTPException: If critical services are unhealthy
    """
    health_status = {
        "cli_translator": "unknown",
        "database_reader": "unknown"
    }
    
    # Check CLI translator health
    try:
        if cli_translator.main_script.exists():
            health_status["cli_translator"] = "healthy"
        else:
            health_status["cli_translator"] = "unhealthy"
    except Exception as e:
        logger.error(f"CLI translator health check failed: {e}")
        health_status["cli_translator"] = "unhealthy"
    
    # Check database reader health
    try:
        # Simple database health check
        stats_reader.get_job_statistics()
        health_status["database_reader"] = "healthy"
    except Exception as e:
        logger.error(f"Database reader health check failed: {e}")
        health_status["database_reader"] = "degraded"  # Not critical
    
    # Check if any critical service is unhealthy
    if health_status["cli_translator"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Critical service (CLI translator) is unhealthy",
                "services": health_status
            }
        )
    
    return health_status


# Utility function for pagination
def get_pagination_params(page: int = 1, page_size: int = 20) -> dict:
    """
    Get validated pagination parameters.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Dictionary with validated pagination parameters
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page number must be >= 1"
        )
    
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page size must be between 1 and 100"
        )
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size
    }


# Legacy dependencies kept for compatibility but raise errors
def get_database_manager():
    """Legacy - database management should be done through CLI."""
    raise NotImplementedError("Database management must be done through CLI")


def get_pipeline_service():
    """Legacy - pipeline execution should be done through CLI."""
    raise NotImplementedError("Pipeline execution must be done through CLI")


def get_job_service():
    """Legacy - job management should be done through CLI."""
    raise NotImplementedError("Job management must be done through CLI. Use CLI translator instead.")