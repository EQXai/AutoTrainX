"""
Base classes for pipeline hooks.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from pathlib import Path


class HookType(Enum):
    """Types of pipeline hooks."""
    PRE_DATASET = "pre_dataset"
    POST_DATASET = "post_dataset"
    PRE_CONFIG = "pre_config"
    POST_CONFIG = "post_config"
    POST_TRAINING = "post_training"
    ON_ERROR = "on_error"


class PipelineHook(ABC):
    """
    Abstract base class for pipeline hooks.
    
    Hooks allow extending pipeline functionality at specific points.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize hook.
        
        Args:
            enabled: Whether this hook is enabled
        """
        self.enabled = enabled
        
    @property
    @abstractmethod
    def hook_type(self) -> HookType:
        """Return the type of this hook."""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this hook."""
        pass
        
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute the hook.
        
        Args:
            context: Hook execution context with relevant data
            
        Returns:
            Optional result dictionary
        """
        pass
        
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """
        Check if hook should execute given the context.
        
        Args:
            context: Hook execution context
            
        Returns:
            True if hook should execute
        """
        return self.enabled