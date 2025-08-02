"""
Image preview generation hook for post-training.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .base import PipelineHook, HookType
from ...image_preview import ImagePreviewPipeline, PreviewConfig
from ...config import Config
from ...utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class ImagePreviewHook(PipelineHook):
    """
    Hook for generating preview images after model training.
    """
    
    def __init__(self, 
                 workflows_dir: Optional[Path] = None,
                 comfyui_url: str = "http://127.0.0.1:8188",
                 enabled: bool = True,
                 auto_detect_models: bool = True,
                 base_path: Optional[str] = None):
        """
        Initialize image preview hook.
        
        Args:
            workflows_dir: Directory containing ComfyUI workflows
            comfyui_url: URL of ComfyUI server
            enabled: Whether hook is enabled
            auto_detect_models: Whether to auto-detect trained models
            base_path: Base path for the project
        """
        super().__init__(enabled)
        
        # Set default workflows directory
        if workflows_dir is None:
            workflows_dir = Path("ComfyUI_workflow_utils/workflows")
            
        self.workflows_dir = workflows_dir
        self.comfyui_url = comfyui_url
        self.auto_detect_models = auto_detect_models
        self._preview_pipeline = None
        
        # Initialize PathManager if custom path is configured
        custom_path = Config.get_custom_output_path(base_path)
        if custom_path:
            self.path_manager = PathManager(base_path or Config.get_default_base_path(), custom_path)
        else:
            self.path_manager = None
        
    @property
    def hook_type(self) -> HookType:
        """Return hook type."""
        return HookType.POST_TRAINING
        
    @property
    def name(self) -> str:
        """Return hook name."""
        return "ImagePreviewHook"
        
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if hook should execute."""
        if not super().should_execute(context):
            return False
            
        # Check if preview was requested (--preview N)
        preview_count = context.get('preview_count', 0)
        if preview_count <= 0:
            logger.info("Skipping preview generation - no previews requested (use --preview N)")
            return False
            
        # Check if training was successful
        if not context.get('training_success', False):
            logger.info("Skipping preview generation - training was not successful")
            return False
            
        # Check if ComfyUI workflows exist
        if not self.workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {self.workflows_dir}")
            return False
            
        # Check if ComfyUI path is configured
        comfyui_path = Config.get_comfyui_path()
        if not comfyui_path:
            logger.info("Skipping preview generation - ComfyUI path not configured. Use --comfyui-path to configure.")
            return False
            
        # Validate sample images exist
        sample_dir = Path(self.workflows_dir).parent / "sample_Image"
        if not sample_dir.exists():
            logger.warning(f"Sample image directory not found: {sample_dir}")
            return False
            
        sample_images = list(sample_dir.glob("sample_image_*.jpg"))
        if not sample_images:
            logger.warning(f"No sample images found in {sample_dir}")
            return False
            
        # Validate required workflow files exist
        preset = context.get('preset', context.get('model_type', ''))
        if 'FluxLORA' in preset and not (self.workflows_dir / "Flux_LORA.json").exists():
            logger.warning(f"Required workflow file not found: Flux_LORA.json")
            return False
        elif 'SDXLCheckpoint' in preset and not (self.workflows_dir / "SDXLCheckpoint.json").exists():
            logger.warning(f"Required workflow file not found: SDXLCheckpoint.json")
            return False
            
        return True
        
    def execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute preview generation.
        
        Expected context:
        - dataset_name: Name of the dataset
        - model_type: Type of model trained (e.g., 'FluxLORA')
        - model_path: Path to trained model (optional if auto_detect)
        - training_config: Training configuration used
        - prompts: Optional list of prompts to use
        """
        try:
            logger.info(f"Executing image preview hook for {context.get('dataset_name')}")
            
            # Initialize preview pipeline if needed
            if self._preview_pipeline is None:
                base_path = context.get('base_path', Config.get_default_base_path())
                self._preview_pipeline = ImagePreviewPipeline(
                    workflows_dir=self.workflows_dir,
                    comfyui_url=self.comfyui_url,
                    base_path=base_path
                )
                
            # Check if ComfyUI was started and track the URL
            from ...utils.signal_handler import get_shutdown_handler
            shutdown_handler = get_shutdown_handler()
            
            # The preview pipeline might have started ComfyUI on a different port
            # Track whatever URL is actually being used after generation
            # This will be set after the preview pipeline executes
                
            # Get model information
            dataset_name = context.get('dataset_name')
            preset = context.get('model_type', context.get('preset'))  # Support both names
            model_path = context.get('model_path')
            preview_count = context.get('preview_count', 1)
            variation_id = context.get('variation_id')  # Get variation_id from context
            
            # Auto-detect model if needed
            if self.auto_detect_models and not model_path:
                model_path = self._find_latest_model(dataset_name, preset, variation_id)
                if not model_path:
                    logger.warning(f"Could not find trained model for {dataset_name}")
                    return None
                
            # Create preview configuration
            preview_config = self._create_preview_config(context)
            
            # Generate previews
            results = self._preview_pipeline.generate_previews(
                model_path=Path(model_path),
                preset=preset,
                dataset_name=dataset_name,
                preview_count=preview_count,
                config=preview_config,
                variation_id=variation_id  # Pass variation_id to preview pipeline
            )
            
            # Track ComfyUI URL after generation (it might have been started on a different port)
            if hasattr(self._preview_pipeline, 'comfyui_client') and hasattr(self._preview_pipeline.comfyui_client, 'server_url'):
                shutdown_handler.set_comfyui_url(self._preview_pipeline.comfyui_client.server_url)
            
            # Aggregate results
            all_success = all(r.success for r in results)
            all_images = []
            errors = []
            
            for result in results:
                if result.success:
                    all_images.extend(result.images)
                else:
                    errors.append(result.error)
            
            return {
                'preview_generated': all_success,
                'preview_images': all_images,
                'preview_error': '; '.join(errors) if errors else None,
                'preview_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"Failed to execute preview hook: {e}")
            return {
                'preview_generated': False,
                'preview_error': str(e)
            }
            
    def _find_latest_model(self, dataset_name: str, model_type: str, variation_id: Optional[str] = None) -> Optional[Path]:
        """Find the latest trained model for a dataset.
        
        Args:
            dataset_name: Name of the dataset or variation
            model_type: Type of model (e.g., 'FluxLORA')
            variation_id: Optional variation ID for variations mode
        """
        # Check if this is a variation first
        is_variation = "_v" in dataset_name and any(preset in dataset_name for preset in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"])
        
        # Use PathManager if available AND not a variation
        # For variations, we need special handling due to the exp_* directory structure
        if self.path_manager and not is_variation:
            output_dir = self.path_manager.get_model_output_path(dataset_name)
        else:
            # Fallback to default paths
            # Get base path from config
            from src.config import Config
            base_path = Path(Config.get_default_base_path())
            
            # Check if this is a variation (contains preset and version info)
            if is_variation:
                # If we have a specific variation_id, use it directly
                if variation_id:
                    output_dir = base_path / "workspace" / "variations" / f"exp_{variation_id}" / dataset_name / "model"
                    logger.debug(f"Using specific variation directory: {output_dir}")
                else:
                    # Fallback: Look for the variation in all experiment directories
                    variations_path = base_path / "workspace" / "variations"
                    logger.debug(f"No variation_id provided, searching all experiments in: {variations_path}")
                    
                    if variations_path.exists():
                        # Look for experiment directories and find the one with the most recent model
                        latest_model_path = None
                        latest_model_time = None
                        
                        for exp_dir in variations_path.glob("exp_*"):
                            variation_dir = exp_dir / dataset_name / "model"
                            logger.debug(f"Checking variation dir: {variation_dir}")
                            
                            if variation_dir.exists():
                                # Check if this directory has any model files
                                model_files = list(variation_dir.glob("*.safetensors"))
                                if model_files:
                                    # Find the most recent model in this directory
                                    most_recent = max(model_files, key=lambda p: p.stat().st_mtime)
                                    model_time = most_recent.stat().st_mtime
                                    
                                    logger.debug(f"Found {len(model_files)} models in {variation_dir}, most recent: {most_recent.name}")
                                    
                                    # Keep track of the most recent model across all experiments
                                    if latest_model_time is None or model_time > latest_model_time:
                                        latest_model_path = most_recent
                                        latest_model_time = model_time
                                        output_dir = variation_dir
                        
                        if latest_model_path:
                            logger.debug(f"Selected most recent model across all experiments: {latest_model_path}")
                            # Return the found model directly since we already searched
                            return latest_model_path
                        else:
                            # No models found in any experiment directory
                            logger.warning(f"No models found for {dataset_name} in any experiment directory")
                            return None
                    else:
                        logger.warning(f"Variations path doesn't exist: {variations_path}")
                        return None
            else:
                # Look in standard output directory
                output_dir = base_path / "workspace" / "output" / dataset_name / "model"
                logger.debug(f"Standard dataset, using: {output_dir}")
        
        logger.debug(f"Final output_dir for {dataset_name}: {output_dir}")
        
        if not output_dir.exists():
            logger.warning(f"Output directory does not exist: {output_dir}")
            return None
            
        # Find model files based on type
        if "LoRA" in model_type or "LORA" in model_type:
            pattern = "*.safetensors"
        else:
            pattern = "*.safetensors"
            
        logger.debug(f"Searching for pattern '{pattern}' in: {output_dir}")
        model_files = list(output_dir.glob(pattern))
        logger.debug(f"Found {len(model_files)} model files: {[f.name for f in model_files]}")
        
        if not model_files:
            logger.warning(f"No model files found matching pattern '{pattern}' in {output_dir}")
            return None
            
        # Return most recent file
        latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Selected latest model: {latest_model}")
        return latest_model
        
    def _load_sample_prompts(self, dataset_name: str) -> List[str]:
        """Load sample prompts for a dataset."""
        # Get base path from config if not using path_manager
        from src.config import Config
        base_path = Path(Config.get_default_base_path())
        
        # For variations, always use the original dataset's prompts
        if "_v" in dataset_name and any(preset in dataset_name for preset in ["FluxLORA", "FluxCheckpoint", "SDXLCheckpoint"]):
            # Extract original dataset name (e.g., "b09g13" from "b09g13_FluxLORA_v1")
            original_dataset = dataset_name.split("_")[0]
            if self.path_manager:
                prompts_file = self.path_manager.get_output_path(original_dataset) / "sample_prompts.txt"
            else:
                prompts_file = base_path / "workspace" / "output" / original_dataset / "sample_prompts.txt"
        else:
            if self.path_manager:
                prompts_file = self.path_manager.get_output_path(dataset_name) / "sample_prompts.txt"
            else:
                prompts_file = base_path / "workspace" / "output" / dataset_name / "sample_prompts.txt"
        
        if prompts_file.exists():
            with open(prompts_file, 'r') as f:
                prompts = [line.strip() for line in f if line.strip()]
                return prompts[:5]  # Use first 5 prompts
                
        # Default prompts if none found
        return [
            f"a photo of {dataset_name}",
            f"a portrait of {dataset_name}",
            f"professional photo of {dataset_name}"
        ]
        
    def _create_preview_config(self, context: Dict[str, Any]) -> PreviewConfig:
        """Create preview configuration from context."""
        training_config = context.get('training_config', {})
        
        # Extract relevant parameters from training config
        config = PreviewConfig(
            steps=20,  # Faster for previews
            cfg_scale=training_config.get('cfg_scale', 7.5),
            width=training_config.get('resolution', 1024),
            height=training_config.get('resolution', 1024),
            seed=42  # Fixed seed for consistency
        )
        
        return config