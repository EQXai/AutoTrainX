"""
AutoTrainX Pipeline - Unified modular pipeline system.

This module provides the main entry point for all pipeline operations,
routing requests to appropriate pipeline implementations based on mode.
"""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from ..config import Config
from .base import PipelineConfig, PipelineResult
from .utils.pipeline_factory import PipelineFactory

# Make ImagePreview import optional
try:
    from .hooks import ImagePreviewHook
    PREVIEW_AVAILABLE = True
except ImportError:
    PREVIEW_AVAILABLE = False
    ImagePreviewHook = None

# Import for backward compatibility
from .base.pipeline_result import DatasetResult, PipelineStatus


class AutoTrainPipeline:
    """
    Main pipeline facade that routes to appropriate implementations.
    
    This class maintains backward compatibility while providing
    access to new modular pipeline modes.
    """
    
    def __init__(self, base_path: str = None, 
                 config: Optional[PipelineConfig] = None):
        """
        Initialize the pipeline router.
        
        Args:
            base_path: Base path for AutoTrainX project (auto-detected if None)
            config: Optional pipeline configuration
        """
        if base_path is None:
            base_path = Config.get_default_base_path()
        self.base_path = Path(base_path)
        self.config = config or PipelineConfig(base_path=base_path)
        
        # Initialize pipeline implementations using factory
        self._pipelines = {
            'single': PipelineFactory.create('single', self.config),
            'batch': PipelineFactory.create('batch', self.config),
            'variations': PipelineFactory.create('variations', self.config)
        }
        
        # Keep references for backward compatibility
        self._single_pipeline = self._pipelines['single']
        self._batch_pipeline = self._pipelines['batch']
        self._variations_pipeline = self._pipelines['variations']
        
        # For backward compatibility
        self.dataset_preparator = self._single_pipeline.dataset_preparator
        self.preset_manager = self._single_pipeline.preset_manager
        
        # Use PathManager if available
        if self.config.path_manager:
            self.presets_dir = self.config.path_manager.get_workspace_path() / "Presets"
        else:
            self.presets_dir = self.base_path / "workspace/Presets"
        
        # Initialize hooks
        self._setup_default_hooks()
        
    # ========== New Modular Methods ==========
    
    def execute(self, mode: str, **kwargs) -> PipelineResult:
        """
        Execute pipeline in specified mode.
        
        Args:
            mode: Execution mode ('single', 'batch', 'variations')
            **kwargs: Mode-specific parameters
            
        Returns:
            PipelineResult with execution details
        """
        # Validate mode
        available_modes = PipelineFactory.available_modes()
        if mode not in available_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of: {', '.join(available_modes)}")
            
        # Route to appropriate pipeline
        return self._pipelines[mode].execute(**kwargs)
            
    def get_execution_plan(self, mode: str, **kwargs) -> Dict[str, Any]:
        """
        Get execution plan for specified mode without executing.
        
        Args:
            mode: Execution mode
            **kwargs: Mode-specific parameters
            
        Returns:
            Execution plan details
        """
        available_modes = PipelineFactory.available_modes()
        if mode not in available_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of: {', '.join(available_modes)}")
            
        return self._pipelines[mode].get_execution_plan(**kwargs)
            
    # ========== Backward Compatibility Methods ==========
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status and available resources.
        
        Maintained for backward compatibility.
        """
        # Get available datasets
        input_datasets = []
        if self.dataset_preparator.input_path.exists():
            input_datasets = [d.name for d in self.dataset_preparator.input_path.iterdir() if d.is_dir()]
            
        output_datasets = []
        if self.dataset_preparator.output_path.exists():
            output_datasets = [d.name for d in self.dataset_preparator.output_path.iterdir() if d.is_dir()]
            
        # Get available presets  
        presets = self.preset_manager.get_presets()
        available_presets = list(presets.keys())
        preset_descriptions = {name: info.description for name, info in presets.items()}
        
        # Get generated configurations
        generated_configs = []
        if self.presets_dir.exists():
            for preset_dir in self.presets_dir.iterdir():
                if preset_dir.is_dir():
                    for config_file in preset_dir.iterdir():
                        if config_file.is_file() and config_file.suffix == '.toml':
                            generated_configs.append(config_file.stem)
        
        # Get variation experiments
        variation_experiments = []
        variations_path = Path(self.base_path) / "workspace" / "variations"
        if variations_path.exists():
            for exp_dir in variations_path.iterdir():
                if exp_dir.is_dir() and exp_dir.name.startswith("exp_"):
                    # Read experiment.json if exists
                    exp_json = exp_dir / "experiment.json"
                    if exp_json.exists():
                        import json
                        with open(exp_json, 'r') as f:
                            exp_data = json.load(f)
                            variation_experiments.append({
                                "variation_id": exp_data.get("variation_id"),
                                "dataset": exp_data.get("dataset"),
                                "preset": exp_data.get("preset"),
                                "created": exp_data.get("created"),
                                "total_variations": exp_data.get("total_variations"),
                                "parameters_varied": exp_data.get("parameters_varied"),
                                "path": str(exp_dir)
                            })
        
        # Get ComfyUI configuration
        from ..config import Config
        comfyui_path = Config.get_comfyui_path(str(self.base_path))
        comfyui_configured = comfyui_path is not None
                    
        return {
            "pipeline_status": "ready",
            "base_path": str(self.base_path),
            "available_modes": PipelineFactory.available_modes(),
            "config": {
                "parallel_enabled": self.config.parallel,
                "max_workers": self.config.max_workers,
                "auto_clean": self.config.auto_clean
            },
            "datasets": {
                "input_datasets": input_datasets,
                "output_datasets": output_datasets,
                "total_input": len(input_datasets),
                "total_output": len(output_datasets)
            },
            "variations": {
                "experiments": variation_experiments,
                "total_experiments": len(variation_experiments)
            },
            "presets": {
                "available_presets": available_presets,
                "preset_descriptions": preset_descriptions,
                "total_presets": len(available_presets)
            },
            "configurations": {
                "generated_configs": generated_configs,
                "total_configs": len(generated_configs)
            },
            "directories": {
                "input_path": str(self.dataset_preparator.input_path),
                "output_path": str(self.dataset_preparator.output_path),
                "presets_path": str(self.presets_dir)
            },
            "comfyui": {
                "configured": comfyui_configured,
                "path": comfyui_path if comfyui_configured else None,
                "preview_enabled": comfyui_configured
            }
        }
        
    def prepare_dataset_only(self, source_path: str, 
                           repeats: int = 30, class_name: str = "person",
                           auto_clean: bool = False) -> PipelineResult:
        """
        Prepare dataset only without generating configurations.
        
        Maintained for backward compatibility.
        """
        self.config.auto_clean = auto_clean
        
        result = self.execute(
            mode='single',
            source_path=source_path,
            repeats=repeats,
            class_name=class_name,
            generate_configs=False
        )
        
        return self._convert_to_legacy_result(result)
            
    def generate_configs_only(self, dataset_name: Optional[str] = None) -> PipelineResult:
        """
        Generate preset configurations for existing datasets.
        
        Maintained for backward compatibility.
        """
        if dataset_name:
            # Single dataset config generation
            result = self.execute(
                mode='single',
                source_path=str(self.dataset_preparator.output_path / dataset_name),
                dataset_name=dataset_name,
                generate_configs=True
            )
        else:
            # Batch config generation for all datasets
            output_datasets = []
            if self.dataset_preparator.output_path.exists():
                output_datasets = [
                    {"source_path": str(self.dataset_preparator.output_path / d.name), 
                     "dataset_name": d.name}
                    for d in self.dataset_preparator.output_path.iterdir() 
                    if d.is_dir()
                ]
                
            if output_datasets:
                result = self.execute(
                    mode='batch',
                    datasets=output_datasets,
                    strategy='sequential'
                )
            else:
                return PipelineResult(
                    status=PipelineStatus.FAILED,
                    mode='single',
                    total_datasets=0,
                    successful_datasets=0,
                    failed_datasets=0,
                    error_message="No datasets found to generate configurations for"
                )
                
        return self._convert_to_legacy_result(result)
            
    def prepare_and_configure(self, source_path: str,
                            repeats: int = 30, class_name: str = "person",
                            auto_clean: bool = False) -> PipelineResult:
        """
        Complete pipeline: prepare dataset and generate configurations.
        
        Maintained for backward compatibility.
        """
        # Update config with auto_clean
        self.config.auto_clean = auto_clean
        
        # Use single pipeline mode
        result = self.execute(
            mode='single',
            source_path=source_path,
            repeats=repeats,
            class_name=class_name,
            generate_configs=True
        )
        
        # Convert to old-style result if needed
        return self._convert_to_legacy_result(result)
            
    def list_available_presets(self) -> Dict[str, str]:
        """
        Get list of available presets with descriptions.
        
        Returns:
            Dictionary mapping preset names to descriptions
        """
        presets = self.preset_manager.get_presets()
        return {name: info.description for name, info in presets.items()}
        
    def list_prepared_datasets(self) -> List[str]:
        """
        Get list of prepared datasets.
        
        Returns:
            List of dataset names that have been prepared
        """
        datasets = []
        if self.dataset_preparator.output_path.exists():
            datasets = [
                d.name for d in self.dataset_preparator.output_path.iterdir() 
                if d.is_dir()
            ]
        return sorted(datasets)
        
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific prepared dataset.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Dictionary with dataset information or None if not found
        """
        dataset_dir = self.dataset_preparator.output_path / dataset_name
        if not dataset_dir.exists():
            return None
            
        # Count files in training directory
        img_dir = dataset_dir / "img"
        total_images = 0
        total_texts = 0
        training_dir = None
        
        if img_dir.exists():
            for subdir in img_dir.iterdir():
                if subdir.is_dir():
                    training_dir = subdir
                    for file in subdir.iterdir():
                        if file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                            total_images += 1
                        elif file.suffix.lower() == '.txt':
                            total_texts += 1
                    break
                    
        # Check for sample prompts
        sample_prompts_file = dataset_dir / "sample_prompts.txt"
        has_prompts = sample_prompts_file.exists()
        
        return {
            "dataset_name": dataset_name,
            "dataset_dir": str(dataset_dir),
            "training_dir": str(training_dir) if training_dir else None,
            "total_images": total_images,
            "total_texts": total_texts,
            "has_sample_prompts": has_prompts,
            "sample_prompts_file": str(sample_prompts_file) if has_prompts else None,
            "model_dir": str(dataset_dir / "model"),
            "log_dir": str(dataset_dir / "log")
        }
        
    def _convert_to_legacy_result(self, result: PipelineResult) -> PipelineResult:
        """Convert new result format to legacy format if needed."""
        # The new PipelineResult is designed to be backward compatible
        # This method ensures any necessary conversions
        return result
        
    # ========== Convenience Methods ==========
    
    def batch_prepare(self, datasets: List[Union[str, Dict[str, Any]]],
                     parallel: bool = False) -> PipelineResult:
        """
        Convenience method for batch dataset preparation.
        
        Args:
            datasets: List of dataset paths or configurations
            parallel: Whether to process in parallel
            
        Returns:
            PipelineResult with batch processing details
        """
        self.config.parallel = parallel
        
        return self.execute(
            mode='batch',
            datasets=datasets,
            strategy='parallel' if parallel else 'sequential'
        )
        
    def create_variations(self, dataset_name: str, base_preset: str,
                         **variations) -> PipelineResult:
        """
        Convenience method for creating configuration variations.
        
        Args:
            dataset_name: Name of prepared dataset
            base_preset: Base preset for variations
            **variations: Parameter variations (e.g., learning_rate=[1e-4, 1e-5])
            
        Returns:
            PipelineResult with variation details
        """
        return self.execute(
            mode='variations',
            dataset_name=dataset_name,
            base_preset=base_preset,
            variations=variations
        )
        
    def _setup_default_hooks(self):
        """Setup default hooks for the pipeline."""
        # Hooks are now managed by HookManager in each pipeline
        # This method is kept for backward compatibility but does nothing
        pass
                
    def enable_image_preview(self, enabled: bool = True, comfyui_url: Optional[str] = None):
        """
        Enable or disable image preview generation.
        
        Args:
            enabled: Whether to enable preview generation
            comfyui_url: Optional ComfyUI server URL
        """
        # Find existing preview hooks
        for pipeline in self._pipelines.values():
            if hasattr(pipeline, '_hooks') and 'post_training' in pipeline._hooks:
                for hook in pipeline._hooks['post_training']:
                    if PREVIEW_AVAILABLE and isinstance(hook, ImagePreviewHook):
                        hook.enabled = enabled
                        if comfyui_url:
                            hook.comfyui_url = comfyui_url
                            
    def execute_hooks(self, hook_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute hooks on all pipeline implementations.
        
        Args:
            hook_type: Type of hooks to execute
            context: Context data for hook execution
            
        Returns:
            Combined results from all hooks
        """
        results = {}
        # Execute hooks on all pipelines (they should all have the same hooks)
        for pipeline in self._pipelines.values():
            if hasattr(pipeline, 'execute_hooks'):
                hook_results = pipeline.execute_hooks(hook_type, context)
                results.update(hook_results)
                break  # Only need to execute once, all pipelines share the same hooks
        return results


# Factory function for backward compatibility
def create_pipeline(base_path: str = None) -> AutoTrainPipeline:
    """
    Factory function to create an AutoTrainPipeline instance.
    
    Args:
        base_path: Base path for AutoTrainX project (auto-detected if None)
        
    Returns:
        AutoTrainPipeline instance
    """
    if base_path is None:
        base_path = Config.get_default_base_path()
    return AutoTrainPipeline(base_path)