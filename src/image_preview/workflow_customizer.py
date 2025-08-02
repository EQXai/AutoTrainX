"""
Workflow customization module.

This module handles customizing ComfyUI workflows based on preset types and parameters.
Ensures correct workflow modification for different model types (FluxLORA, SDXLCheckpoint).
"""

import json
import random
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..config import Config
from ..utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class WorkflowCustomizer:
    """Handles customization of ComfyUI workflows for different presets."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize workflow customizer.
        
        Args:
            base_path: Base path of AutoTrainX project
        """
        self.base_path = base_path or Path.cwd()
        
        # Initialize PathManager if custom path is configured
        custom_path = Config.get_custom_output_path(str(self.base_path))
        if custom_path:
            self.path_manager = PathManager(str(self.base_path), custom_path)
        else:
            self.path_manager = None
        
    def _get_effective_preset(self, preset_name: str) -> str:
        """
        Get the effective preset name for workflow customization.
        For custom presets, this returns the base preset.
        """
        # Import here to avoid circular imports
        from ..scripts.preset_manager import PresetManager
        
        try:
            preset_manager = PresetManager()
            preset_info = preset_manager.get_preset(preset_name)
            
            if preset_info and preset_info.is_custom and preset_info.base_preset:
                logger.info(f"Custom preset '{preset_name}' detected, using base preset '{preset_info.base_preset}' for customization")
                return preset_info.base_preset
        except Exception as e:
            logger.warning(f"Failed to check preset type for '{preset_name}': {e}")
        
        return preset_name

    def customize_workflow(self,
                         workflow: Dict[str, Any],
                         preset: str,
                         model_filename: str,
                         dataset_name: str,
                         preview_index: int) -> Dict[str, Any]:
        """
        Customize workflow based on preset type.
        
        Args:
            workflow: Base workflow dictionary
            preset: Preset name (e.g., 'FluxLORA', 'SDXLCheckpoint')
            model_filename: Filename of the trained model in ComfyUI models directory
            dataset_name: Name of the dataset
            preview_index: Index of the preview (1-based)
            
        Returns:
            Customized workflow dictionary
        """
        logger.info(f"Customizing workflow for {preset} - Preview {preview_index}")
        
        # Get effective preset (handles custom presets)
        effective_preset = self._get_effective_preset(preset)
        
        # Determine workflow type based on effective preset
        if 'FluxLORA' in effective_preset:
            return self._customize_flux_lora_workflow(
                workflow, model_filename, dataset_name, preview_index, preset
            )
        elif 'SDXLCheckpoint' in effective_preset:
            return self._customize_sdxl_checkpoint_workflow(
                workflow, model_filename, dataset_name, preview_index, preset
            )
        else:
            logger.warning(f"Unknown preset type: {preset} (effective: {effective_preset})")
            return workflow
            
    def _customize_flux_lora_workflow(self,
                                    workflow: Dict[str, Any],
                                    model_filename: str,
                                    dataset_name: str,
                                    preview_index: int,
                                    original_preset: str) -> Dict[str, Any]:
        """Customize FluxLORA workflow."""
        # Find and update nodes
        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get('class_type', '')
            
            # Update UNETLoader
            if class_type == 'UNETLoader':
                # TODO: En el futuro, este valor debe ser actualizado con el modelo UNET específico
                # Por ahora se mantiene el valor actual del workflow
                logger.info("UNETLoader found - keeping current value (TODO: update in future)")
                
            # Update LoraLoader (CRITICAL)
            elif class_type == 'LoraLoader':
                if 'inputs' in node_data:
                    node_data['inputs']['lora_name'] = model_filename
                    logger.info(f"Updated LoraLoader with model: {model_filename}")
                    
            # Update LoadImageFromPath
            elif class_type == 'LoadImageFromPath':
                if 'inputs' in node_data:
                    sample_image_path = self._get_sample_image_path(preview_index)
                    node_data['inputs']['image'] = sample_image_path
                    logger.info(f"Updated LoadImageFromPath: {sample_image_path}")
                    
            # Update RandomNoise - ALWAYS randomize
            elif class_type == 'RandomNoise':
                if 'inputs' in node_data:
                    seed = random.randint(0, 2**32 - 1)
                    node_data['inputs']['noise_seed'] = seed
                    logger.info(f"Randomized noise seed: {seed}")
                    
            # Update PrimitiveString nodes for output path
            elif class_type == 'PrimitiveString':
                meta_title = node_data.get('_meta', {}).get('title', '')
                if meta_title.upper() in ['OUTPUT_PATH', 'OUTPUT PATH']:
                    if 'inputs' in node_data:
                        # Determine correct output path based on whether this is a variation
                        if "_v" in dataset_name and any(p in dataset_name for p in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"]):
                            # For variations, use the new structure
                            variations_path = os.path.join(self.base_path, 'workspace', 'variations')
                            output_path = None
                            
                            # Try to find the experiment directory
                            if os.path.exists(variations_path):
                                for exp_dir in os.listdir(variations_path):
                                    if exp_dir.startswith("exp_"):
                                        variation_dir = os.path.join(variations_path, exp_dir, dataset_name)
                                        if os.path.exists(variation_dir):
                                            output_path = os.path.abspath(
                                                os.path.join(variation_dir, 'Preview')
                                            )
                                            break
                            
                            if output_path is None:
                                # Fallback to direct path if experiment directory not found
                                output_path = os.path.abspath(
                                    os.path.join(self.base_path, 'workspace', 'variations', dataset_name, 'Preview')
                                )
                        else:
                            # Standard output path for single/batch modes
                            if self.path_manager:
                                output_path = os.path.abspath(
                                    str(self.path_manager.get_preview_output_path(dataset_name))
                                )
                            else:
                                output_path = os.path.abspath(
                                    os.path.join(self.base_path, 'workspace', 'output', dataset_name, 'Preview')
                                )
                        
                        node_data['inputs']['value'] = output_path
                        logger.info(f"Updated output path: {output_path}")
                        
        # Update SaveImage nodes for filename
        self._update_save_image_nodes(workflow, dataset_name, original_preset, preview_index)
        
        return workflow
        
    def _customize_sdxl_checkpoint_workflow(self,
                                          workflow: Dict[str, Any],
                                          model_filename: str,
                                          dataset_name: str,
                                          preview_index: int,
                                          original_preset: str) -> Dict[str, Any]:
        """Customize SDXLCheckpoint workflow - RESTRICTIVE MODE."""
        # Find and update specific nodes only
        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get('class_type', '')
            
            # Update CheckpointLoaderSimple
            if class_type == 'CheckpointLoaderSimple':
                if 'inputs' in node_data:
                    node_data['inputs']['ckpt_name'] = model_filename
                    logger.info(f"Updated CheckpointLoaderSimple: {model_filename}")
                    
            # Update seed nodes - ALWAYS randomize
            elif class_type == 'Seed Everywhere':
                if 'inputs' in node_data and 'seed' in node_data['inputs']:
                    seed = random.randint(0, 2**32 - 1)
                    node_data['inputs']['seed'] = seed
                    logger.info(f"Randomized seed in {class_type}: {seed}")
                    
            # Update Load Prompt From File - EQX (both seed and file_path)
            elif class_type == 'Load Prompt From File - EQX':
                if 'inputs' in node_data:
                    # First, randomize seed if present
                    if 'seed' in node_data['inputs']:
                        seed = random.randint(0, 2**32 - 1)
                        node_data['inputs']['seed'] = seed
                        logger.info(f"Randomized seed in {class_type}: {seed}")
                    
                    # Then, update file path to absolute path
                    txt_path = os.path.abspath(
                        os.path.join(self.base_path, 'ComfyUI_workflow_utils', 'txt', 'stand1.txt')
                    )
                    
                    # Verify the file exists
                    if not os.path.exists(txt_path):
                        logger.warning(f"Prompt file not found: {txt_path}")
                        logger.info(f"Base path is: {self.base_path}")
                        # Try alternative location
                        alt_path = os.path.abspath(
                            os.path.join(os.getcwd(), 'ComfyUI_workflow_utils', 'txt', 'stand1.txt')
                        )
                        if os.path.exists(alt_path):
                            txt_path = alt_path
                            logger.info(f"Using alternative path: {txt_path}")
                        else:
                            logger.error(f"Alternative path also not found: {alt_path}")
                    
                    node_data['inputs']['file_path'] = txt_path
                    logger.info(f"Updated prompt file path: {txt_path}")
                    
            # Update PrimitiveString for Output_Path (node 294)
            elif class_type == 'PrimitiveString':
                meta_title = node_data.get('_meta', {}).get('title', '')
                if meta_title.upper() in ['OUTPUT_PATH', 'OUTPUT PATH']:
                    if 'inputs' in node_data:
                        # Determine correct output path based on whether this is a variation
                        if "_v" in dataset_name and any(p in dataset_name for p in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"]):
                            # For variations, use the new structure
                            variations_path = os.path.join(self.base_path, 'workspace', 'variations')
                            output_path = None
                            
                            # Try to find the experiment directory
                            if os.path.exists(variations_path):
                                for exp_dir in os.listdir(variations_path):
                                    if exp_dir.startswith("exp_"):
                                        variation_dir = os.path.join(variations_path, exp_dir, dataset_name)
                                        if os.path.exists(variation_dir):
                                            output_path = os.path.abspath(
                                                os.path.join(variation_dir, 'Preview')
                                            )
                                            break
                            
                            if output_path is None:
                                # Fallback to direct path if experiment directory not found
                                output_path = os.path.abspath(
                                    os.path.join(self.base_path, 'workspace', 'variations', dataset_name, 'Preview')
                                )
                        else:
                            # Standard output path for single/batch modes
                            if self.path_manager:
                                output_path = os.path.abspath(
                                    str(self.path_manager.get_preview_output_path(dataset_name))
                                )
                            else:
                                output_path = os.path.abspath(
                                    os.path.join(self.base_path, 'workspace', 'output', dataset_name, 'Preview')
                                )
                        
                        node_data['inputs']['value'] = output_path
                        logger.info(f"Updated output path: {output_path}")
                        
            # Update SaveImage_EQX for filename
            elif class_type == 'SaveImage_EQX':
                if 'inputs' in node_data:
                    # Check if dataset_name already contains the preset (for variations)
                    if "_v" in dataset_name and original_preset in dataset_name:
                        # For variations, dataset_name already includes preset, don't duplicate
                        filename_prefix = f"{dataset_name}_{preview_index:02d}"
                    else:
                        # For single/batch modes, include preset in filename
                        filename_prefix = f"{dataset_name}_{original_preset}_{preview_index:02d}"
                    node_data['inputs']['filename_prefix'] = filename_prefix
                    logger.info(f"Updated SaveImage_EQX filename: {filename_prefix}")
                    
        return workflow
        
    def _get_sample_image_path(self, preview_index: int) -> str:
        """Get sample image path for the given preview index."""
        sample_dir = os.path.join(
            self.base_path, 'ComfyUI_workflow_utils', 'sample_Image'
        )
        
        # Validate sample directory exists
        if not os.path.exists(sample_dir):
            raise FileNotFoundError(f"Sample image directory not found: {sample_dir}")
        
        # List available sample images
        sample_images = sorted([
            f for f in os.listdir(sample_dir)
            if f.startswith('sample_image_') and f.endswith('.jpg')
        ])
        
        if not sample_images:
            raise FileNotFoundError(f"No sample images found in {sample_dir}. Expected files like 'sample_image_01.jpg'")
        
        # Use modulo to cycle through available images
        image_index = (preview_index - 1) % len(sample_images)
        selected_image = sample_images[image_index]
        full_path = os.path.join(sample_dir, selected_image)
        
        # Verify the selected image exists
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Sample image not found: {full_path}")
            
        logger.info(f"Using sample image {image_index + 1}/{len(sample_images)}: {selected_image}")
        return full_path
        
    def _update_save_image_nodes(self,
                               workflow: Dict[str, Any],
                               dataset_name: str,
                               preset: str,
                               preview_index: int):
        """Update SaveImage nodes with correct filename format."""
        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get('class_type', '')
            
            if class_type in ['SaveImage', 'SaveImage_EQX']:
                if 'inputs' in node_data:
                    # Check if dataset_name already contains the preset (for variations)
                    if "_v" in dataset_name and preset in dataset_name:
                        # For variations, dataset_name already includes preset, don't duplicate
                        filename_prefix = f"{dataset_name}_{preview_index:02d}"
                    else:
                        # For single/batch modes, include preset in filename
                        filename_prefix = f"{dataset_name}_{preset}_{preview_index:02d}"
                    
                    if 'filename_prefix' in node_data['inputs']:
                        node_data['inputs']['filename_prefix'] = filename_prefix
                        logger.info(f"Updated {class_type} filename: {filename_prefix}")