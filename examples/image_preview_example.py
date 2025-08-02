"""
Example of how ImagePreview integrates with the AutoTrainX pipeline.

This example demonstrates:
1. How the pipeline automatically triggers preview generation after training
2. How to manually control preview generation
3. How to customize preview settings
"""

from pathlib import Path
from src.pipeline import AutoTrainPipeline
from src.image_preview import ImagePreviewPipeline, PreviewConfig

def example_with_automatic_preview():
    """
    Example showing automatic preview generation after training.
    
    The pipeline will automatically generate previews when:
    1. ComfyUI workflows are available
    2. Training completes successfully
    3. Preview hook is enabled (default)
    """
    # Initialize pipeline - preview hook is automatically registered
    pipeline = AutoTrainPipeline()
    
    # The pipeline will prepare dataset and generate configs
    result = pipeline.prepare_and_configure(
        source_path="/path/to/dataset",
        repeats=30,
        class_name="person"
    )
    
    print(f"Dataset prepared: {result.successful_datasets}/{result.total_datasets}")
    
    # After training completes (using sd-scripts), the preview hook will:
    # 1. Detect the trained model
    # 2. Load the appropriate ComfyUI workflow
    # 3. Generate preview images
    # 4. Save them to workspace/output/dataset_name/previews/
    
    
def example_with_manual_preview():
    """
    Example showing manual preview generation.
    """
    # Initialize preview pipeline directly
    preview_pipeline = ImagePreviewPipeline(
        workflows_dir=Path("ComfyUI_workflow_utils/workflows"),
        comfyui_url="http://127.0.0.1:8188"
    )
    
    # Generate preview for a specific model
    result = preview_pipeline.generate_preview(
        model_path=Path("workspace/output/my_dataset/model/my_lora.safetensors"),
        model_type="FluxLORA",
        dataset_name="my_dataset",
        prompts=[
            "a photo of my_dataset",
            "a portrait of my_dataset in professional lighting",
            "my_dataset in a natural setting"
        ],
        config=PreviewConfig(
            steps=20,
            cfg_scale=7.5,
            width=1024,
            height=1024,
            seed=42
        )
    )
    
    if result.success:
        print(f"Generated {result.image_count} preview images:")
        for img in result.images:
            print(f"  - {img}")
    else:
        print(f"Preview generation failed: {result.error}")
        
        
def example_with_custom_settings():
    """
    Example showing how to customize preview settings.
    """
    # Initialize pipeline
    pipeline = AutoTrainPipeline()
    
    # Disable automatic preview
    pipeline.enable_image_preview(enabled=False)
    
    # Or enable with custom ComfyUI URL
    pipeline.enable_image_preview(
        enabled=True,
        comfyui_url="http://192.168.1.100:8188"  # Remote ComfyUI server
    )
    
    
def example_batch_preview():
    """
    Example showing batch preview generation for multiple models.
    """
    preview_pipeline = ImagePreviewPipeline(
        workflows_dir=Path("ComfyUI_workflow_utils/workflows")
    )
    
    # Define multiple models to generate previews for
    models = [
        {
            'path': 'workspace/output/dataset1/model/lora.safetensors',
            'type': 'FluxLORA',
            'dataset': 'dataset1',
            'prompts': ['a photo of dataset1']
        },
        {
            'path': 'workspace/output/dataset2/model/checkpoint.safetensors',
            'type': 'SDXLCheckpoint', 
            'dataset': 'dataset2',
            'prompts': ['a portrait of dataset2']
        }
    ]
    
    # Generate previews for all models
    results = preview_pipeline.batch_generate_previews(
        models=models,
        config=PreviewConfig(steps=15, cfg_scale=7.0)
    )
    
    # Check results
    for result in results:
        print(f"{result.dataset_name}: {'Success' if result.success else 'Failed'}")
        

if __name__ == "__main__":
    print("ImagePreview Integration Examples")
    print("=" * 50)
    
    print("\n1. Automatic preview generation is enabled by default")
    print("   After training, previews will be generated automatically")
    
    print("\n2. Manual preview generation gives you full control")
    print("   Use ImagePreviewPipeline directly for custom workflows")
    
    print("\n3. Preview settings can be customized via PreviewConfig")
    print("   Control steps, CFG scale, resolution, and more")
    
    print("\n4. Batch processing is supported for multiple models")
    print("   Generate previews for many models efficiently")