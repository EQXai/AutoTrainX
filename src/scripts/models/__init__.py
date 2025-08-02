"""
AutoTrainX Models Package

This package provides unified model management functionality for AutoTrainX.
"""

from .model_manager import (
    # Main classes
    ModelManager,
    TrainingConfig,
    ValidationError,
    
    # Global functions
    verify_all_models,
    get_model_manager,
    check_models_status,
    
    # Configuration constants
    REQUIRED_MODELS,
    HUGGINGFACE_SOURCES
)

__all__ = [
    'ModelManager',
    'TrainingConfig', 
    'ValidationError',
    'verify_all_models',
    'get_model_manager',
    'check_models_status',
    'REQUIRED_MODELS',
    'HUGGINGFACE_SOURCES'
]