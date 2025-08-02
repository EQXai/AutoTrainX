"""
Model manager for ComfyUI integration.

Handles copying trained models to ComfyUI directories temporarily for preview generation.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging
from contextlib import contextmanager

from ..config import Config
from ..utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class ComfyUIModelManager:
    """Manages temporary model files in ComfyUI directories."""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize model manager."""
        self.comfyui_path = Config.get_comfyui_path()
        if not self.comfyui_path:
            raise ValueError("ComfyUI path not configured. Use --comfyui-path to set it.")
            
        self.comfyui_path = Path(self.comfyui_path)
        self._validate_paths()
        
        # Initialize PathManager if custom path is configured
        custom_path = Config.get_custom_output_path(base_path)
        if custom_path:
            self.path_manager = PathManager(base_path or Config.get_default_base_path(), custom_path)
        else:
            self.path_manager = None
        
    def _validate_paths(self):
        """Validate ComfyUI model directories exist."""
        # First check if ComfyUI path exists
        if not self.comfyui_path.exists():
            raise ValueError(f"ComfyUI directory not found: {self.comfyui_path}")
            
        # Check models directory
        models_dir = self.comfyui_path / "models"
        if not models_dir.exists():
            raise ValueError(
                f"ComfyUI models directory not found: {models_dir}\n"
                f"Please ensure ComfyUI is properly installed at {self.comfyui_path}"
            )
            
        # Set up directories
        self.loras_dir = models_dir / "loras"
        self.checkpoints_dir = models_dir / "checkpoints"
        
        # Create directories if they don't exist (with warnings)
        if not self.loras_dir.exists():
            logger.warning(f"LoRA directory not found: {self.loras_dir}. Creating it...")
            try:
                self.loras_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created LoRA directory: {self.loras_dir}")
            except Exception as e:
                raise ValueError(f"Failed to create LoRA directory: {e}")
                
        if not self.checkpoints_dir.exists():
            logger.warning(f"Checkpoints directory not found: {self.checkpoints_dir}. Creating it...")
            try:
                self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created checkpoints directory: {self.checkpoints_dir}")
            except Exception as e:
                raise ValueError(f"Failed to create checkpoints directory: {e}")
                
        # Verify directories are writable
        test_file = self.loras_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise ValueError(f"LoRA directory is not writable: {self.loras_dir}: {e}")
            
        test_file = self.checkpoints_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise ValueError(f"Checkpoints directory is not writable: {self.checkpoints_dir}: {e}")
            
    def _get_effective_preset(self, preset_name: str) -> str:
        """
        Get the effective preset name for custom presets.
        For custom presets, this returns the base preset.
        """
        # Import here to avoid circular imports
        from ..scripts.preset_manager import PresetManager
        
        try:
            preset_manager = PresetManager()
            preset_info = preset_manager.get_preset(preset_name)
            
            if preset_info and preset_info.is_custom and preset_info.base_preset:
                logger.info(f"Custom preset '{preset_name}' detected, using base preset '{preset_info.base_preset}' for model type detection")
                return preset_info.base_preset
        except Exception as e:
            logger.warning(f"Failed to check preset type for '{preset_name}': {e}")
        
        return preset_name
            
    def copy_model_to_comfyui(self, model_path: Path, preset: str) -> Tuple[str, Path]:
        """
        Copy model to appropriate ComfyUI directory.
        
        Args:
            model_path: Path to the trained model
            preset: Preset name to determine target directory
            
        Returns:
            Tuple of (model_filename, destination_path)
        """
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
            
        # Get effective preset for custom presets
        effective_preset = self._get_effective_preset(preset)
        
        # Determine target directory based on preset
        if 'LoRA' in effective_preset or 'lora' in effective_preset.lower():
            target_dir = self.loras_dir
        else:
            target_dir = self.checkpoints_dir
            
        # Copy model to ComfyUI
        model_filename = model_path.name
        destination = target_dir / model_filename
        
        # If file already exists, use a temporary name
        if destination.exists():
            base_name = model_path.stem
            extension = model_path.suffix
            temp_name = f"{base_name}_temp_{os.getpid()}{extension}"
            destination = target_dir / temp_name
            model_filename = temp_name
            
        logger.info(f"Copying model to ComfyUI: {model_path} -> {destination}")
        shutil.copy2(model_path, destination)
        
        return model_filename, destination
        
    def remove_model_from_comfyui(self, model_path: Path):
        """
        Remove temporary model from ComfyUI.
        
        Args:
            model_path: Path to the model in ComfyUI directory
        """
        if model_path.exists():
            logger.info(f"Removing temporary model: {model_path}")
            try:
                os.remove(model_path)
            except Exception as e:
                logger.error(f"Failed to remove temporary model: {e}")
                
    @contextmanager
    def temporary_model(self, model_path: Path, preset: str):
        """
        Context manager for temporary model copying.
        
        Usage:
            with model_manager.temporary_model(model_path, preset) as model_filename:
                # Use model_filename in workflow
                pass
            # Model is automatically removed after
        
        Args:
            model_path: Path to the trained model
            preset: Preset name
            
        Yields:
            Model filename in ComfyUI
        """
        model_filename = None
        destination = None
        
        try:
            # Copy model
            model_filename, destination = self.copy_model_to_comfyui(model_path, preset)
            yield model_filename
            
        finally:
            # Always clean up
            if destination and destination.exists():
                self.remove_model_from_comfyui(destination)
                
    def find_latest_model(self, dataset_name: str, preset: str) -> Optional[Path]:
        """
        Find the latest trained model for a dataset.
        
        Args:
            dataset_name: Name of the dataset
            preset: Preset used for training
            
        Returns:
            Path to the model or None if not found
        """
        # Determine output directory based on configuration
        if self.path_manager:
            # Use PathManager to get correct model path
            output_dir = self.path_manager.get_model_output_path(dataset_name)
        else:
            # Fallback to default paths
            # Check if this is a variation (contains preset and version info)
            if "_v" in dataset_name and any(preset_name in dataset_name for preset_name in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"]):
                # Look in variations directory
                output_dir = Path("workspace/Variations") / dataset_name / "model"
            else:
                # Look in standard output directory
                output_dir = Path("workspace/output") / dataset_name / "model"
        
        if not output_dir.exists():
            return None
            
        # Find model files
        model_files = list(output_dir.glob("*.safetensors"))
        
        if not model_files:
            return None
            
        # Return most recent file
        return max(model_files, key=lambda p: p.stat().st_mtime)
        
    def validate_model_compatibility(self, model_path: Path, preset: str) -> bool:
        """
        Validate if model is compatible with preset.
        
        Args:
            model_path: Path to model file
            preset: Preset name
            
        Returns:
            True if compatible
        """
        # Basic validation - check file extension
        if not model_path.suffix == '.safetensors':
            logger.warning(f"Model file is not .safetensors: {model_path}")
            return False
            
        # Check file size (basic sanity check)
        file_size_mb = model_path.stat().st_size / (1024 * 1024)
        
        if 'LoRA' in preset and file_size_mb > 500:
            logger.warning(f"LoRA model seems too large: {file_size_mb:.1f}MB")
            
        return True