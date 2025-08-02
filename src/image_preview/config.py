"""
Configuration settings for ImagePreview module.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class ImagePreviewSettings:
    """Settings for image preview generation."""
    
    # ComfyUI connection
    comfyui_url: str = "http://127.0.0.1:8188"
    connection_timeout: int = 30
    execution_timeout: int = 300  # 5 minutes per image
    
    # Workflow settings
    workflows_dir: Path = Path("ComfyUI_workflow_utils/workflows")
    workflow_mappings: Dict[str, str] = None
    
    # Generation settings
    enabled: bool = True
    auto_detect_models: bool = True
    batch_size: int = 1
    max_preview_images: int = 5
    
    # Default preview parameters
    default_steps: int = 20
    default_cfg_scale: float = 7.5
    default_width: int = 1024
    default_height: int = 1024
    default_seed: Optional[int] = 42
    
    # Output settings
    save_workflows: bool = False  # Save modified workflows for debugging
    preview_subfolder: str = "previews"
    
    def __post_init__(self):
        """Initialize default workflow mappings if not provided."""
        if self.workflow_mappings is None:
            self.workflow_mappings = {
                'FluxLORA': 'Flux_LORA.json',
                'FluxCheckpoint': 'Flux_LORA.json',
                'SDXLCheckpoint': 'SDXLCheckpoint.json',
                'SDXLLoRA': 'SDXLCheckpoint.json'
            }
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImagePreviewSettings':
        """Create settings from dictionary."""
        # Convert string paths to Path objects
        if 'workflows_dir' in data and isinstance(data['workflows_dir'], str):
            data['workflows_dir'] = Path(data['workflows_dir'])
            
        return cls(**data)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        data = {
            'comfyui_url': self.comfyui_url,
            'connection_timeout': self.connection_timeout,
            'execution_timeout': self.execution_timeout,
            'workflows_dir': str(self.workflows_dir),
            'workflow_mappings': self.workflow_mappings,
            'enabled': self.enabled,
            'auto_detect_models': self.auto_detect_models,
            'batch_size': self.batch_size,
            'max_preview_images': self.max_preview_images,
            'default_steps': self.default_steps,
            'default_cfg_scale': self.default_cfg_scale,
            'default_width': self.default_width,
            'default_height': self.default_height,
            'default_seed': self.default_seed,
            'save_workflows': self.save_workflows,
            'preview_subfolder': self.preview_subfolder
        }
        return data