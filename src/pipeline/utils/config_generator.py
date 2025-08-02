"""
Configuration generator for unified config handling across all pipelines.

This module provides a centralized way to generate training configurations,
ensuring consistency across different pipeline modes (single, batch, variations).
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import copy
from src.utils.job_id import generate_job_id
from src.utils.path_manager import PathManager


class ConfigurationGenerator:
    """Base class for generating training configurations consistently."""
    
    def __init__(self, preset_manager, base_path: Path, path_manager: Optional[PathManager] = None):
        """
        Initialize the configuration generator.
        
        Args:
            preset_manager: PresetManager instance for preset information
            base_path: Base path of the project
            path_manager: Optional PathManager for custom output paths
        """
        self.preset_manager = preset_manager
        self.base_path = Path(base_path)
        self.path_manager = path_manager
    
    def get_base_config(self, preset_name: str) -> Dict[str, Any]:
        """
        Get base configuration for a preset using unified method.
        
        Args:
            preset_name: Name of the preset
            
        Returns:
            Base configuration dictionary
            
        Raises:
            ValueError: If preset not found
        """
        preset_info = self.preset_manager.get_preset(preset_name)
        if not preset_info:
            raise ValueError(f"Preset not found: {preset_name}")
        
        # Always use preset_info.defaults for consistency
        return copy.deepcopy(preset_info.defaults)
    
    def resolve_model_paths(self, config: Dict[str, Any], preset_name: str) -> Dict[str, Any]:
        """
        Resolve model paths consistently using preset manager.
        
        Args:
            config: Configuration dictionary to update
            preset_name: Name of the preset for model resolution
            
        Returns:
            Updated configuration with resolved model paths
        """
        # Get model paths from preset manager
        model_paths = self.preset_manager.get_model_paths(preset_name)
        
        # Update configuration with normalized paths
        for key, path in model_paths.items():
            if path:  # Only update if path is not None/empty
                config[key] = self._normalize_path(path)
        
        return config
    
    def update_dataset_paths(self, config: Dict[str, Any], 
                           dataset_name: str, 
                           output_dir: Path,
                           variation_name: Optional[str] = None,
                           preset_name: Optional[str] = None,
                           original_dataset_dir: Optional[Path] = None,
                           job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Update configuration with dataset-specific paths.
        
        Args:
            config: Configuration dictionary to update
            dataset_name: Name of the dataset
            output_dir: Base output directory for the dataset
            variation_name: Optional variation name (for output_name)
            preset_name: Optional preset name to include in output_name
            original_dataset_dir: Optional path to original dataset (for variations)
            job_id: Optional job ID to include in output paths
            
        Returns:
            Updated configuration with dataset paths
        """
        # Ensure output_dir is a Path object
        output_dir = Path(output_dir)
        
        # Generate job_id if not provided
        if job_id is None:
            job_id = generate_job_id()
        
        # Store job_id in config for reference
        config["job_id"] = job_id
        
        # Determine output_name with job_id
        if variation_name:
            output_name = f"{variation_name}_{job_id}"
        elif preset_name:
            output_name = f"{dataset_name}_{preset_name}_{job_id}"
        else:
            output_name = f"{dataset_name}_{job_id}"
        
        # Determine train_data_dir - use original dataset for variations
        if original_dataset_dir:
            train_data_dir = self._normalize_path(original_dataset_dir / "img")
            sample_prompts_path = self._normalize_path(original_dataset_dir / "sample_prompts.txt")
        else:
            # For normal training, images are in the base dataset directory
            train_data_dir = self._normalize_path(output_dir / "img")
            sample_prompts_path = self._normalize_path(output_dir / "sample_prompts.txt")
        
        # Update paths with consistent normalization
        # Keep output_dir and logging_dir pointing to base dataset folder
        # Only output_name includes the JobID
        
        # For variations mode, always use the provided output_dir
        # This ensures each variation has its own independent output directory
        model_output_path = output_dir / "model"
        log_output_path = output_dir / "log"
            
        config.update({
            "train_data_dir": train_data_dir,
            "output_dir": self._normalize_path(model_output_path),
            "logging_dir": self._normalize_path(log_output_path),
            "sample_prompts": sample_prompts_path,
            "output_name": output_name
        })
        
        return config
    
    def _normalize_path(self, path: Any) -> str:
        """
        Normalize paths for cross-platform compatibility.
        
        Converts all paths to use forward slashes, which work on all platforms
        including Windows, Linux, and macOS.
        
        Args:
            path: Path to normalize (string or Path object)
            
        Returns:
            Normalized path string with forward slashes
        """
        # Convert to Path object if string
        if isinstance(path, str):
            path = Path(path)
        
        # Convert to absolute path if relative
        if not path.is_absolute():
            path = self.base_path / path
        
        # Use as_posix() for forward slashes on all platforms
        return path.as_posix()
    
    def validate_dataset_exists(self, dataset_name: str, dataset_base_path: Path) -> bool:
        """
        Validate that a dataset exists before generating configuration.
        
        Args:
            dataset_name: Name of the dataset to validate
            dataset_base_path: Base path where datasets are stored
            
        Returns:
            True if dataset exists, False otherwise
        """
        dataset_path = dataset_base_path / dataset_name
        img_path = dataset_path / "img"
        
        # Check if the dataset directory and img subdirectory exist
        return dataset_path.exists() and img_path.exists()
    
    def apply_variations(self, base_config: Dict[str, Any], 
                        variations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameter variations to a configuration.
        
        Handles nested parameters using dot notation (e.g., "optimizer_args.lr").
        
        Args:
            base_config: Base configuration to modify
            variations: Dictionary of parameter variations to apply
            
        Returns:
            Configuration with variations applied
        """
        config = copy.deepcopy(base_config)
        
        for param, value in variations.items():
            if '.' in param:
                # Handle nested parameters
                keys = param.split('.')
                target = config
                
                # Navigate to the nested location
                for key in keys[:-1]:
                    if key not in target:
                        target[key] = {}
                    target = target[key]
                
                # Set the final value
                target[keys[-1]] = value
            else:
                # Simple parameter
                config[param] = value
        
        return config
    
    def create_config_header(self, preset_name: str, dataset_name: str, 
                           mode: str, variations: Optional[Dict[str, Any]] = None,
                           job_id: Optional[str] = None) -> str:
        """
        Create a descriptive header for configuration files.
        
        Args:
            preset_name: Name of the base preset
            dataset_name: Name of the dataset
            mode: Pipeline mode (single, batch, variations)
            variations: Optional variations dict for variations mode
            job_id: Optional job ID to include in header
            
        Returns:
            Header string for TOML file
        """
        header_lines = [
            f"# Configuration generated by AutoTrainX",
            f"# Mode: {mode}",
            f"# Base preset: {preset_name}",
            f"# Dataset: {dataset_name}"
        ]
        
        if job_id:
            header_lines.append(f"# JobID: {job_id}")
        
        if variations:
            header_lines.append(f"# Variations: {variations}")
        
        header_lines.append("")  # Empty line before config
        
        return "\n".join(header_lines)