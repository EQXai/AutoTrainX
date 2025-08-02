"""
Data models for image preview module.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class PreviewConfig:
    """Configuration for preview generation."""
    steps: int = 20
    cfg_scale: float = 7.5
    width: int = 1024
    height: int = 1024
    batch_size: int = 1
    seed: Optional[int] = None
    lora_strength: Optional[float] = 1.0
    sampler: str = "dpmpp_2m"
    scheduler: str = "karras"
    denoise: float = 1.0
    
    # Additional parameters that might be needed
    clip_skip: int = -1
    positive_prompt_prefix: str = ""
    negative_prompt: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            k: v for k, v in self.__dict__.items() 
            if v is not None
        }


@dataclass
class PreviewResult:
    """Result of preview generation."""
    success: bool
    dataset_name: str
    model_type: str
    images: List[Path] = field(default_factory=list)
    workflow_used: Optional[str] = None
    prompts_used: Optional[List[str]] = None
    error: Optional[str] = None
    generation_time: Optional[float] = None
    
    @property
    def image_count(self) -> int:
        """Number of images generated."""
        return len(self.images)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'dataset_name': self.dataset_name,
            'model_type': self.model_type,
            'images': [str(img) for img in self.images],
            'workflow_used': self.workflow_used,
            'prompts_used': self.prompts_used,
            'error': self.error,
            'generation_time': self.generation_time,
            'image_count': self.image_count
        }


@dataclass
class WorkflowModification:
    """Represents a modification to apply to a workflow."""
    node_id: str
    field_path: List[str]  # e.g., ['inputs', 'text']
    new_value: Any
    
    def apply(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Apply this modification to a workflow."""
        if self.node_id in workflow:
            node = workflow[self.node_id]
            
            # Navigate to the field
            current = node
            for i, key in enumerate(self.field_path[:-1]):
                if key not in current:
                    current[key] = {}
                current = current[key]
                
            # Set the value
            if self.field_path:
                current[self.field_path[-1]] = self.new_value
                
        return workflow


@dataclass
class BatchPreviewRequest:
    """Request for batch preview generation."""
    models: List[Dict[str, Any]]
    config: Optional[PreviewConfig] = None
    parallel: bool = False
    max_workers: int = 4