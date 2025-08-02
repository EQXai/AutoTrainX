"""Path management system for AutoTrainX.

This module provides centralized path management with support for custom output paths.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


class PathManager:
    """Manages all paths in AutoTrainX with support for custom output directories."""
    
    def __init__(self, base_path: str, custom_output_path: Optional[str] = None):
        """Initialize PathManager.
        
        Args:
            base_path: Base AutoTrainX installation path
            custom_output_path: Optional custom path for outputs (models, configs, previews)
        """
        self.base_path = Path(base_path).absolute()
        self.custom_output_path = Path(custom_output_path).absolute() if custom_output_path else None
        self.mode = "custom" if custom_output_path else "default"
        
        # Validate paths
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {self.base_path}")
            
        if self.custom_output_path and not self.custom_output_path.exists():
            self.custom_output_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_custom_mode(self) -> bool:
        """Check if using custom output path."""
        return self.mode == "custom"
    
    # Base paths that don't change with custom mode
    def get_base_path(self) -> Path:
        """Get the base AutoTrainX path."""
        return self.base_path
    
    def get_models_base_path(self) -> Path:
        """Get the base models directory (for downloading base models)."""
        return self.base_path / "models"
    
    def get_presets_base_path(self) -> Path:
        """Get the base presets directory (for preset definitions)."""
        return self.base_path / "Presets"
    
    def get_logs_base_path(self) -> Path:
        """Get the logs directory."""
        return self.base_path / "logs"
    
    def get_workspace_path(self) -> Path:
        """Get the workspace path (always in base for input data)."""
        return self.base_path / "workspace"
    
    # Input paths (always in workspace)
    def get_input_base_path(self) -> Path:
        """Get the input base directory."""
        return self.get_workspace_path() / "input"
    
    def get_input_path(self, dataset_name: str) -> Path:
        """Get the input path for a specific dataset."""
        return self.get_input_base_path() / dataset_name
    
    # Output paths (affected by custom mode)
    def get_output_base_path(self) -> Path:
        """Get the output base directory."""
        # Always return standard workspace/output path
        # Custom paths are handled by file move hook after training
        return self.get_workspace_path() / "output"
    
    def get_output_path(self, dataset_name: str) -> Path:
        """Get the output path for a specific dataset."""
        return self.get_output_base_path() / dataset_name
    
    def get_model_output_path(self, dataset_name: str) -> Path:
        """Get the model output path for a dataset."""
        return self.get_output_path(dataset_name) / "model"
    
    def get_log_output_path(self, dataset_name: str) -> Path:
        """Get the log output path for a dataset."""
        return self.get_output_path(dataset_name) / "log"
    
    def get_preview_output_path(self, dataset_name: str) -> Path:
        """Get the preview output path for a dataset."""
        return self.get_output_path(dataset_name) / "Preview"
    
    def get_config_output_path(self, dataset_name: str) -> Path:
        """Get the config output path for a dataset (stores training TOML)."""
        # Always use standard Presets path
        # Custom paths are handled by file move hook after training
        return self.get_workspace_path() / "Presets"
    
    # Preset configuration paths
    def get_preset_config_path(self, preset_name: str, dataset_name: str) -> Path:
        """Get the path for a generated preset configuration."""
        # Always use standard path - configs are in workspace/Presets/PresetName/
        # Custom paths are handled by file move hook after training
        return self.get_workspace_path() / "Presets" / preset_name / f"{dataset_name}_{preset_name}.toml"
    
    # Variations paths
    def get_variations_base_path(self) -> Path:
        """Get the variations base directory."""
        # Always use standard workspace/variations path
        # Custom paths are handled by file move hook after training
        return self.get_workspace_path() / "variations"
    
    def get_variation_output_path(self, experiment_id: str, dataset_name: str) -> Path:
        """Get the output path for a variation experiment."""
        return self.get_variations_base_path() / f"exp_{experiment_id}" / dataset_name
    
    # Metadata management
    def save_training_metadata(self, dataset_name: str, metadata: Dict[str, Any]) -> None:
        """Save training metadata for a dataset."""
        output_path = self.get_output_path(dataset_name)
        metadata_file = output_path / "metadata.json"
        
        # Add path information to metadata
        metadata.update({
            "path_mode": self.mode,
            "base_path": str(self.base_path),
            "custom_output_path": str(self.custom_output_path) if self.custom_output_path else None,
            "timestamp": datetime.now().isoformat(),
            "output_structure": {
                "models": str(self.get_model_output_path(dataset_name)),
                "logs": str(self.get_log_output_path(dataset_name)),
                "previews": str(self.get_preview_output_path(dataset_name)),
                "config": str(self.get_config_output_path(dataset_name))
            }
        })
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def load_training_metadata(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Load training metadata for a dataset."""
        metadata_file = self.get_output_path(dataset_name) / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return None
    
    # Path validation and setup
    def ensure_output_structure(self, dataset_name: str) -> None:
        """Ensure all output directories exist for a dataset."""
        paths = [
            self.get_output_path(dataset_name),
            self.get_model_output_path(dataset_name),
            self.get_log_output_path(dataset_name),
            self.get_preview_output_path(dataset_name),
        ]
        
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
    
    def get_path_summary(self) -> Dict[str, str]:
        """Get a summary of current path configuration."""
        return {
            "mode": self.mode,
            "base_path": str(self.base_path),
            "custom_output_path": str(self.custom_output_path) if self.custom_output_path else None,
            "workspace": str(self.get_workspace_path()),
            "input_base": str(self.get_input_base_path()),
            "output_base": str(self.get_output_base_path()),
            "models_base": str(self.get_models_base_path()),
            "presets_base": str(self.get_presets_base_path()),
            "variations_base": str(self.get_variations_base_path()),
            "note": "Custom paths are applied after training via file move hook" if self.custom_output_path else None
        }
    
    @classmethod
    def from_config(cls, base_path: str, config: Dict[str, Any]) -> 'PathManager':
        """Create PathManager from configuration dictionary."""
        custom_path = config.get('custom_output_path')
        return cls(base_path, custom_path)
    
    def to_config(self) -> Dict[str, Any]:
        """Export PathManager configuration."""
        return {
            "custom_output_path": str(self.custom_output_path) if self.custom_output_path else None,
            "mode": self.mode
        }


class PathProfile:
    """Manages path profiles for different configurations."""
    
    def __init__(self, config_file: Optional[Path] = None, base_path: Optional[str] = None):
        """Initialize PathProfile manager.
        
        Args:
            config_file: Path to configuration file
            base_path: Base path for AutoTrainX project
        """
        if config_file:
            self.config_file = config_file
        else:
            # Use settings directory in the project root
            if base_path:
                self.config_file = Path(base_path) / "settings" / "profiles.json"
            else:
                # Try to auto-detect base path
                from ..config import Config
                detected_base = Config.get_default_base_path()
                self.config_file = Path(detected_base) / "settings" / "profiles.json"
        
        self.profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load profiles from configuration file."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "default": {
                "name": "default",
                "description": "Standard workspace structure",
                "custom_output_path": None
            }
        }
    
    def _save_profiles(self) -> None:
        """Save profiles to configuration file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.profiles, f, indent=2)
    
    def create_profile(self, name: str, custom_output_path: Optional[str], 
                      description: str = "") -> None:
        """Create a new profile.
        
        Args:
            name: Profile name
            custom_output_path: Custom output path for this profile
            description: Profile description
        """
        self.profiles[name] = {
            "name": name,
            "description": description,
            "custom_output_path": custom_output_path,
            "created": datetime.now().isoformat()
        }
        self._save_profiles()
    
    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a profile by name."""
        return self.profiles.get(name)
    
    def delete_profile(self, name: str) -> bool:
        """Delete a profile."""
        if name == "default":
            return False
        if name in self.profiles:
            del self.profiles[name]
            self._save_profiles()
            return True
        return False
    
    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        """List all profiles."""
        return self.profiles.copy()
    
    def get_path_manager(self, base_path: str, profile_name: str) -> PathManager:
        """Create a PathManager from a profile."""
        profile = self.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile not found: {profile_name}")
        
        return PathManager(base_path, profile.get('custom_output_path'))