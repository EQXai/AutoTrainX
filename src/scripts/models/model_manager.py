#!/usr/bin/env python3
"""
Unified Model Management System for AutoTrainX

This module unifies functionality from:
1. config_models.py (TrainingConfig and ValidationError)
2. model_sync.py (model synchronization logic)
3. preset_manager.py (model path management)

Features:
- Complete model verification and synchronization
- Local model checking in ./models/
- External sync from /workspace/Train/models
- HuggingFace downloads as fallback
- Model configuration management
- TrainingConfig compatibility
"""

import os
import shutil
import sys
import toml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Add parent directory to path for imports if running standalone
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.config import Config
else:
    from ...config import Config


# ===== COMPATIBILITY CLASSES =====

class ValidationError(Exception):
    """ValidationError for compatibility with existing code"""
    pass


class TrainingConfig:
    """Minimal TrainingConfig that accepts any configuration."""
    
    def __init__(self, **data):
        # Simple approach: accept any configuration
        for key, value in data.items():
            setattr(self, key, value)
    
    def dict(self):
        """Return configuration as dictionary for compatibility."""
        return {key: value for key, value in self.__dict__.items()}
    
    def __getitem__(self, key):
        """Allow dictionary-style access for compatibility."""
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        """Allow dictionary-style assignment for compatibility."""
        setattr(self, key, value)
    
    def get(self, key, default=None):
        """Get attribute with default value for compatibility."""
        return getattr(self, key, default)


# ===== MODEL CONFIGURATION =====

REQUIRED_MODELS = {
    "flux1-dev-fp8.safetensors": "flux model",
    "SDXLModel.safetensors": "sdxl model",
    "t5xxl_fp8_e4m3fn.safetensors": "t5 encoder",
    "ae.safetensors": "autoencoder",
    "clip_l.safetensors": "clip encoder"
}

HUGGINGFACE_SOURCES = {
    "flux1-dev-fp8.safetensors": "black-forest-labs/FLUX.1-dev",
    "SDXLModel.safetensors": "stabilityai/stable-diffusion-xl-base-1.0",
    "t5xxl_fp8_e4m3fn.safetensors": "comfyanonymous/flux_text_encoders",
    "ae.safetensors": "black-forest-labs/FLUX.1-dev",
    "clip_l.safetensors": "comfyanonymous/flux_text_encoders"
}


# ===== MODEL MANAGER CLASS =====

class ModelManager:
    """Unified model management system."""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = Config.get_default_base_path()
        self.base_path = Path(base_path)
        self.models_dir = self.base_path / "models"
        self.source_model_dir = Path("/workspace/Train/models/trainX")
        
        # Required models with their relative paths
        self.required_model_paths = [
            "flux1-dev-fp8.safetensors",
            "SDXLModel.safetensors", 
            "t5xxl_fp8_e4m3fn.safetensors",
            "ae.safetensors",
            "clip_l.safetensors"
        ]
        
        self._ensure_models_directory()
    
    def _ensure_models_directory(self):
        """Ensure models directory exists."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def _log_message(self, message: str, level: str = "INFO"):
        """Simple logging with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def _get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get file information (size and modification time)."""
        if not file_path.exists():
            return None
        stat = file_path.stat()
        return {
            'size': stat.st_size,
            'mtime': stat.st_mtime
        }
    
    def _need_sync(self, source_file: Path, target_file: Path) -> bool:
        """Determine if a file needs synchronization."""
        if not target_file.exists():
            return True
        
        source_info = self._get_file_info(source_file)
        target_info = self._get_file_info(target_file)
        
        if source_info is None or target_info is None:
            return False
        
        # Compare size and modification time
        if (source_info['size'] != target_info['size'] or 
            source_info['mtime'] > target_info['mtime']):
            return True
        
        return False
    
    def _copy_file_with_progress(self, source: Path, target: Path) -> bool:
        """Copy a file with progress indication."""
        try:
            file_size = source.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            self._log_message(f"Copying {source.name} ({file_size_mb:.1f} MB)...")
            
            # Ensure target directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the file
            shutil.copy2(source, target)
            
            self._log_message(f"✓ {source.name} copied successfully")
            return True
            
        except Exception as e:
            self._log_message(f"✗ Error copying {source.name}: {str(e)}", "ERROR")
            return False
    
    def _download_from_huggingface(self, model_name: str) -> bool:
        """Download model from HuggingFace as fallback."""
        try:
            from huggingface_hub import hf_hub_download
            
            if model_name not in HUGGINGFACE_SOURCES:
                self._log_message(f"No HuggingFace source defined for {model_name}", "WARNING")
                return False
            
            repo_id = HUGGINGFACE_SOURCES[model_name]
            target_path = self.models_dir / model_name
            
            self._log_message(f"Downloading {model_name} from {repo_id}...")
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=model_name,
                local_dir=target_path.parent,
                local_dir_use_symlinks=False
            )
            
            self._log_message(f"✓ Downloaded {model_name} successfully")
            return True
            
        except ImportError:
            self._log_message("huggingface_hub not available for downloads", "ERROR")
            return False
        except Exception as e:
            self._log_message(f"✗ Error downloading {model_name}: {str(e)}", "ERROR")
            return False
    
    def _check_local_models(self) -> bool:
        """Check if all required models exist locally."""
        missing = []
        
        for rel_path in self.required_model_paths:
            target_file = self.models_dir / rel_path
            if not target_file.exists():
                missing.append(rel_path)
        
        if not missing:
            self._log_message(f"✓ All {len(self.required_model_paths)} required models are present locally")
            return True
        
        self._log_message(f"✗ {len(missing)} required models are missing locally")
        for missing_model in missing:
            self._log_message(f"  - {missing_model}", "INFO")
        
        return False
    
    def _sync_from_external(self) -> bool:
        """Sync missing models from external source directory."""
        if not self.source_model_dir.exists():
            self._log_message(f"External source directory not found: {self.source_model_dir}", "WARNING")
            return False
        
        self._log_message("Attempting to sync from external source...")
        
        # Find missing models that need sync
        files_to_sync = []
        total_size = 0
        
        for rel_path in self.required_model_paths:
            source_file = self.source_model_dir / rel_path
            target_file = self.models_dir / rel_path
            
            if source_file.exists():
                if self._need_sync(source_file, target_file):
                    files_to_sync.append((source_file, target_file))
                    total_size += source_file.stat().st_size
            else:
                self._log_message(f"Model not found in external source: {rel_path}", "WARNING")
        
        if not files_to_sync:
            self._log_message("✓ No models need synchronization from external source")
            return True
        
        # Show sync summary
        total_size_gb = total_size / (1024 * 1024 * 1024)
        self._log_message(f"Need to sync {len(files_to_sync)} models ({total_size_gb:.1f} GB)")
        
        # Copy files
        success_count = 0
        for source_file, target_file in files_to_sync:
            if self._copy_file_with_progress(source_file, target_file):
                success_count += 1
            else:
                self._log_message(f"Failed to copy {source_file.name}", "ERROR")
        
        # Summary
        if success_count == len(files_to_sync):
            self._log_message(f"✓ External sync completed: {success_count}/{len(files_to_sync)} models")
            return True
        else:
            self._log_message(f"✗ Partial external sync: {success_count}/{len(files_to_sync)} models", "WARNING")
            return False
    
    def _download_missing_from_huggingface(self) -> bool:
        """Download any remaining missing models from HuggingFace."""
        missing_models = []
        
        for rel_path in self.required_model_paths:
            target_file = self.models_dir / rel_path
            if not target_file.exists():
                model_name = target_file.name
                missing_models.append(model_name)
        
        if not missing_models:
            return True
        
        self._log_message(f"Attempting to download {len(missing_models)} missing models from HuggingFace...")
        
        success_count = 0
        for model_name in missing_models:
            if self._download_from_huggingface(model_name):
                success_count += 1
        
        if success_count == len(missing_models):
            self._log_message(f"✓ HuggingFace downloads completed: {success_count}/{len(missing_models)} models")
            return True
        else:
            self._log_message(f"✗ Partial HuggingFace downloads: {success_count}/{len(missing_models)} models", "ERROR")
            return False
    
    def verify_models(self) -> bool:
        """
        Complete model verification with multi-step fallback:
        1. Check local models
        2. Sync from external source if needed
        3. Download from HuggingFace if still missing
        """
        self._log_message("=== STARTING MODEL VERIFICATION ===")
        
        # Step 1: Check if all models are already available locally
        if self._check_local_models():
            self._log_message("✓ All required models verified successfully")
            return True
        
        # Step 2: Try to sync from external source
        self._log_message("Attempting external synchronization...")
        sync_success = self._sync_from_external()
        
        # Check again after external sync
        if self._check_local_models():
            self._log_message("✓ All required models verified after external sync")
            return True
        
        # Step 3: Download missing models from HuggingFace
        self._log_message("Attempting HuggingFace downloads for missing models...")
        download_success = self._download_missing_from_huggingface()
        
        # Final verification
        if self._check_local_models():
            self._log_message("✓ All required models verified after HuggingFace downloads")
            return True
        
        self._log_message("✗ Model verification failed - some models are still missing", "ERROR")
        return False
    
    def get_model_paths(self, preset_name: str) -> Dict[str, str]:
        """Get resolved model paths for preset compatibility."""
        # Load models configuration for the preset
        models_config = self._load_models_config_for_preset(preset_name)
        base_path = models_config.get("base_path", "./models")
        
        # Build paths dictionary
        result = {
            "pretrained_model_name_or_path": f"{base_path}/{models_config.get('pretrained_model', 'flux1-dev-fp8.safetensors')}"
        }
        
        # Add additional model paths if they exist in config
        for model_key in ["ae", "clip_l", "t5xxl"]:
            if model_key in models_config and models_config[model_key]:
                result[model_key] = f"{base_path}/{models_config[model_key]}"
        
        return result
    
    def _load_models_config_for_preset(self, preset_name: str) -> Dict[str, str]:
        """Load models configuration for a specific preset."""
        # Try to find preset directory in new structure first
        preset_base_dir = self.base_path / "Presets" / "Base" / preset_name
        preset_custom_dir = self.base_path / "Presets" / "Custom" / preset_name
        
        # Check custom presets first
        if preset_custom_dir.exists():
            return self._load_models_config(preset_custom_dir)
        
        # Then check base presets
        if preset_base_dir.exists():
            return self._load_models_config(preset_base_dir)
        
        # Fallback to old structure for compatibility
        old_preset_dir = self.base_path / "BasePresets" / preset_name
        if old_preset_dir.exists():
            return self._load_models_config(old_preset_dir)
        
        # Fallback to default configuration
        return {
            "base_path": "./models",
            "pretrained_model": "flux1-dev-fp8.safetensors",
            "ae": "ae.safetensors",
            "clip_l": "clip_l.safetensors", 
            "t5xxl": "t5xxl_fp8_e4m3fn.safetensors"
        }
    
    def _load_models_config(self, preset_dir: Path) -> Dict[str, str]:
        """Load models configuration from preset directory with fallback defaults."""
        models_path = preset_dir / "models.toml"
        
        # Basic defaults
        basic_defaults = {
            "base_path": "./models",
            "pretrained_model": "flux1-dev-fp8.safetensors"
        }
        
        # Flux-specific defaults
        flux_defaults = {
            "ae": "ae.safetensors",
            "clip_l": "clip_l.safetensors", 
            "t5xxl": "t5xxl_fp8_e4m3fn.safetensors"
        }
        
        if not models_path.exists():
            return {**basic_defaults, **flux_defaults}
            
        try:
            with open(models_path, 'r', encoding='utf-8') as f:
                models_config = toml.load(f).get('models', {})
                return {**basic_defaults, **models_config}
        except Exception as e:
            self._log_message(f"Warning: Failed to load models config for {preset_dir.name}: {e}")
            return {**basic_defaults, **flux_defaults}


# ===== GLOBAL FUNCTIONS =====

def verify_all_models(base_path: str = None) -> bool:
    """
    Simple global function for model verification (for main.py compatibility).
    
    Args:
        base_path: Base path for AutoTrainX project (auto-detected if None)
        
    Returns:
        bool: True if all models are verified and available
    """
    if base_path is None:
        base_path = Config.get_default_base_path()
    try:
        manager = ModelManager(base_path)
        return manager.verify_models()
    except Exception as e:
        print(f"[ERROR] Model verification failed: {str(e)}")
        return False


# ===== CONVENIENCE FUNCTIONS =====

def get_model_manager(base_path: str = None) -> ModelManager:
    """Get a ModelManager instance."""
    if base_path is None:
        base_path = Config.get_default_base_path()
    return ModelManager(base_path)


def check_models_status(base_path: str = None) -> Dict[str, bool]:
    """
    Check status of individual models without attempting to download.
    
    Args:
        base_path: Base path for AutoTrainX project (auto-detected if None)
        
    Returns:
        dict: Model name -> availability status
    """
    if base_path is None:
        base_path = Config.get_default_base_path()
    manager = ModelManager(base_path)
    status = {}
    
    for rel_path in manager.required_model_paths:
        target_file = manager.models_dir / rel_path
        model_name = target_file.name
        status[model_name] = target_file.exists()
    
    return status


# ===== MAIN EXECUTION =====

if __name__ == "__main__":
    """Allow direct execution for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoTrainX Model Manager")
    parser.add_argument("--base-path", default=Config.get_default_base_path(), 
                       help="Base path for AutoTrainX project (default: auto-detected)")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check model status without downloading")
    
    args = parser.parse_args()
    
    if args.check_only:
        print("=== MODEL STATUS CHECK ===")
        status = check_models_status(args.base_path)
        for model, available in status.items():
            status_str = "✓ Available" if available else "✗ Missing"
            print(f"{model}: {status_str}")
        
        all_available = all(status.values())
        print(f"\nOverall status: {'✓ All models available' if all_available else '✗ Some models missing'}")
        sys.exit(0 if all_available else 1)
    else:
        success = verify_all_models(args.base_path)
        sys.exit(0 if success else 1)