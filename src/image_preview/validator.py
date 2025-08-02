"""
Validation utilities for image preview system.

This module provides comprehensive validation for all components
required for successful preview generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

from ..config import Config

logger = logging.getLogger(__name__)


class PreviewSystemValidator:
    """Validates all components required for preview generation."""
    
    @staticmethod
    def validate_all() -> Tuple[bool, List[str]]:
        """
        Perform comprehensive validation of the preview system.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # 1. Validate ComfyUI configuration
        comfyui_errors = PreviewSystemValidator.validate_comfyui_setup()
        errors.extend(comfyui_errors)
        
        # 2. Validate workflows
        workflow_errors = PreviewSystemValidator.validate_workflows()
        errors.extend(workflow_errors)
        
        # 3. Validate sample images
        sample_errors = PreviewSystemValidator.validate_sample_images()
        errors.extend(sample_errors)
        
        # 4. Validate ComfyUI model directories
        model_dir_errors = PreviewSystemValidator.validate_comfyui_model_dirs()
        errors.extend(model_dir_errors)
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def validate_comfyui_setup() -> List[str]:
        """Validate ComfyUI is properly configured."""
        errors = []
        
        # Check if ComfyUI path is configured
        comfyui_path = Config.get_comfyui_path()
        if not comfyui_path:
            errors.append("ComfyUI path not configured. Use: python main.py --comfyui-path /path/to/ComfyUI")
            return errors
            
        # Check if ComfyUI directory exists
        comfyui_dir = Path(comfyui_path)
        if not comfyui_dir.exists():
            errors.append(f"ComfyUI directory not found: {comfyui_dir}")
            return errors
            
        # Check if main.py exists in ComfyUI
        main_py = comfyui_dir / "main.py"
        if not main_py.exists():
            errors.append(f"ComfyUI main.py not found. Invalid ComfyUI installation at: {comfyui_dir}")
            
        return errors
    
    @staticmethod
    def validate_workflows() -> List[str]:
        """Validate required workflow files exist."""
        errors = []
        base_path = Path.cwd()
        workflows_dir = base_path / "ComfyUI_workflow_utils" / "workflows"
        
        if not workflows_dir.exists():
            errors.append(f"Workflows directory not found: {workflows_dir}")
            return errors
            
        # Check required workflow files
        required_workflows = {
            "Flux_LORA.json": "FluxLORA preset",
            "SDXLCheckpoint.json": "SDXLCheckpoint preset"
        }
        
        for workflow_file, description in required_workflows.items():
            workflow_path = workflows_dir / workflow_file
            if not workflow_path.exists():
                errors.append(f"Missing workflow file for {description}: {workflow_path}")
            else:
                # Validate it's a valid JSON file
                try:
                    import json
                    with open(workflow_path, 'r') as f:
                        json.load(f)
                except Exception as e:
                    errors.append(f"Invalid JSON in workflow file {workflow_path}: {e}")
                    
        return errors
    
    @staticmethod
    def validate_sample_images() -> List[str]:
        """Validate sample images exist."""
        errors = []
        base_path = Path.cwd()
        sample_dir = base_path / "ComfyUI_workflow_utils" / "sample_Image"
        
        if not sample_dir.exists():
            errors.append(f"Sample image directory not found: {sample_dir}")
            return errors
            
        # Check for sample images
        sample_images = list(sample_dir.glob("sample_image_*.jpg"))
        if not sample_images:
            errors.append(
                f"No sample images found in {sample_dir}. "
                f"Expected files like: sample_image_01.jpg, sample_image_02.jpg, etc."
            )
        else:
            logger.info(f"Found {len(sample_images)} sample images")
            
        return errors
    
    @staticmethod
    def validate_comfyui_model_dirs() -> List[str]:
        """Validate ComfyUI model directories."""
        errors = []
        
        comfyui_path = Config.get_comfyui_path()
        if not comfyui_path:
            return ["ComfyUI path not configured"]
            
        comfyui_dir = Path(comfyui_path)
        models_dir = comfyui_dir / "models"
        
        if not models_dir.exists():
            errors.append(f"ComfyUI models directory not found: {models_dir}")
            return errors
            
        # Check subdirectories
        required_dirs = {
            "loras": "LoRA models",
            "checkpoints": "Checkpoint models"
        }
        
        for dir_name, description in required_dirs.items():
            dir_path = models_dir / dir_name
            if not dir_path.exists():
                logger.warning(f"{description} directory not found: {dir_path} (will be created when needed)")
            else:
                # Check if writable
                test_file = dir_path / ".write_test"
                try:
                    test_file.touch()
                    test_file.unlink()
                except Exception as e:
                    errors.append(f"{description} directory is not writable: {dir_path}")
                    
        return errors
    
    @staticmethod
    def print_validation_report():
        """Print a detailed validation report."""
        print("\n=== Image Preview System Validation ===\n")
        
        is_valid, errors = PreviewSystemValidator.validate_all()
        
        if is_valid:
            print("✅ All validations passed! The image preview system is ready to use.")
            print("\nTo generate previews after training, use:")
            print("  python main.py --train --single --source /path/to/dataset --preset FluxLORA --preview 5")
        else:
            print("❌ Validation failed. Please fix the following issues:\n")
            for i, error in enumerate(errors, 1):
                print(f"{i}. {error}")
                
            print("\n💡 Quick fixes:")
            if any("ComfyUI path not configured" in e for e in errors):
                print("  - Set ComfyUI path: python main.py --comfyui-path /path/to/ComfyUI")
            if any("Sample image" in e for e in errors):
                print("  - Add sample images to ComfyUI_workflow_utils/sample_Image/")
                print("    Files should be named: sample_image_01.jpg, sample_image_02.jpg, etc.")
            if any("workflow" in e.lower() for e in errors):
                print("  - Ensure workflow JSON files are in ComfyUI_workflow_utils/workflows/")
                
        print("\n" + "="*40 + "\n")