"""Factory for creating pipeline instances."""

from typing import Optional, Type
from ..base import PipelineInterface, PipelineConfig
from ..modes import SinglePipeline, BatchPipeline, VariationsPipeline


class PipelineFactory:
    """Factory for creating pipeline instances based on mode."""
    
    _pipelines = {
        'single': SinglePipeline,
        'batch': BatchPipeline,
        'variations': VariationsPipeline
    }
    
    @classmethod
    def create(cls, mode: str, config: PipelineConfig) -> PipelineInterface:
        """
        Create a pipeline instance for the specified mode.
        
        Args:
            mode: Pipeline mode ('single', 'batch', 'variations')
            config: Pipeline configuration
            
        Returns:
            Pipeline instance
            
        Raises:
            ValueError: If mode is not recognized
        """
        if mode not in cls._pipelines:
            raise ValueError(
                f"Unknown pipeline mode: {mode}. "
                f"Available modes: {', '.join(cls._pipelines.keys())}"
            )
            
        pipeline_class = cls._pipelines[mode]
        return pipeline_class(config)
        
    @classmethod
    def register(cls, mode: str, pipeline_class: Type[PipelineInterface]) -> None:
        """
        Register a new pipeline mode.
        
        Args:
            mode: Mode name
            pipeline_class: Pipeline class that implements PipelineInterface
        """
        cls._pipelines[mode] = pipeline_class
        
    @classmethod
    def available_modes(cls) -> list[str]:
        """Get list of available pipeline modes."""
        return list(cls._pipelines.keys())