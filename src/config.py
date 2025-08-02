"""Configuration module for AutoTrainX.

This module provides system-agnostic configuration and path management.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Central configuration for AutoTrainX."""
    
    @staticmethod
    def get_default_base_path() -> str:
        """Get the default base path for AutoTrainX.
        
        Returns the path based on the following priority:
        1. AUTOTRAINX_BASE_PATH environment variable
        2. Current working directory if it contains the AutoTrainX structure
        3. Parent directory of this file (assumes standard installation)
        
        Returns:
            Default base path as string
        """
        # Check environment variable first
        env_path = os.environ.get('AUTOTRAINX_BASE_PATH')
        if env_path and os.path.exists(env_path):
            return env_path
            
        # Check if current directory looks like AutoTrainX root
        cwd = Path.cwd()
        if (cwd / 'main.py').exists() and (cwd / 'src').exists():
            return str(cwd)
            
        # Default to the parent directory of src/
        src_parent = Path(__file__).parent.parent
        if src_parent.name == 'AutoTrainX' or (src_parent / 'main.py').exists():
            return str(src_parent)
            
        # Fallback to current directory
        return str(cwd)
    
    @staticmethod
    def get_workspace_path(base_path: Optional[str] = None) -> Path:
        """Get the workspace path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Path to workspace directory
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        return Path(base_path) / "workspace"
    
    @staticmethod
    def get_models_path(base_path: Optional[str] = None) -> Path:
        """Get the models path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Path to models directory
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        return Path(base_path) / "models"
    
    @staticmethod
    def get_presets_path(base_path: Optional[str] = None) -> Path:
        """Get the base presets path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Path to Presets directory
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        return Path(base_path) / "Presets"
    
    @staticmethod
    def get_logs_path(base_path: Optional[str] = None) -> Path:
        """Get the logs path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Path to logs directory
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        return Path(base_path) / "logs"
    
    @staticmethod
    def ensure_directories(base_path: Optional[str] = None) -> None:
        """Ensure all required directories exist.
        
        Args:
            base_path: Optional base path override
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
            
        directories = [
            Config.get_workspace_path(base_path),
            Config.get_workspace_path(base_path) / "input",
            Config.get_workspace_path(base_path) / "output",
            Config.get_workspace_path(base_path) / "Presets",
            Config.get_models_path(base_path),
            Config.get_presets_path(base_path),
            Config.get_logs_path(base_path)
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def get_config_file_path(base_path: Optional[str] = None) -> Path:
        """Get the configuration file path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Path to configuration file
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        return Path(base_path) / "config.json"
    
    @staticmethod
    def load_config(base_path: Optional[str] = None) -> dict:
        """Load configuration from file.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Configuration dictionary
        """
        config_path = Config.get_config_file_path(base_path)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    @staticmethod
    def save_config(config: dict, base_path: Optional[str] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary
            base_path: Optional base path override
        """
        config_path = Config.get_config_file_path(base_path)
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save configuration: {e}")
    
    @staticmethod
    def get_comfyui_path(base_path: Optional[str] = None) -> Optional[str]:
        """Get the saved ComfyUI path.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            ComfyUI path if set, None otherwise
        """
        config = Config.load_config(base_path)
        return config.get('COMFYPATH')
    
    @staticmethod
    def set_comfyui_path(comfyui_path: str, base_path: Optional[str] = None) -> None:
        """Set and save the ComfyUI path.
        
        Args:
            comfyui_path: Path to ComfyUI installation
            base_path: Optional base path override
        """
        config = Config.load_config(base_path)
        config['COMFYPATH'] = comfyui_path
        Config.save_config(config, base_path)
        print(f"✓ ComfyUI path saved: {comfyui_path}")
        
    @staticmethod
    def get_training_progress_setting(base_path: Optional[str] = None) -> bool:
        """Get the training progress display setting.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            True to show progress bar (default), False to show raw logs
        """
        config = Config.load_config(base_path)
        return config.get('show_training_progress', True)
        
    @staticmethod
    def set_training_progress_setting(show_progress: bool, base_path: Optional[str] = None) -> None:
        """Set the training progress display setting.
        
        Args:
            show_progress: True to show progress bar, False to show raw logs
            base_path: Optional base path override
        """
        config = Config.load_config(base_path)
        config['show_training_progress'] = show_progress
        Config.save_config(config, base_path)
        print(f"✓ Training progress setting saved: {'progress bar' if show_progress else 'raw logs'}")
    
    @staticmethod
    def get_custom_output_path(base_path: Optional[str] = None) -> Optional[str]:
        """Get the custom output path if configured.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Custom output path if set, None otherwise
        """
        config = Config.load_config(base_path)
        return config.get('custom_output_path')
    
    @staticmethod
    def set_custom_output_path(custom_path: Optional[str], base_path: Optional[str] = None) -> None:
        """Set the custom output path.
        
        Args:
            custom_path: Path for custom outputs (None to disable)
            base_path: Optional base path override
        """
        config = Config.load_config(base_path)
        if custom_path:
            config['custom_output_path'] = str(Path(custom_path).absolute())
            print(f"✓ Custom output path set: {custom_path}")
        else:
            config.pop('custom_output_path', None)
            print("✓ Custom output path cleared (using default workspace)")
        Config.save_config(config, base_path)
    
    @staticmethod
    def get_active_profile(base_path: Optional[str] = None) -> str:
        """Get the active path profile.
        
        Args:
            base_path: Optional base path override
            
        Returns:
            Active profile name
        """
        config = Config.load_config(base_path)
        return config.get('active_profile', 'default')
    
    @staticmethod
    def set_active_profile(profile_name: str, base_path: Optional[str] = None) -> None:
        """Set the active path profile.
        
        Args:
            profile_name: Profile name to activate
            base_path: Optional base path override
        """
        config = Config.load_config(base_path)
        config['active_profile'] = profile_name
        Config.save_config(config, base_path)
        print(f"✓ Active profile set: {profile_name}")


# Convenience function for backward compatibility
def get_default_base_path() -> str:
    """Get the default base path for AutoTrainX.
    
    Returns:
        Default base path as string
    """
    return Config.get_default_base_path()