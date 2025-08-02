#!/usr/bin/env python3
"""
Example usage of the unified ModelManager system.

This script demonstrates how to use the new ModelManager class
and its various functions for model verification and management.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.scripts.models import (
    ModelManager,
    TrainingConfig,
    ValidationError,
    verify_all_models,
    check_models_status,
    get_model_manager
)


def main():
    """Demonstrate ModelManager usage."""
    
    print("=== AutoTrainX Model Manager Example ===\n")
    
    # 1. Simple global verification (for main.py)
    print("1. Simple verification using global function:")
    result = verify_all_models()
    print(f"   Result: {'✓ Success' if result else '✗ Failed'}\n")
    
    # 2. Check individual model status
    print("2. Individual model status:")
    status = check_models_status()
    for model, available in status.items():
        status_str = "✓ Available" if available else "✗ Missing"
        print(f"   {model}: {status_str}")
    print()
    
    # 3. Using ModelManager directly
    print("3. Using ModelManager class:")
    manager = get_model_manager()
    
    # Get model paths for a preset
    print("   Model paths for 'flux_lora' preset:")
    paths = manager.get_model_paths("flux_lora")
    for key, path in paths.items():
        print(f"   {key}: {path}")
    print()
    
    # 4. TrainingConfig compatibility
    print("4. TrainingConfig compatibility:")
    config = TrainingConfig(
        learning_rate=0.001,
        epochs=100,
        batch_size=4,
        pretrained_model_name_or_path="./models/flux1-dev-fp8.safetensors"
    )
    print(f"   Config created: {config.get('learning_rate')} LR, {config.get('epochs')} epochs")
    print(f"   Dict format: {config.dict()}")
    print()
    
    # 5. Manual verification with detailed logging
    print("5. Manual verification with detailed logging:")
    detailed_result = manager.verify_models()
    print(f"   Detailed verification result: {'✓ Success' if detailed_result else '✗ Failed'}")


if __name__ == "__main__":
    main()