"""
Main pipeline for generating preview images using ComfyUI.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .workflow_handler import WorkflowHandler
from .comfyui_client import ComfyUIClient
from .models import PreviewConfig, PreviewResult
from .utils import ComfyUIManager
from .model_manager import ComfyUIModelManager

logger = logging.getLogger(__name__)


class ImagePreviewPipeline:
    """
    Pipeline for generating preview images after model training.
    
    This pipeline:
    1. Loads pre-configured ComfyUI workflows
    2. Modifies workflows based on trained model and parameters
    3. Sends workflows to ComfyUI for execution
    4. Saves generated preview images
    """
    
    def __init__(self, 
                 workflows_dir: Path,
                 comfyui_url: str = "http://127.0.0.1:8188",
                 output_dir: Optional[Path] = None,
                 base_path: Optional[str] = None):
        """
        Initialize the image preview pipeline.
        
        Args:
            workflows_dir: Directory containing ComfyUI workflow templates
            comfyui_url: URL of the ComfyUI server
            output_dir: Directory to save preview images
            base_path: Base path for the project
        """
        self.workflows_dir = Path(workflows_dir)
        self.output_dir = output_dir or Path("workspace/output")
        self.base_path = base_path
        
        self.workflow_handler = WorkflowHandler(workflows_dir, base_path=base_path)
        self.comfyui_client = ComfyUIClient(comfyui_url)
        
    def generate_previews(self, 
                         model_path: Path,
                         preset: str,
                         dataset_name: str,
                         preview_count: int = 1,
                         config: Optional[PreviewConfig] = None,
                         variation_id: Optional[str] = None) -> List[PreviewResult]:
        """
        Generate preview images for a trained model.
        
        Args:
            model_path: Path to the trained model
            preset: Preset name (e.g., 'FluxLORA', 'SDXLCheckpoint')
            dataset_name: Name of the dataset used for training
            preview_count: Number of preview images to generate
            config: Optional preview configuration
            
        Returns:
            List of PreviewResult objects
        """
        logger.info(f"Generating {preview_count} previews for {dataset_name} using {preset}")
        
        # Ensure ComfyUI is running
        success, actual_url = ComfyUIManager.ensure_comfyui_running(self.comfyui_client.server_url)
        if not success:
            logger.error("Failed to ensure ComfyUI is running")
            return [PreviewResult(
                success=False,
                dataset_name=dataset_name,
                model_type=preset,
                error="ComfyUI is not running and could not be started"
            )]
        
        # Update client URL if port changed
        if actual_url != self.comfyui_client.server_url:
            logger.info(f"Updating ComfyUI client URL from {self.comfyui_client.server_url} to {actual_url}")
            self.comfyui_client.server_url = actual_url
        
        # Initialize model manager
        try:
            model_manager = ComfyUIModelManager(base_path=self.base_path)
        except ValueError as e:
            logger.error(f"Failed to initialize model manager: {e}")
            return [PreviewResult(
                success=False,
                dataset_name=dataset_name,
                model_type=preset,
                error=str(e)
            )]
        
        results = []
        
        # Use context manager to handle model copying/removal
        with model_manager.temporary_model(model_path, preset) as model_filename:
            # Load appropriate workflow template
            try:
                workflow = self.workflow_handler.load_workflow(preset)
            except Exception as e:
                logger.error(f"Failed to load workflow: {e}")
                return [PreviewResult(
                    success=False,
                    dataset_name=dataset_name,
                    model_type=preset,
                    error=f"Failed to load workflow: {e}"
                )]
            
            # Generate multiple previews
            for preview_index in range(1, preview_count + 1):
                logger.info(f"Generating preview {preview_index}/{preview_count}")
                
                try:
                    # Modify workflow for this preview
                    modified_workflow = self.workflow_handler.modify_workflow(
                        workflow=workflow,
                        model_filename=model_filename,
                        dataset_name=dataset_name,
                        preset=preset,
                        preview_index=preview_index
                    )
                    
                    # Send to ComfyUI for execution
                    job_id = self.comfyui_client.execute_workflow(modified_workflow, dataset_name)
                    
                    # Wait for completion (don't worry about download errors, images are saved locally)
                    try:
                        images = self.comfyui_client.wait_for_completion(job_id)
                    except Exception as e:
                        logger.debug(f"Image download via API not available (this is normal): {e}")
                        images = []  # Empty list, we'll rely on local files
                    
                    # The workflow should save images automatically to the correct location
                    # based on our customizations
                    # Get base path for absolute paths
                    base_path = Path(self.base_path) if self.base_path else Path.cwd()
                    
                    # Check if this is a variation and use the appropriate directory structure
                    if "_v" in dataset_name and any(p in dataset_name for p in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"]):
                        # For variations, use the specific variation_id if provided
                        if variation_id:
                            preview_dir = base_path / "workspace" / "variations" / f"exp_{variation_id}" / dataset_name / "Preview"
                            logger.debug(f"Using specific variation preview dir: {preview_dir}")
                        else:
                            # Fallback: look in the new structure
                            variations_path = base_path / "workspace" / "variations"
                            if variations_path.exists():
                                # Find the experiment directory containing this variation
                                preview_dir = None
                                for exp_dir in variations_path.glob("exp_*"):
                                    variation_dir = exp_dir / dataset_name
                                    if variation_dir.exists():
                                        preview_dir = variation_dir / "Preview"
                                        break
                                
                                if preview_dir is None:
                                    # Fallback to old structure if not found
                                    preview_dir = base_path / "workspace" / "variations" / dataset_name / "Preview"
                            else:
                                preview_dir = base_path / "workspace" / "variations" / dataset_name / "Preview"
                    else:
                        # Standard output directory for single/batch modes
                        preview_dir = base_path / "workspace" / "output" / dataset_name / "Preview"
                    
                    preview_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Check for various filename patterns that ComfyUI might generate
                    # For variations, dataset_name already includes preset
                    if "_v" in dataset_name and preset in dataset_name:
                        # Variations pattern: dataset_name_XX.png
                        possible_filenames = [
                            f"{dataset_name}_{preview_index:02d}.png",
                            f"{dataset_name}_{preview_index:02d}_0001.png",
                            f"{dataset_name}_{preview_index:02d}_00001.png",
                            f"{dataset_name}_{preview_index:02d}_0001_SUFFIX.png",
                            f"{dataset_name}_{preview_index:02d}_SUFFIX.png",
                            f"{dataset_name}_{preview_index:02d}_1.png",
                            f"{dataset_name}_{preview_index:02d}_001.png"
                        ]
                    else:
                        # Single/batch pattern: dataset_preset_XX.png
                        possible_filenames = [
                            f"{dataset_name}_{preset}_{preview_index:02d}.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_0001.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_00001.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_0001_SUFFIX.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_SUFFIX.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_1.png",
                            f"{dataset_name}_{preset}_{preview_index:02d}_001.png"
                        ]
                    
                    saved_images = []
                    for filename in possible_filenames:
                        file_path = preview_dir / filename
                        if file_path.exists():
                            saved_images.append(file_path)
                            logger.info(f"Found generated image: {file_path}")
                            break
                    
                    if not saved_images:
                        # Fallback: save returned images if workflow didn't save them
                        logger.debug(f"No images found locally for preview {preview_index} with expected patterns, checking for downloaded images")
                        if images:
                            for idx, image_data in enumerate(images):
                                # Use appropriate naming pattern for fallback
                                if "_v" in dataset_name and preset in dataset_name:
                                    fallback_filename = f"{dataset_name}_{preview_index:02d}_fallback.png"
                                else:
                                    fallback_filename = f"{dataset_name}_{preset}_{preview_index:02d}_fallback.png"
                                image_path = preview_dir / fallback_filename
                                with open(image_path, 'wb') as f:
                                    f.write(image_data)
                                saved_images.append(image_path)
                                logger.info(f"Saved downloaded image as: {image_path}")
                        else:
                            # Try to find any PNG file that might match
                            logger.debug(f"No downloaded images available, searching for any matching files in {preview_dir}")
                            pattern_files = list(preview_dir.glob(f"{dataset_name}*{preview_index:02d}*.png"))
                            if pattern_files:
                                saved_images.extend(pattern_files)
                                logger.info(f"Found generated images: {[f.name for f in pattern_files]}")
                            else:
                                logger.warning(f"No preview images found for preview {preview_index}")
                    
                    results.append(PreviewResult(
                        success=True,
                        dataset_name=dataset_name,
                        model_type=preset,
                        images=saved_images,
                        workflow_used=preset
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to generate preview {preview_index}: {str(e)}")
                    results.append(PreviewResult(
                        success=False,
                        dataset_name=dataset_name,
                        model_type=preset,
                        error=f"Preview {preview_index}: {str(e)}"
                    ))
        
        # Shutdown ComfyUI after all previews are generated
        logger.info("Shutting down ComfyUI after preview generation")
        ComfyUIManager.shutdown_comfyui(self.comfyui_client.server_url)
        
        return results
            
    def generate_preview(self, 
                        model_path: Path,
                        model_type: str,
                        dataset_name: str,
                        prompts: Optional[List[str]] = None,
                        config: Optional[PreviewConfig] = None) -> PreviewResult:
        """
        Generate a single preview image (backward compatibility).
        
        Args:
            model_path: Path to the trained model
            model_type: Type of model (used as preset)
            dataset_name: Name of the dataset
            prompts: Optional list of prompts (not used in new system)
            config: Optional preview configuration
            
        Returns:
            Single PreviewResult
        """
        results = self.generate_previews(
            model_path=model_path,
            preset=model_type,
            dataset_name=dataset_name,
            preview_count=1,
            config=config
        )
        return results[0] if results else PreviewResult(
            success=False,
            dataset_name=dataset_name,
            model_type=model_type,
            error="No results generated"
        )