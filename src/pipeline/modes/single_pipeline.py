"""Single dataset processing pipeline."""

from typing import Dict, List, Optional, Any
from pathlib import Path
from ..base import PipelineInterface, PipelineConfig, PipelineResult, DatasetResult, PipelineStatus
from ..base.pipeline_context import PipelineContext
from ...scripts.dataset_preparation import DatasetPreparator, extract_dataset_name
from ...scripts.preset_manager import get_preset_manager
from ..utils.shared_pipeline_utils import (
    print_existing_datasets_warning,
    get_clean_confirmation,
    print_cleaning_message,
    print_cleaning_complete,
    print_operation_cancelled,
    print_detailed_error,
    should_show_cleaning_prompt,
    print_config_generation_table,
    print_compact_preparation
)
from ..utils.config_generator import ConfigurationGenerator
from ...utils import managed_resource, WorkspaceManager
from ...utils.job_tracker import get_tracker
from ...database import ExecutionStatus, PipelineMode
import uuid
from datetime import datetime
import toml
import os
import textwrap


class SinglePipeline(PipelineInterface):
    """
    Pipeline for processing a single dataset.
    
    This is the traditional mode that processes one dataset at a time
    with full control over each step.
    """
    
    def __init__(self, config: PipelineConfig):
        super().__init__(config)
        # Keep quiet mode to prevent duplicate output
        self.dataset_preparator = DatasetPreparator(config.base_path, quiet_mode=True, path_manager=config.path_manager)
        self.preset_manager = get_preset_manager()
        self.config_generator = ConfigurationGenerator(self.preset_manager, config.base_path, path_manager=config.path_manager)
        
    def execute(self, source_path: str, repeats: int = 30, 
                class_name: str = "person", dataset_name: Optional[str] = None,
                generate_configs: bool = True, preset: Optional[str] = None,
                auto_clean: bool = False, **kwargs) -> PipelineResult:
        """
        Execute single dataset pipeline.
        
        Args:
            source_path: Path to source dataset
            repeats: Number of training repetitions
            class_name: Class name for the object
            dataset_name: Optional custom dataset name
            generate_configs: Whether to generate preset configurations
            preset: Optional specific preset to generate config for (if None, generates for all)
            
        Returns:
            PipelineResult with execution details
        """
        # Create execution context
        context = PipelineContext(pipeline_id=str(uuid.uuid4()))
        start_time = datetime.now()
        
        # Validate inputs
        errors = self.validate_inputs(source_path=source_path, repeats=repeats)
        if errors:
            return self._create_error_result(errors, context)
            
        # Extract dataset name
        if not dataset_name:
            dataset_name = extract_dataset_name(source_path, quiet=self.dataset_preparator.quiet_mode)
        
        # Use job_id from kwargs if provided (from API), otherwise generate new one
        from ...utils.job_id import generate_job_id
        job_id = kwargs.get('job_id', generate_job_id())
        
        # Get tracker instance
        tracker = get_tracker()
        
        # Create execution record
        preset_name = preset if preset else "all"
        tracker.create_execution(
            job_id=job_id,
            pipeline_mode=PipelineMode.SINGLE.value,
            dataset_name=dataset_name,
            preset=preset_name
        )
            
        try:
            # Track if dataset was cleaned
            was_cleaned = self.dataset_preparator.check_existing_dataset(dataset_name)
            
            # Track dataset preparation stage
            with tracker.track_stage(job_id, ExecutionStatus.PREPARING_DATASET):
                # Execute dataset preparation
                prep_result = self._prepare_dataset(
                    source_path, dataset_name, repeats, class_name, auto_clean
                )
            
            configs = []
            if generate_configs and prep_result['success']:
                # Track configuration generation stage
                with tracker.track_stage(job_id, ExecutionStatus.CONFIGURING_PRESET):
                    # Generate configurations
                    configs = self._generate_configurations(dataset_name, preset, job_id)
                
                # Show compact preparation output
                print_compact_preparation(
                    dataset_name=dataset_name,
                    source_path=source_path,
                    repeats=repeats,
                    class_name=class_name,
                    was_cleaned=was_cleaned,
                    valid_pairs=prep_result.get('valid_pairs', 0),
                    configs=configs
                )
                
            # Create dataset result
            dataset_result = DatasetResult(
                dataset_name=dataset_name,
                success=prep_result['success'],
                input_dir=prep_result.get('input_dir'),
                output_dir=prep_result.get('output_dir'),
                prompts_file=prep_result.get('prompts_file'),
                configs=configs,
                error=prep_result.get('error')
            )
            
            # Update context
            if prep_result['success']:
                context.add_processed_dataset(dataset_name)
                if configs:
                    context.generated_configs[dataset_name] = configs
                    
            # Update status based on preparation result
            if not prep_result['success']:
                tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=prep_result.get('error'))
            elif generate_configs and configs:
                # Configuration is complete, mark as ready for training
                tracker.update_status(job_id, ExecutionStatus.READY_FOR_TRAINING)
            
            # Set output path if successful
            if prep_result['success'] and prep_result.get('output_dir'):
                tracker.set_output_path(job_id, str(prep_result['output_dir']))
                    
            # Create final result
            return PipelineResult(
                status=PipelineStatus.SUCCESS if prep_result['success'] else PipelineStatus.FAILED,
                mode='single',
                total_datasets=1,
                successful_datasets=1 if prep_result['success'] else 0,
                failed_datasets=0 if prep_result['success'] else 1,
                results={dataset_name: dataset_result},
                execution_time=(datetime.now() - start_time).total_seconds(),
                context=context,
                # Legacy fields
                repeats=repeats,
                class_name=class_name
            )
            
        except Exception as e:
            context.add_error({
                'dataset': dataset_name,
                'error': str(e),
                'type': 'execution_error'
            })
            # Update tracker with error
            tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=str(e))
            return self._create_error_result([str(e)], context)
            
    def validate_inputs(self, **kwargs) -> List[str]:
        """Validate single pipeline inputs."""
        errors = []
        
        source_path = kwargs.get('source_path')
        if not source_path:
            errors.append("source_path is required")
        elif not Path(source_path).exists():
            errors.append(f"Source path does not exist: {source_path}")
            
        repeats = kwargs.get('repeats', 30)
        if not isinstance(repeats, int) or repeats < 1:
            errors.append("repeats must be a positive integer")
            
        return errors
        
    def get_execution_plan(self, **kwargs) -> Dict[str, Any]:
        """Get execution plan for single dataset."""
        source_path = kwargs.get('source_path', '')
        dataset_name = kwargs.get('dataset_name') or extract_dataset_name(source_path)
        
        return {
            'mode': 'single',
            'steps': [
                {'step': 1, 'action': 'validate_source', 'target': source_path},
                {'step': 2, 'action': 'copy_to_input', 'target': self._get_relative_path('input', dataset_name)},
                {'step': 3, 'action': 'create_output_structure', 'target': self._get_relative_path('output', dataset_name)},
                {'step': 4, 'action': 'generate_prompts', 'target': self._get_relative_path('output', dataset_name, 'sample_prompts.txt')},
                {'step': 5, 'action': 'generate_configs', 'presets': self.preset_manager.get_preset_names()}
            ],
            'estimated_time': 'Less than 1 minute'
        }
        
    def _prepare_dataset(self, source_path: str, dataset_name: str,
                        repeats: int, class_name: str, auto_clean: bool = False) -> Dict[str, Any]:
        """Internal dataset preparation."""
        try:
            # Check if dataset already exists
            if self.dataset_preparator.check_existing_dataset(dataset_name):
                if auto_clean:
                    # Auto-clean enabled, clean without prompting
                    # Only show message if not in quiet mode (batch mode sets quiet mode)
                    if self.config.verbose and not self.dataset_preparator.quiet_mode:
                        print(f"Cleaning existing dataset '{dataset_name}'...")
                    self.dataset_preparator.clean_existing_dataset(dataset_name)
                else:
                    # In single mode with terminal, ask user
                    if should_show_cleaning_prompt(self.config):
                        print_existing_datasets_warning(
                            [dataset_name],
                            self.dataset_preparator.input_path,
                            self.dataset_preparator.output_path,
                            mode="single"
                        )
                        
                        response = get_clean_confirmation(mode="single")
                        if response in ['y', 'yes']:
                            self.dataset_preparator.clean_existing_dataset(dataset_name)
                        else:
                            return {
                                'success': False,
                                'error': f"Dataset '{dataset_name}' already exists and user chose not to clean it"
                            }
                    else:
                        # Non-interactive mode, skip
                        return {
                            'success': False,
                            'error': f"Dataset '{dataset_name}' already exists"
                        }
            
            # Prepare the dataset
            result = self.dataset_preparator.prepare_dataset(
                source_path=source_path,
                dataset_name=dataset_name,
                repeats=repeats,
                class_name=class_name
            )
            return {
                'success': True,
                **result
            }
        except Exception as e:
            # On error, show detailed information
            print_detailed_error(e, dataset_name, source_path, self.config.verbose)
            return {
                'success': False,
                'error': str(e)
            }
            
    def _generate_configurations(self, dataset_name: str, preset_filter: Optional[str] = None, job_id: Optional[str] = None) -> List[str]:
        """Generate preset configurations for dataset.
        
        Args:
            dataset_name: Name of the dataset
            preset_filter: If specified, only generate config for this preset
        """
        configs = []
        try:
            # Ensure presets directory exists
            if self.config.path_manager:
                presets_base_dir = self.config.path_manager.get_workspace_path() / "Presets"
            else:
                presets_base_dir = Path(self.config.base_path) / "workspace" / "Presets"
            presets_base_dir.mkdir(parents=True, exist_ok=True)
            
            # Get presets to generate configs for
            if preset_filter:
                # Only generate for the specified preset
                preset_info = self.preset_manager.get_preset(preset_filter)
                if preset_info:
                    presets = {preset_filter: preset_info}
                else:
                    print(f"Warning: Preset '{preset_filter}' not found")
                    return configs
            else:
                # Generate configs for all available presets
                presets = self.preset_manager.get_presets()
                
            for preset_name, preset_info in presets.items():
                try:
                    # Create preset-specific directory
                    if self.config.path_manager:
                        # In custom mode, configs go to dataset config dir
                        preset_dir = self.config.path_manager.get_config_output_path(dataset_name)
                    else:
                        preset_dir = presets_base_dir / preset_name
                    preset_dir.mkdir(exist_ok=True, parents=True)
                    
                    # Initial config path (will be updated with job_id later)
                    config_path = preset_dir / "temp.toml"
                    
                    # Generate configuration
                    actual_config_path = self._generate_single_preset_config(dataset_name, preset_name, preset_info, config_path, job_id)
                    if actual_config_path:
                        configs.append(str(actual_config_path))
                        # Only show individual config generation in debug mode
                        if os.environ.get('CONFIG_DEBUG', '').lower() == 'true':
                            print(f"✅ Generated config: {actual_config_path.name}")
                    else:
                        # Always show failures
                        if self.config.verbose:
                            print(f"❌ Failed to generate config for {dataset_name}_{preset_name}")
                            
                except Exception as e:
                    if self.config.verbose:
                        print(f"Warning: Failed to generate config for {preset_name}: {e}")
                    
        except Exception as e:
            # Log error but don't fail the entire pipeline
            print(f"Warning: Failed to generate some configs: {e}")
            
        return configs
        
    def _generate_single_preset_config(self, dataset_name: str, preset_name: str, 
                                     preset_info: Any, config_path: Path, job_id: Optional[str] = None) -> Optional[Path]:
        """Generate a single preset configuration file."""
        try:
            import toml
            
            # Use ConfigurationGenerator for consistent config generation
            base_config = self.config_generator.get_base_config(preset_name)
            
            # Resolve model paths
            base_config = self.config_generator.resolve_model_paths(base_config, preset_name)
            
            # Update dataset-specific paths with JobID
            output_dir_base = self.dataset_preparator.output_path / dataset_name
            base_config = self.config_generator.update_dataset_paths(
                base_config, dataset_name, output_dir_base, preset_name=preset_name, job_id=job_id
            )
            
            # Get the job_id from config (if not provided, it was generated)
            if not job_id:
                job_id = base_config.get('job_id')
            
            # Update config path to include job_id
            config_name_with_job = f"{dataset_name}_{preset_name}_{job_id}"
            config_path = config_path.parent / f"{config_name_with_job}.toml"
            
            # Write configuration file with header
            with open(config_path, 'w', encoding='utf-8') as f:
                header = self.config_generator.create_config_header(
                    preset_name, dataset_name, 'single', job_id=job_id
                )
                f.write(header + "\n")
                toml.dump(base_config, f)
                
            return config_path
            
        except Exception as e:
            if self.config.verbose:
                print(f"Error generating config for {dataset_name}_{preset_name}: {e}")
            return None
        
    def _create_error_result(self, errors: List[str], context: PipelineContext) -> PipelineResult:
        """Create error result."""
        return PipelineResult(
            status=PipelineStatus.FAILED,
            mode='single',
            total_datasets=0,
            successful_datasets=0,
            failed_datasets=0,
            context=context,
            error_message="; ".join(errors)
        )
    
    def _get_relative_path(self, path_type: str, dataset_name: str, *additional_parts) -> str:
        """Get relative path for display purposes."""
        if self.config.path_manager and self.config.path_manager.is_custom_mode:
            # In custom mode, show the custom output path
            base = self.config.path_manager.custom_output_path
            if path_type == 'input':
                # Input always stays in workspace
                parts = ['workspace', 'input', dataset_name] + list(additional_parts)
            else:
                # Output goes to custom path
                parts = [dataset_name] + list(additional_parts)
            return str(Path(base, *parts))
        else:
            # Default mode
            parts = ['workspace', path_type, dataset_name] + list(additional_parts)
            return str(Path(*parts))