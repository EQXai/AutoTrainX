"""
Handler for ComfyUI workflow manipulation and modification.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from copy import deepcopy

from .models import PreviewConfig
from .workflow_customizer import WorkflowCustomizer

logger = logging.getLogger(__name__)


class WorkflowHandler:
    """
    Handles loading and modification of ComfyUI workflows.
    """
    
    # Workflow file mappings
    WORKFLOW_MAPPINGS = {
        'FluxLORA': 'Flux_LORA.json',
        'FluxCheckpoint': 'Flux_LORA.json',  # Can use same workflow
        'SDXLCheckpoint': 'SDXLCheckpoint.json',
        'SDXLLoRA': 'SDXLCheckpoint.json'  # Can adapt same workflow
    }
    
    def __init__(self, workflows_dir: Path, base_path: Optional[str] = None):
        """
        Initialize workflow handler.
        
        Args:
            workflows_dir: Directory containing workflow JSON files
            base_path: Base path for the project
        """
        self.workflows_dir = Path(workflows_dir)
        self._validate_workflows_dir()
        self.customizer = WorkflowCustomizer(base_path=Path(base_path) if base_path else None)
        
    def _validate_workflows_dir(self):
        """Validate that workflows directory exists and contains expected files."""
        if not self.workflows_dir.exists():
            raise ValueError(f"Workflows directory not found: {self.workflows_dir}")
            
        # Check for at least one workflow file
        json_files = list(self.workflows_dir.glob("*.json"))
        if not json_files:
            raise ValueError(f"No workflow JSON files found in {self.workflows_dir}")
            
    def _get_base_preset(self, preset_name: str) -> str:
        """
        Get the base preset name for custom presets.
        
        Args:
            preset_name: The preset name to check
            
        Returns:
            The base preset name if it's a custom preset, otherwise the original preset name
        """
        # Import here to avoid circular imports
        from ..scripts.preset_manager import PresetManager
        
        try:
            preset_manager = PresetManager()
            preset_info = preset_manager.get_preset(preset_name)
            
            if preset_info and preset_info.is_custom and preset_info.base_preset:
                logger.info(f"Custom preset '{preset_name}' detected, using base preset '{preset_info.base_preset}' for workflow")
                return preset_info.base_preset
        except Exception as e:
            logger.warning(f"Failed to check preset type for '{preset_name}': {e}")
        
        return preset_name
    
    def load_workflow(self, model_type: str) -> Dict[str, Any]:
        """
        Load workflow template for specific model type.
        
        Args:
            model_type: Type of model (e.g., 'FluxLORA', 'SDXLCheckpoint')
            
        Returns:
            Workflow dictionary
        """
        # Check if this is a custom preset and get its base preset
        effective_model_type = self._get_base_preset(model_type)
        
        workflow_file = self.WORKFLOW_MAPPINGS.get(effective_model_type)
        if not workflow_file:
            raise ValueError(f"No workflow mapping for model type: {model_type} (effective type: {effective_model_type}). Available types: {list(self.WORKFLOW_MAPPINGS.keys())}")
            
        workflow_path = self.workflows_dir / workflow_file
        if not workflow_path.exists():
            # List available workflows for better error message
            available_workflows = [f.name for f in self.workflows_dir.glob("*.json")] if self.workflows_dir.exists() else []
            raise FileNotFoundError(
                f"Workflow file not found: {workflow_path}\n"
                f"Available workflows in {self.workflows_dir}: {available_workflows}"
            )
            
        # Validate file is readable and valid JSON
        try:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in workflow file {workflow_path}: {e}")
        except Exception as e:
            raise IOError(f"Failed to read workflow file {workflow_path}: {e}")
            
        # Validate workflow structure
        if not isinstance(workflow, dict):
            raise ValueError(f"Workflow must be a dictionary, got {type(workflow)}")
            
        # Validate workflow has nodes
        if not any(isinstance(v, dict) and 'class_type' in v for v in workflow.values()):
            raise ValueError(f"Workflow appears to have no valid nodes")
            
        logger.info(f"Loaded and validated workflow: {workflow_file} for {model_type}")
        return workflow
        
    def modify_workflow(self,
                       workflow: Dict[str, Any],
                       model_filename: str,
                       dataset_name: str,
                       preset: str,
                       preview_index: int = 1) -> Dict[str, Any]:
        """
        Modify workflow with specific parameters using the new customizer.
        
        Args:
            workflow: Base workflow dictionary
            model_filename: Filename of model in ComfyUI directory
            dataset_name: Name of the dataset
            preset: Preset name (e.g., 'FluxLORA', 'SDXLCheckpoint')
            preview_index: Index of preview being generated (1-based)
            
        Returns:
            Modified workflow dictionary
        """
        # Deep copy to avoid modifying original
        modified = deepcopy(workflow)
        
        # Use the new customizer
        return self.customizer.customize_workflow(
            modified, preset, model_filename, dataset_name, preview_index
        )
        
    def validate_workflow(self, workflow: Dict[str, Any]) -> bool:
        """
        Validate that a workflow has required nodes and connections.
        
        Args:
            workflow: Workflow dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_node_types = {'KSampler', 'SaveImage'}
        found_types = set()
        
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict) and 'class_type' in node_data:
                class_type = node_data['class_type']
                if class_type in required_node_types or 'Sampler' in class_type:
                    found_types.add('KSampler' if 'Sampler' in class_type else class_type)
                    
        missing = required_node_types - found_types
        if missing:
            logger.warning(f"Workflow missing required nodes: {missing}")
            return False
            
        return True