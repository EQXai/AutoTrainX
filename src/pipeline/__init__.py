"""
AutoTrainX Pipeline Package

This package provides unified dataset preparation and preset configuration
functionality for the AutoTrainX project.
"""

from .pipeline import (
    AutoTrainPipeline,
    PipelineResult,
    create_pipeline
)

__all__ = [
    'AutoTrainPipeline',
    'PipelineResult', 
    'create_pipeline'
]

__version__ = '1.0.0'