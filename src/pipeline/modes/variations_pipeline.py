"""Configuration variations pipeline for experimentation."""

from typing import Dict, List, Optional, Any, Tuple
from itertools import product
from pathlib import Path
from ..base import PipelineInterface, PipelineConfig, PipelineResult, DatasetResult, PipelineStatus
from ..base.pipeline_context import PipelineContext
from ...scripts.preset_manager import get_preset_manager
from ..utils.config_generator import ConfigurationGenerator
from ...utils.job_tracker import get_tracker
from ...database import ExecutionStatus
import uuid
from datetime import datetime
import copy
import toml


class VariationsPipeline(PipelineInterface):
    """
    Pipeline for generating configuration variations.
    
    Supports experimentation by creating multiple variations
    of training configurations with different hyperparameters.
    """
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        self.preset_manager = get_preset_manager()
        self.config_generator = ConfigurationGenerator(self.preset_manager, config.base_path, path_manager=config.path_manager)
        
    def execute(self, dataset_name: str,
                base_preset: str,
                variations: Dict[str, List[Any]],
                naming_template: str = "{dataset}_{preset}_{variation}") -> PipelineResult:
        """
        Generate configuration variations for experimentation.
        
        Args:
            dataset_name: Name of the prepared dataset
            base_preset: Base preset to create variations from
            variations: Dictionary of parameter variations
            naming_template: Template for naming variations
            
        Returns:
            PipelineResult with generated configurations
        """
        context = PipelineContext(pipeline_id=str(uuid.uuid4()))
        start_time = datetime.now()
        
        # Validate inputs
        errors = self.validate_inputs(
            dataset_name=dataset_name,
            base_preset=base_preset,
            variations=variations
        )
        if errors:
            return self._create_error_result(errors, context)
        
        # Generate variation ID for grouping all variations in this experiment
        from ...utils.job_id import generate_job_id
        variation_id = generate_job_id()  # Single ID for all variations in this experiment
        parent_experiment_id = f"exp_{variation_id}"
        
        # Get tracker instance
        tracker = get_tracker()
            
        try:
            # Generate all variation combinations
            variation_configs = self._generate_variations(
                dataset_name, base_preset, variations, naming_template, variation_id
            )
            
            # Calculate total combinations for tracking
            total_combinations = len(variation_configs)
            
            # Create configuration files with tracking
            results = {}
            for var_name, var_config in variation_configs.items():
                # Get the job_id from the variation config
                job_id = var_config.get('job_id', generate_job_id())
                
                # Get variation metadata
                metadata = var_config.get('__metadata__', {})
                variation_dict = metadata.get('variations', {})
                variation_index = metadata.get('variation_index', 0)
                
                # Create variation record in database
                tracker.create_variation(
                    job_id=job_id,
                    variation_id=variation_id,  # All variations share the same ID
                    experiment_name=var_name,
                    dataset_name=dataset_name,
                    preset=base_preset,
                    total_combinations=total_combinations,
                    varied_parameters=variations,
                    parameter_values=variation_dict,
                    parent_experiment_id=parent_experiment_id
                )
                
                # Track configuration stage
                with tracker.track_stage(job_id, ExecutionStatus.CONFIGURING_PRESET):
                    result = self._create_variation_config(
                        dataset_name, var_name, var_config, variation_id
                    )
                
                # Update status based on result
                if result.success:
                    # Update to READY_FOR_TRAINING - training will update it later
                    tracker.update_status(job_id, ExecutionStatus.READY_FOR_TRAINING)
                    if result.configs and len(result.configs) > 0:
                        # Extract output path from config path
                        if self.config.path_manager:
                            output_path = str(self.config.path_manager.get_variation_output_path(f"exp_{variation_id}", var_name))
                        else:
                            output_path = str(Path(self.config.base_path) / "workspace" / "variations" / f"exp_{variation_id}" / var_name)
                        tracker.set_output_path(job_id, output_path)
                else:
                    tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=result.error)
                
                results[var_name] = result
                
            # Create experiment.json with metadata
            if self.config.path_manager:
                experiment_base = self.config.path_manager.get_variations_base_path() / f"exp_{variation_id}"
            else:
                experiment_base = Path(self.config.base_path) / "workspace" / "variations" / f"exp_{variation_id}"
            experiment_base.mkdir(parents=True, exist_ok=True)
            
            experiment_metadata = {
                "variation_id": variation_id,
                "dataset": dataset_name,
                "preset": base_preset,
                "created": datetime.now().isoformat(),
                "parameters_varied": variations,
                "total_variations": len(variation_configs),
                "variations": list(variation_configs.keys()),
                "status": "completed"
            }
            
            import json
            with open(experiment_base / "experiment.json", 'w') as f:
                json.dump(experiment_metadata, f, indent=2)
            
            # Aggregate results
            total = len(variation_configs)
            successful = sum(1 for r in results.values() if r.success)
            
            return PipelineResult(
                status=PipelineStatus.SUCCESS if successful == total else PipelineStatus.PARTIAL_SUCCESS,
                mode='variations',
                total_datasets=total,
                successful_datasets=successful,
                failed_datasets=total - successful,
                results=results,
                execution_time=(datetime.now() - start_time).total_seconds(),
                context=context
            )
            
        except Exception as e:
            context.add_error({
                'error': str(e),
                'type': 'variation_generation_error'
            })
            return self._create_error_result([str(e)], context)
            
    def validate_inputs(self, **kwargs) -> List[str]:
        """Validate variations pipeline inputs."""
        errors = []
        
        dataset_name = kwargs.get('dataset_name')
        if not dataset_name:
            errors.append("dataset_name is required")
            
        base_preset = kwargs.get('base_preset')
        if not base_preset:
            errors.append("base_preset is required")
        elif not self.preset_manager.is_valid_preset(base_preset):
            errors.append(f"Invalid preset: {base_preset}")
            
        variations = kwargs.get('variations', {})
        if not variations:
            errors.append("At least one variation parameter must be provided")
            
        return errors
        
    def get_execution_plan(self, **kwargs) -> Dict[str, Any]:
        """Get execution plan for variations."""
        variations = kwargs.get('variations', {})
        
        # Calculate total combinations
        total_combinations = 1
        for values in variations.values():
            total_combinations *= len(values)
            
        return {
            'mode': 'variations',
            'base_preset': kwargs.get('base_preset'),
            'variation_parameters': list(variations.keys()),
            'total_combinations': total_combinations,
            'examples': self._generate_example_names(kwargs)[:5]
        }
        
    def _generate_variations(self, dataset_name: str, base_preset: str,
                           variations: Dict[str, List[Any]],
                           naming_template: str,
                           variation_id: str) -> Dict[str, Dict[str, Any]]:
        """Generate all variation combinations."""
        # Validate dataset exists before generating variations
        # Note: Prepared datasets are always in workspace/input, regardless of custom output path
        if self.config.path_manager:
            # For input validation, always check workspace/input
            input_base = self.config.path_manager.get_input_base_path()
            # But for output, use the custom path
            original_dataset_dir = self.config.path_manager.get_output_path(dataset_name)
        else:
            input_base = Path(self.config.base_path) / "workspace" / "input"
            original_dataset_dir = Path(self.config.base_path) / "workspace" / "output" / dataset_name
            
        # Validate in input directory first (where prepared datasets are)
        if not self.config_generator.validate_dataset_exists(dataset_name, input_base):
            # If not in input, check output (for backwards compatibility)
            output_base = self.config.path_manager.get_output_base_path() if self.config.path_manager else Path(self.config.base_path) / "workspace" / "output"
            if not self.config_generator.validate_dataset_exists(dataset_name, output_base):
                raise ValueError(f"Dataset not found: {dataset_name}. Please prepare the dataset first.")
        
        # Base path for variations with experiment ID
        if self.config.path_manager:
            variations_base = self.config.path_manager.get_variations_base_path() / f"exp_{variation_id}"
        else:
            variations_base = Path(self.config.base_path) / "workspace" / "variations" / f"exp_{variation_id}"
        
        # Get base configuration using ConfigurationGenerator
        base_config = self.config_generator.get_base_config(base_preset)
        
        # Generate all combinations
        param_names = list(variations.keys())
        param_values = [variations[param] for param in param_names]
        
        variation_configs = {}
        
        for i, combination in enumerate(product(*param_values)):
            # Create variation config
            var_config = copy.deepcopy(base_config)
            
            # Generate variation name
            var_name = naming_template.format(
                dataset=dataset_name,
                preset=base_preset,
                variation=f"v{i+1}"
            )
            
            # Create independent output directory for each variation
            variation_output_dir = variations_base / var_name
            
            # Apply variation parameters first
            variation_dict = dict(zip(param_names, combination))
            var_config = self.config_generator.apply_variations(var_config, variation_dict)
            
            # Resolve model paths using preset manager
            var_config = self.config_generator.resolve_model_paths(var_config, base_preset)
            
            # Update dataset-specific paths with independent variation directory
            # For variations, we need to point to the output directory where processed images are
            if self.config.path_manager:
                output_dataset_dir = self.config.path_manager.get_output_path(dataset_name)
            else:
                output_dataset_dir = Path(self.config.base_path) / "workspace" / "output" / dataset_name
                
            var_config = self.config_generator.update_dataset_paths(
                var_config, dataset_name, variation_output_dir, 
                variation_name=var_name, original_dataset_dir=output_dataset_dir
            )
            
            # Add metadata
            var_config['__metadata__'] = {
                'base_preset': base_preset,
                'dataset': dataset_name,
                'variations': variation_dict,
                'variation_index': i + 1,
                'variation_id': variation_id  # Add variation_id to metadata
            }
            
            variation_configs[var_name] = var_config
            
        return variation_configs
        
    def _create_variation_config(self, dataset_name: str, 
                               variation_name: str,
                               config: Dict[str, Any],
                               variation_id: str = None) -> DatasetResult:
        """Create a single variation configuration file."""
        try:
            # Remove metadata before saving
            config_to_save = copy.deepcopy(config)
            metadata = config_to_save.pop('__metadata__', {})
            
            # Create output directory structure for this variation
            if variation_id:
                if self.config.path_manager:
                    variations_base = self.config.path_manager.get_variations_base_path() / f"exp_{variation_id}"
                else:
                    variations_base = Path(self.config.base_path) / "workspace" / "variations" / f"exp_{variation_id}"
            else:
                if self.config.path_manager:
                    variations_base = self.config.path_manager.get_variations_base_path()
                else:
                    variations_base = Path(self.config.base_path) / "workspace" / "variations"
            variation_output_dir = variations_base / variation_name
            
            # Create necessary subdirectories for training output
            (variation_output_dir / "model").mkdir(parents=True, exist_ok=True)
            (variation_output_dir / "log").mkdir(parents=True, exist_ok=True)
            
            # Ensure presets directory exists with preset subdirectory
            # This creates a structure like: Presets/Variations/FluxLORA/
            base_preset = metadata.get('base_preset', 'unknown')
            presets_dir = Path(self.config.base_path) / "workspace" / "Presets" / "Variations" / base_preset
            presets_dir.mkdir(parents=True, exist_ok=True)
            
            # Get job_id from config
            job_id = config_to_save.get('job_id', '')
            
            # Save configuration with job_id in filename
            config_name_with_job = f"{variation_name}_{job_id}" if job_id else variation_name
            config_path = presets_dir / f"{config_name_with_job}.toml"
            with open(config_path, 'w') as f:
                # Use ConfigurationGenerator for consistent header
                header = self.config_generator.create_config_header(
                    metadata.get('base_preset', 'unknown'),
                    metadata.get('dataset', 'unknown'),
                    'variations',
                    metadata.get('variations', {}),
                    job_id=job_id
                )
                f.write(header + "\n")
                toml.dump(config_to_save, f)
            
            return DatasetResult(
                dataset_name=variation_name,
                success=True,
                configs=[str(config_path)],
                metadata=metadata
            )
        except Exception as e:
            return DatasetResult(
                dataset_name=variation_name,
                success=False,
                error=str(e)
            )
            
    def _generate_example_names(self, kwargs: Dict[str, Any]) -> List[str]:
        """Generate example variation names."""
        template = kwargs.get('naming_template', "{dataset}_{preset}_{variation}")
        examples = []
        
        for i in range(5):
            example = template.format(
                dataset=kwargs.get('dataset_name', 'dataset'),
                preset=kwargs.get('base_preset', 'preset'),
                variation=f"v{i+1}"
            )
            examples.append(example)
            
        return examples
        
    def _create_error_result(self, errors: List[str], context: PipelineContext) -> PipelineResult:
        """Create error result."""
        return PipelineResult(
            status=PipelineStatus.FAILED,
            mode='variations',
            total_datasets=0,
            successful_datasets=0,
            failed_datasets=0,
            context=context,
            error_message="; ".join(errors)
        )