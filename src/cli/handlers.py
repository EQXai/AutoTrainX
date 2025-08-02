"""
Command handlers for AutoTrainX CLI operations.

This module contains all command handler functions that execute
specific operations based on CLI arguments.
"""

from pathlib import Path
from typing import Dict, List, Any

from src.pipeline.pipeline import AutoTrainPipeline
from src.cli.formatter import ResultFormatter
from src.training.trainer import SDScriptsTrainer
from src.scripts.preset_manager import get_preset_info


class CommandHandlers:
    """Handles execution of different CLI commands."""
    
    def __init__(self, pipeline: AutoTrainPipeline, formatter: ResultFormatter):
        self.pipeline = pipeline
        self.formatter = formatter
    
    def handle_prepare(self, args) -> int:
        """Handle dataset preparation and configuration generation."""
        mode = args.mode or 'single'  # Default to single mode
        
        if mode == 'single':
            result = self._handle_single_mode(args)
            
        elif mode == 'batch':
            result = self._handle_batch_mode(args)
            
        elif mode == 'variations':
            result = self._handle_variations_mode(args)
        
        self.formatter.print_result_summary(result)
        return 0 if result.success else 1
    
    def _handle_single_mode(self, args):
        """Process a single dataset."""
        return self.pipeline.execute(
            mode='single',
            source_path=args.source,
            repeats=args.repeats,
            class_name=args.class_name,
            generate_configs=True
        )
    
    def _handle_batch_mode(self, args):
        """Process multiple datasets in batch."""
        source_dir = Path(args.source)
        batch_datasets = self._scan_for_datasets(source_dir, args)
        
        if not batch_datasets:
            print(f"Error: No valid datasets found in {source_dir}")
            print("   Expected subdirectories containing image files")
            return self._create_error_result("No valid datasets found")
        
        # Dataset list will be shown in the batch processing table
        
        return self.pipeline.execute(
            mode='batch',
            datasets=batch_datasets,
            strategy='parallel' if args.parallel else 'sequential',
            continue_on_error=args.continue_on_error
        )
    
    def _handle_variations_mode(self, args):
        """Create configuration variations for a dataset."""
        dataset_name = Path(args.source).name
        variations = self._parse_variations(args.variations)
        
        return self.pipeline.execute(
            mode='variations',
            dataset_name=dataset_name,
            base_preset=args.preset,
            variations=variations,
            naming_template=args.naming_template
        )
    
    def handle_configure(self, args) -> int:
        """Handle configuration generation command."""
        result = self.pipeline.generate_configs_only(dataset_name=None)
        self.formatter.print_result_summary(result)
        return 0 if result.success else 1
    
    def handle_status(self, args) -> int:
        """Handle status display command."""
        status = self.pipeline.get_pipeline_status()
        self.formatter.print_status(status)
        return 0
    
    def handle_list_presets(self, args) -> int:
        """Handle list presets command."""
        presets = self.pipeline.list_available_presets()
        self.formatter.print_presets(presets)
        return 0
    
    def handle_dataset_info(self, args) -> int:
        """Handle dataset info command."""
        info = self.pipeline.get_dataset_info(args.dataset_info)
        if not info:
            print(f"Error: Dataset '{args.dataset_info}' not found.")
            return 1
        
        self.formatter.print_dataset_info(args.dataset_info, info)
        return 0
    
    def _scan_for_datasets(self, source_dir: Path, args) -> List[Dict[str, Any]]:
        """Scan directory for valid dataset subdirectories."""
        batch_datasets = []
        
        for subdir in source_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                # Check if it contains images (basic dataset validation)
                if self._has_images(subdir):
                    batch_datasets.append({
                        'source_path': str(subdir),
                        'repeats': args.repeats,
                        'class_name': args.class_name
                    })
        
        return batch_datasets
    
    def _has_images(self, directory: Path) -> bool:
        """Check if directory contains image files."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        for ext in image_extensions:
            if list(directory.glob(f'*{ext}')):
                return True
        return False
    
    def _parse_variations(self, variations_args: List[str]) -> Dict[str, List[Any]]:
        """Parse variation arguments into a dictionary."""
        variations = {}
        
        for var_spec in variations_args:
            param, values = var_spec.split('=', 1)
            # Try to parse numeric values
            parsed_values = []
            for value in values.split(','):
                try:
                    # Try float first
                    if '.' in value or 'e' in value.lower():
                        parsed_values.append(float(value))
                    else:
                        parsed_values.append(int(value))
                except ValueError:
                    # Keep as string
                    parsed_values.append(value)
            variations[param] = parsed_values
        
        return variations
    
    def handle_train(self, args) -> int:
        """Handle model training command."""
        mode = args.mode or 'single'
        
        # First, prepare dataset and generate configs (just like --prepare)
        if mode == 'single':
            prepare_result = self._handle_single_mode(args)
            
        elif mode == 'batch':
            prepare_result = self._handle_batch_mode(args)
            
        elif mode == 'variations':
            prepare_result = self._handle_variations_mode(args)
        
        # If preparation failed, stop here
        if not prepare_result.success:
            self.formatter.print_result_summary(prepare_result)
            return 1
        
        # Now proceed with training
        trainer = SDScriptsTrainer(self.pipeline.base_path)
        
        # Get preset info
        preset_name = args.preset if args.preset else self._detect_preset_from_mode(prepare_result, args)
        if not preset_name:
            print("Error: Could not determine preset for training")
            return 1
            
        preset_info = get_preset_info(preset_name)
        if not preset_info:
            print(f"Error: Preset '{preset_name}' not found")
            return 1
        
        # Execute training based on mode
        if mode == 'single':
            return self._train_single(prepare_result, trainer, preset_info)
            
        elif mode == 'batch':
            return self._train_batch(prepare_result, trainer, preset_info)
            
        elif mode == 'variations':
            return self._train_variations(prepare_result, trainer)
    
    def _train_single(self, prepare_result, trainer, preset_info) -> int:
        """Train a single dataset."""
        dataset_name = prepare_result.dataset_name
        toml_path = self.pipeline.base_path / "workspace" / "Presets" / preset_info.name / f"{dataset_name}_{preset_info.name}.toml"
        
        if not toml_path.exists():
            print(f"Error: Configuration file not found: {toml_path}")
            return 1
        
        success = trainer.execute_training(toml_path, preset_info, dataset_name)
        return 0 if success else 1
    
    def _train_batch(self, prepare_result, trainer, preset_info) -> int:
        """Train multiple datasets in batch."""
        total_success = True
        
        for dataset_result in prepare_result.dataset_results:
            if dataset_result['status'] == 'SUCCESS':
                dataset_name = dataset_result['dataset_name']
                toml_path = self.pipeline.base_path / "workspace" / "Presets" / preset_info.name / f"{dataset_name}_{preset_info.name}.toml"
                
                if toml_path.exists():
                    success = trainer.execute_training(toml_path, preset_info, dataset_name)
                    if not success:
                        total_success = False
                        if not prepare_result.continue_on_error:
                            return 1
                else:
                    print(f"Warning: Configuration file not found for {dataset_name}, skipping")
        
        return 0 if total_success else 1
    
    def _train_variations(self, prepare_result, trainer) -> int:
        """Train all variations."""
        total_success = True
        
        for variation_result in prepare_result.variation_results:
            if variation_result['success']:
                config_path = Path(variation_result['config_path'])
                preset_name = variation_result['preset']
                preset_info = get_preset_info(preset_name)
                
                if preset_info and config_path.exists():
                    dataset_name = variation_result['name']
                    success = trainer.execute_training(config_path, preset_info, dataset_name)
                    if not success:
                        total_success = False
        
        return 0 if total_success else 1
    
    def _detect_preset_from_mode(self, prepare_result, args):
        """Detect preset from prepare result for variations mode."""
        if hasattr(prepare_result, 'preset_name'):
            return prepare_result.preset_name
        elif hasattr(args, 'preset') and args.preset:
            return args.preset
        return None
    
    def _create_error_result(self, error_message: str):
        """Create a simple error result object."""
        class ErrorResult:
            def __init__(self, message):
                self.success = False
                self.error_message = message
                self.mode = 'error'
                self.status = type('obj', (object,), {'value': 'FAILED'})
                
        return ErrorResult(error_message)