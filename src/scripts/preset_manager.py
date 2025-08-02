"""
Unified preset management system for AutoTrainX.

This module provides preset management functionality:
- Manages training presets by scanning BasePresets directory
- Handles dynamic preset detection and configuration
- Integrates with model management system
"""

import os
import json
import toml
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Import from the new model management system
from .models import TrainingConfig, ValidationError, ModelManager


# ===== PRESET MANAGER FUNCTIONALITY =====

def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


@dataclass
class PresetInfo:
    """Information about a training preset (renamed from ProfileInfo)."""
    name: str
    description: str
    config_path: Path
    defaults: Dict[str, Any]
    is_lora: bool = False
    model_type: str = "unknown"
    training_script: str = "unknown"
    default_args: List[str] = None
    base_preset: Optional[str] = None  # For custom presets
    is_custom: bool = False
    preset_type: str = "base"  # "base" or "custom"
    
    def __post_init__(self):
        if self.default_args is None:
            self.default_args = []


class PresetManager:
    """Manages training presets dynamically (renamed from ProfileManager)."""
    
    def __init__(self):
        self.project_root = get_project_root()
        # Support both old and new structures
        self.presets_root = self.project_root / "Presets"
        self.base_presets_dir = self.presets_root / "Base"
        self.custom_presets_dir = self.presets_root / "Custom"
        
        # Fallback to old structure if new doesn't exist
        if not self.presets_root.exists():
            self.presets_root = self.project_root / "BasePresets"
            self.base_presets_dir = self.presets_root
            self.custom_presets_dir = None
        
        self.sd_scripts_dir = self.project_root / "sd-scripts"
        self._presets_cache: Optional[Dict[str, PresetInfo]] = None
        
        # Initialize model manager
        self.model_manager = ModelManager(str(self.project_root))
        
        # Flexible script mapping based on model types and features
        self._script_patterns = {
            "flux_lora": "flux_train_network.py",
            "flux_full": "flux_train.py", 
            "sdxl_full": "sdxl_train.py",
            "sdxl_lora": "train_network.py",
            "default": "train_network.py"
        }
        
        # Default arguments based on detected characteristics
        self._default_args_patterns = {
            "sdxl_full": [
                "--max_grad_norm=0.0",
                "--no_half_vae",
                "--train_text_encoder", 
                "--learning_rate_te2=0",
            ],
            "flux_lora": [],
            "flux_full": [],
            "sdxl_lora": [],
            "default": []
        }
        
        # Create Presets directory if it doesn't exist (dynamic creation)
        self.presets_dir = self.project_root / "workspace/Presets"  # Updated from BatchConfig
        self.presets_dir.mkdir(exist_ok=True)
    
    def _detect_preset_characteristics(self, config: Dict[str, Any]) -> Tuple[bool, str, str, List[str]]:
        """Detect preset characteristics and return is_lora, model_type, script, default_args."""
        is_lora = "network_module" in config or "network_dim" in config
        
        # Detect model type from config
        pretrained_path = str(config.get("pretrained_model_name_or_path", "")).lower()
        vae = str(config.get("vae", "")).lower()
        
        if "flux" in pretrained_path:
            model_type = "flux"
            if is_lora:
                script_key = "flux_lora"
                script = self._script_patterns["flux_lora"]
                default_args = self._default_args_patterns["flux_lora"].copy()
            else:
                script_key = "flux_full" 
                script = self._script_patterns["flux_full"]
                default_args = self._default_args_patterns["flux_full"].copy()
        elif "sdxl" in pretrained_path or "stabilityai/sdxl-vae" in vae:
            model_type = "sdxl"
            if is_lora:
                script_key = "sdxl_lora"
                script = self._script_patterns["sdxl_lora"]
                default_args = self._default_args_patterns["sdxl_lora"].copy()
            else:
                script_key = "sdxl_full"
                script = self._script_patterns["sdxl_full"] 
                default_args = self._default_args_patterns["sdxl_full"].copy()
        else:
            model_type = "unknown"
            script = self._script_patterns["default"]
            default_args = self._default_args_patterns["default"].copy()
            
        return is_lora, model_type, script, default_args
    
    def _generate_description(self, preset_name: str, model_type: str, is_lora: bool) -> str:
        """Generate a descriptive text for the preset."""
        model_display = model_type.upper() if model_type != "unknown" else "Custom"
        training_type = "LoRA" if is_lora else "Full"
        return f"{model_display} {training_type} training preset"
    
    def _load_preset_config(self, preset_dir: Path, base_preset_name: Optional[str] = None, is_loading_base: bool = False) -> Optional[Dict[str, Any]]:
        """Load preset configuration from base.toml."""
        config_path = preset_dir / "base.toml"
        
        if not config_path.exists():
            print(f"Warning: No base.toml found for preset {preset_dir.name}")
            return None
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config for {preset_dir.name}: {e}")
            return None
    
    def _load_preset_metadata(self, preset_dir: Path) -> Optional[Dict[str, Any]]:
        """Load preset metadata from preset.toml."""
        metadata_path = preset_dir / "preset.toml"
        if not metadata_path.exists():
            return None
            
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return toml.load(f)
        except Exception as e:
            print(f"Warning: Failed to load metadata for {preset_dir.name}: {e}")
            return None
    
    def _deep_merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_configs(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
                
        return result
    
    def _load_models_config(self, preset_dir: Path) -> Dict[str, str]:
        """Load models configuration using the new model manager."""
        return self.model_manager._load_models_config(preset_dir)
    
    def _scan_presets(self) -> Dict[str, PresetInfo]:
        """Scan both Base and Custom preset directories."""
        presets = {}
        
        # Scan base presets
        if self.base_presets_dir.exists():
            base_presets = self._scan_directory(self.base_presets_dir, "base")
            presets.update(base_presets)
        else:
            print(f"Warning: Base presets directory not found: {self.base_presets_dir}")
        
        # Scan custom presets if available
        if self.custom_presets_dir and self.custom_presets_dir.exists():
            custom_presets = self._scan_directory(self.custom_presets_dir, "custom")
            presets.update(custom_presets)
        
        return presets
    
    def _scan_directory(self, directory: Path, preset_type: str) -> Dict[str, PresetInfo]:
        """Scan a specific directory for presets."""
        presets = {}
        
        for item in directory.iterdir():
            if not item.is_dir():
                continue
                
            preset_name = item.name
            
            # For custom presets, check for preset metadata
            preset_metadata = None
            base_preset_name = None
            if preset_type == "custom":
                preset_metadata = self._load_preset_metadata(item)
                if preset_metadata:
                    base_preset_name = preset_metadata.get("preset", {}).get("base")
            
            # Load configuration
            config = self._load_preset_config(item, base_preset_name)
            
            if config is None:
                print(f"Warning: Skipping preset {preset_name} - no valid configuration found")
                continue
            
            # For custom presets with a base, inherit characteristics from base preset
            if preset_type == "custom" and base_preset_name:
                # Try to get characteristics from base preset
                base_preset_info = None
                for existing_preset_name, existing_preset in presets.items():
                    if existing_preset_name == base_preset_name:
                        base_preset_info = existing_preset
                        break
                
                if not base_preset_info:
                    # Load base preset if not in current presets dict
                    base_dir = self.base_presets_dir / base_preset_name
                    if base_dir.exists():
                        base_config = self._load_preset_config(base_dir)
                        if base_config:
                            is_lora, model_type, training_script, default_args = self._detect_preset_characteristics(base_config)
                        else:
                            is_lora, model_type, training_script, default_args = self._detect_preset_characteristics(config)
                    else:
                        is_lora, model_type, training_script, default_args = self._detect_preset_characteristics(config)
                else:
                    # Use base preset characteristics
                    is_lora = base_preset_info.is_lora
                    model_type = base_preset_info.model_type
                    training_script = base_preset_info.training_script
                    default_args = base_preset_info.default_args.copy()
            else:
                # For base presets or custom without base, detect from config
                is_lora, model_type, training_script, default_args = self._detect_preset_characteristics(config)
            
            # Generate description
            if preset_metadata and "description" in preset_metadata.get("preset", {}):
                description = preset_metadata["preset"]["description"]
            else:
                description = self._generate_description(preset_name, model_type, is_lora)
            
            presets[preset_name] = PresetInfo(
                name=preset_name,
                description=description,
                config_path=item / "base.toml",
                defaults=config,
                is_lora=is_lora,
                model_type=model_type,
                training_script=training_script,
                default_args=default_args,
                base_preset=base_preset_name,
                is_custom=(preset_type == "custom"),
                preset_type=preset_type
            )
            
            # Only print in verbose/debug mode
            if os.environ.get('PRESET_DEBUG', '').lower() == 'true':
                type_str = f"[{preset_type.upper()}]"
                print(f"✅ {type_str} Detected preset: {preset_name} ({model_type} {'LoRA' if is_lora else 'Full'}) -> {training_script}")
            
        return presets
    
    def get_presets(self, force_refresh: bool = False) -> Dict[str, PresetInfo]:
        """Get all available presets."""
        if self._presets_cache is None or force_refresh:
            self._presets_cache = self._scan_presets()
        return self._presets_cache
    
    def get_preset_names(self, force_refresh: bool = False) -> List[str]:
        """Get list of available preset names."""
        return list(self.get_presets(force_refresh).keys())
    
    def get_preset(self, name: str) -> Optional[PresetInfo]:
        """Get specific preset by name."""
        return self.get_presets().get(name)
    
    def is_valid_preset(self, name: str) -> bool:
        """Check if preset name is valid."""
        return name in self.get_preset_names()
    
    def get_preset_descriptions(self) -> Dict[str, str]:
        """Get preset descriptions for API/UI."""
        presets = self.get_presets()
        return {name: info.description for name, info in presets.items()}
    
    def get_training_script(self, preset_name: str) -> Optional[str]:
        """Get training script for preset."""
        preset = self.get_preset(preset_name)
        return preset.training_script if preset else None
    
    def get_default_args(self, preset_name: str) -> List[str]:
        """Get default arguments for preset."""
        preset = self.get_preset(preset_name)
        return preset.default_args.copy() if preset else []
    
    def get_model_paths(self, preset_name: str) -> Dict[str, str]:
        """Get resolved full paths for all models in a preset."""
        return self.model_manager.get_model_paths(preset_name)
    
    def get_lora_presets(self) -> List[str]:
        """Get list of LoRA preset names."""
        presets = self.get_presets()
        return [name for name, info in presets.items() if info.is_lora]
    
    def get_full_training_presets(self) -> List[str]:
        """Get list of full training preset names."""
        presets = self.get_presets()
        return [name for name, info in presets.items() if not info.is_lora]
    
    def get_presets_by_model_type(self, model_type: str) -> List[str]:
        """Get presets filtered by model type."""
        presets = self.get_presets()
        return [name for name, info in presets.items() if info.model_type == model_type]
    
    def refresh_presets(self) -> Dict[str, PresetInfo]:
        """Force refresh preset cache."""
        return self.get_presets(force_refresh=True)
    
    def supports_gpu_ids(self, preset_name: str) -> bool:
        """Check if preset supports GPU IDs (non-SDXL presets)."""
        preset = self.get_preset(preset_name)
        if not preset:
            return True  # Default to True for unknown presets
        return preset.model_type != "sdxl" or preset.is_lora
    
    def create_custom_preset(self, name: str, base_preset_name: str, 
                           description: Optional[str] = None,
                           overrides: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a new custom preset based on an existing preset.
        
        Args:
            name: Name for the new custom preset
            base_preset_name: Name of the base preset to inherit from
            description: Optional description for the preset
            overrides: Optional configuration overrides
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure custom presets directory exists
        if not self.custom_presets_dir:
            self.custom_presets_dir = self.presets_root / "Custom"
        self.custom_presets_dir.mkdir(exist_ok=True)
        
        # Validate base preset exists
        base_preset = self.get_preset(base_preset_name)
        if not base_preset:
            print(f"Error: Base preset '{base_preset_name}' not found")
            return False
        
        # Check if preset already exists
        preset_dir = self.custom_presets_dir / name
        if preset_dir.exists():
            print(f"Error: Preset '{name}' already exists")
            return False
        
        # Create preset directory
        preset_dir.mkdir()
        
        # Create preset metadata
        from datetime import datetime
        metadata = {
            "preset": {
                "base": base_preset_name,
                "name": name,
                "description": description or f"Custom preset based on {base_preset_name}",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        
        # Write metadata
        metadata_path = preset_dir / "preset.toml"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            toml.dump(metadata, f)
        
        # Copy full configuration from base preset and apply overrides
        config = copy.deepcopy(base_preset.defaults)
        
        # Apply overrides if provided
        if overrides:
            config = self._deep_merge_configs(config, overrides)
        
        # Write full configuration
        config_path = preset_dir / "base.toml"
        with open(config_path, 'w', encoding='utf-8') as f:
            toml.dump(config, f)
        
        # Copy models.toml from base preset if exists
        base_models_path = Path(base_preset.config_path).parent / "models.toml"
        if base_models_path.exists():
            import shutil
            shutil.copy(base_models_path, preset_dir / "models.toml")
        
        # Refresh cache
        self.refresh_presets()
        
        return True
    
    def delete_custom_preset(self, name: str) -> bool:
        """
        Delete a custom preset.
        
        Args:
            name: Name of the custom preset to delete
            
        Returns:
            True if successful, False otherwise
        """
        preset = self.get_preset(name)
        if not preset:
            print(f"Error: Preset '{name}' not found")
            return False
        
        if not preset.is_custom:
            print(f"Error: Cannot delete base preset '{name}'")
            return False
        
        # Remove preset directory
        preset_dir = self.custom_presets_dir / name
        if preset_dir.exists():
            import shutil
            shutil.rmtree(preset_dir)
            
        # Refresh cache
        self.refresh_presets()
        
        return True
    
    def list_custom_presets(self) -> List[str]:
        """Get list of custom preset names."""
        presets = self.get_presets()
        return [name for name, info in presets.items() if info.is_custom]
    
    def get_base_presets(self) -> List[str]:
        """Get list of base preset names."""
        presets = self.get_presets()
        return [name for name, info in presets.items() if info.preset_type == "base"]


# ===== GLOBAL INSTANCE AND COMPATIBILITY FUNCTIONS =====

# Global instance
_preset_manager = None

def get_preset_manager() -> PresetManager:
    """Get global preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager


# Backward compatibility functions (updated for new naming)
def get_valid_presets() -> List[str]:
    """Get list of valid preset names."""
    return get_preset_manager().get_preset_names()

def is_valid_preset(preset_name: str) -> bool:
    """Check if preset name is valid."""
    return get_preset_manager().is_valid_preset(preset_name)

def get_preset_info(preset_name: str) -> Optional[PresetInfo]:
    """Get preset information."""
    return get_preset_manager().get_preset(preset_name)

def get_preset_descriptions() -> Dict[str, str]:
    """Get all preset descriptions."""
    return get_preset_manager().get_preset_descriptions()

def get_training_script(preset_name: str) -> Optional[str]:
    """Get training script for preset."""
    return get_preset_manager().get_training_script(preset_name)

def get_default_args(preset_name: str) -> List[str]:
    """Get default arguments for preset."""
    return get_preset_manager().get_default_args(preset_name)


# ===== LEGACY COMPATIBILITY (profile_manager aliases) =====
# These functions maintain compatibility with existing code that uses profile terminology

ProfileInfo = PresetInfo  # Alias for backward compatibility
ProfileManager = PresetManager  # Alias for backward compatibility

def get_profile_manager() -> PresetManager:
    """Legacy alias for get_preset_manager()."""
    return get_preset_manager()

def get_valid_profiles() -> List[str]:
    """Legacy alias for get_valid_presets()."""
    return get_valid_presets()

def is_valid_profile(profile_name: str) -> bool:
    """Legacy alias for is_valid_preset()."""
    return is_valid_preset(profile_name)

def get_profile_info(profile_name: str) -> Optional[PresetInfo]:
    """Legacy alias for get_preset_info()."""
    return get_preset_info(profile_name)

def get_profile_descriptions() -> Dict[str, str]:
    """Legacy alias for get_preset_descriptions()."""
    return get_preset_descriptions()