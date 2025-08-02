"""
Example of how to configure and use ComfyUI integration with AutoTrainX.

This example demonstrates:
1. How to set the ComfyUI path
2. How the path is saved for future use
3. How the ImagePreview module uses the saved path
"""

from pathlib import Path
from src.config import Config
from src.image_preview import ComfyUIManager

def example_configure_comfyui():
    """
    Example showing how to configure ComfyUI path.
    
    You can do this via command line:
    python main.py --comfyui-path /path/to/ComfyUI
    
    Or programmatically:
    """
    # Set ComfyUI path programmatically
    comfyui_path = "/home/user/ComfyUI"
    Config.set_comfyui_path(comfyui_path)
    
    # Check if path was saved
    saved_path = Config.get_comfyui_path()
    print(f"Saved ComfyUI path: {saved_path}")
    
    # The path is now saved in config.json and will be used automatically
    

def example_check_comfyui_setup():
    """
    Example showing how to check ComfyUI setup.
    """
    # Get saved ComfyUI path
    comfyui_path = Config.get_comfyui_path()
    
    if not comfyui_path:
        print("ComfyUI path not configured!")
        print("Run: python main.py --comfyui-path /path/to/ComfyUI")
        return
        
    print(f"ComfyUI configured at: {comfyui_path}")
    
    # Check if ComfyUI is running
    if ComfyUIManager.is_comfyui_running():
        print("✓ ComfyUI is running")
    else:
        print("✗ ComfyUI is not running")
        
    # Check model paths
    lora_path = ComfyUIManager.get_lora_path()
    checkpoint_path = ComfyUIManager.get_checkpoint_path()
    
    if lora_path:
        print(f"✓ LoRA models directory: {lora_path}")
    else:
        print("✗ LoRA models directory not found")
        
    if checkpoint_path:
        print(f"✓ Checkpoint models directory: {checkpoint_path}")
    else:
        print("✗ Checkpoint models directory not found")
        

def example_command_line_usage():
    """
    Example command line usage for ComfyUI integration.
    """
    print("ComfyUI Integration Examples:")
    print("=" * 50)
    
    print("\n1. Configure ComfyUI path (one-time setup):")
    print("   python main.py --comfyui-path /home/user/ComfyUI")
    
    print("\n2. Train with automatic preview generation:")
    print("   python main.py --train --single --source /path/to/dataset --preset FluxLORA")
    print("   (ComfyUI will be started automatically if needed)")
    
    print("\n3. Check current configuration:")
    print("   python main.py --status")
    print("   (Will show if ComfyUI is configured)")
    
    print("\n4. The configuration is saved in config.json:")
    print("   {")
    print('     "COMFYPATH": "/home/user/ComfyUI"')
    print("   }")
    

if __name__ == "__main__":
    print("ComfyUI Setup Examples")
    print("=" * 50)
    
    # Check current setup
    example_check_comfyui_setup()
    
    print("\n" + "=" * 50)
    print("Command Line Usage:")
    print("=" * 50)
    example_command_line_usage()