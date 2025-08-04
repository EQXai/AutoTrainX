"""
Simplified command handlers using the unified argument system.
"""

from pathlib import Path
from typing import Dict, List, Any

from src.pipeline.pipeline import AutoTrainPipeline
from src.cli.formatter import ResultFormatter
from src.cli.unified_args import UnifiedArgs, Operation, Mode
from src.training import get_trainer
from src.scripts.preset_manager import get_preset_info
from src.utils.path_manager import PathManager, PathProfile
from src.config import Config


class UnifiedCommandHandler:
    """Handles command execution with unified arguments."""
    
    def __init__(self, pipeline: AutoTrainPipeline, formatter: ResultFormatter):
        self.pipeline = pipeline
        self.formatter = formatter
    
    def execute(self, args: UnifiedArgs) -> int:
        """Execute command based on unified arguments."""
        # Route to appropriate handler
        handlers = {
            Operation.TRAIN: self._handle_train,
            Operation.PREPARE: self._handle_prepare,
            Operation.CONFIGURE: self._handle_configure,
            Operation.STATUS: self._handle_status,
            Operation.LIST_PRESETS: self._handle_list_presets,
            Operation.DATASET_INFO: self._handle_dataset_info,
            Operation.SET_CONFIG: self._handle_set_config,
            Operation.VALIDATE_PREVIEW: self._handle_validate_preview,
            Operation.DIAGNOSE_COMFYUI: self._handle_diagnose_comfyui,
            Operation.CREATE_PRESET: self._handle_create_preset,
            Operation.DELETE_PRESET: self._handle_delete_preset,
            Operation.SHOW_PRESET: self._handle_show_preset,
            Operation.JOB_HISTORY: self._handle_job_history,
            Operation.JOB_INFO: self._handle_job_info,
            Operation.DB_STATS: self._handle_db_stats,
            Operation.CLEAR_DB: self._handle_clear_db,
            Operation.CLEANUP_STALE: self._handle_cleanup_stale,
            Operation.LIST_PROFILES: self._handle_list_profiles,
            Operation.SAVE_PROFILE: self._handle_save_profile,
            Operation.DELETE_PROFILE: self._handle_delete_profile,
            Operation.SET_PROFILE: self._handle_set_profile,
        }
        
        handler = handlers.get(args.operation)
        if not handler:
            print(f"Error: Unknown operation {args.operation}")
            return 1
        
        return handler(args)
    
    def _handle_train(self, args: UnifiedArgs) -> int:
        """Handle training operation (includes preparation)."""
        # First prepare the dataset
        prepare_result = self._prepare_dataset(args)
        
        if not prepare_result.success:
            self.formatter.print_result_summary(prepare_result)
            return 1
        
        # Then proceed with training
        # Get trainer with progress monitoring (configurable)
        show_progress = not args.raw_output if hasattr(args, 'raw_output') else None
        trainer = get_trainer(self.pipeline.base_path, show_progress)
        
        # Execute training based on mode
        if args.mode == Mode.SINGLE:
            return self._train_single(args, prepare_result, trainer)
        elif args.mode == Mode.BATCH:
            return self._train_batch(args, prepare_result, trainer)
        elif args.mode == Mode.VARIATIONS:
            return self._train_variations(args, prepare_result, trainer)
    
    def _handle_prepare(self, args: UnifiedArgs) -> int:
        """Handle dataset preparation only."""
        result = self._prepare_dataset(args)
        self.formatter.print_result_summary(result)
        return 0 if result.success else 1
    
    def _prepare_dataset(self, args: UnifiedArgs):
        """Prepare dataset based on mode."""
        if args.mode == Mode.SINGLE:
            return self.pipeline.execute(
                mode='single',
                source_path=args.source,
                repeats=args.repeats,
                class_name=args.class_name,
                generate_configs=True,
                preset=args.preset
            )
        
        elif args.mode == Mode.BATCH:
            # Scan for datasets in batch mode
            source_dir = Path(args.source)
            batch_datasets = self._scan_for_datasets(source_dir, args)
            
            if not batch_datasets:
                return self._create_error_result(f"No valid datasets found in {source_dir}")
            
            # Dataset list will be shown in the batch processing table
            
            return self.pipeline.execute(
                mode='batch',
                datasets=batch_datasets,
                strategy='parallel' if args.parallel else 'sequential',
                continue_on_error=args.continue_on_error,
                preset=args.preset
            )
        
        elif args.mode == Mode.VARIATIONS:
            # First check if source is a path to prepare or just a dataset name
            source_path = Path(args.source)
            
            if source_path.exists() and source_path.is_dir():
                # Source is a directory, we need to prepare it first
                print(f"📁 Preparing dataset from: {args.source}")
                prepare_result = self.pipeline.execute(
                    mode='single',
                    source_path=str(source_path),
                    repeats=args.repeats,
                    class_name=args.class_name,
                    generate_configs=False,  # Don't generate configs, variations will do that
                    auto_clean=args.auto_clean
                )
                
                if not prepare_result.success:
                    return self._create_error_result(f"Failed to prepare dataset: {prepare_result.error_message}")
                    
                dataset_name = prepare_result.dataset_name
            else:
                # Source is just a dataset name
                dataset_name = source_path.name
                
                # Check if dataset exists
                dataset_info = self.pipeline.get_dataset_info(dataset_name)
                if not dataset_info:
                    return self._create_error_result(f"Dataset '{dataset_name}' not found. Please prepare it first.")
            
            # Now create variations
            return self.pipeline.execute(
                mode='variations',
                dataset_name=dataset_name,
                base_preset=args.preset,
                variations=args.variations,
                naming_template=args.naming_template
            )
    
    def _handle_configure(self, args: UnifiedArgs) -> int:
        """Handle configuration generation."""
        result = self.pipeline.generate_configs_only(dataset_name=None)
        self.formatter.print_result_summary(result)
        return 0 if result.success else 1
    
    def _handle_status(self, args: UnifiedArgs) -> int:
        """Handle status display with automatic stale process cleanup."""
        from src.database import DatabaseManager
        from src.utils.quiet_mode import quiet_database_init
        
        # Perform automatic cleanup of stale processes with quiet DB init
        with quiet_database_init():
            db = DatabaseManager()
        try:
            cleaned_count = db.cleanup_stale_processes()
            if cleaned_count > 0:
                print(f"\n\033[93m⚠️  Auto-cleaned {cleaned_count} stale process(es) before showing status\033[0m")
        except Exception as e:
            print(f"\n\033[91mWarning: Could not check for stale processes: {e}\033[0m")
        
        # Show normal status
        status = self.pipeline.get_pipeline_status()
        self.formatter.print_status(status)
        return 0
    
    def _handle_list_presets(self, args: UnifiedArgs) -> int:
        """Handle preset listing."""
        presets = self.pipeline.list_available_presets()
        self.formatter.print_presets(presets)
        return 0
    
    def _handle_dataset_info(self, args: UnifiedArgs) -> int:
        """Handle dataset info display."""
        info = self.pipeline.get_dataset_info(args.dataset_name)
        if not info:
            print(f"Error: Dataset '{args.dataset_name}' not found.")
            return 1
        
        self.formatter.print_dataset_info(args.dataset_name, info)
        return 0
    
    def _handle_create_preset(self, args: UnifiedArgs) -> int:
        """Handle custom preset creation."""
        from src.scripts.preset_manager import get_preset_manager
        
        preset_manager = get_preset_manager()
        success = preset_manager.create_custom_preset(
            name=args.preset_name,
            base_preset_name=args.base_preset,
            description=args.preset_description,
            overrides=args.preset_overrides
        )
        
        if success:
            if args.json:
                import json
                print(json.dumps({
                    "status": "success",
                    "message": f"Created custom preset '{args.preset_name}' based on '{args.base_preset}'"
                }))
            else:
                print(f"\033[92m✓ Created custom preset '{args.preset_name}' based on '{args.base_preset}'\033[0m")
        else:
            if args.json:
                import json
                print(json.dumps({
                    "status": "error",
                    "message": f"Failed to create preset '{args.preset_name}'"
                }))
            return 1
        
        return 0
    
    def _handle_delete_preset(self, args: UnifiedArgs) -> int:
        """Handle custom preset deletion."""
        from src.scripts.preset_manager import get_preset_manager
        
        preset_manager = get_preset_manager()
        success = preset_manager.delete_custom_preset(args.preset_name)
        
        if success:
            if args.json:
                import json
                print(json.dumps({
                    "status": "success",
                    "message": f"Deleted custom preset '{args.preset_name}'"
                }))
            else:
                print(f"\033[92m✓ Deleted custom preset '{args.preset_name}'\033[0m")
        else:
            if args.json:
                import json
                print(json.dumps({
                    "status": "error",
                    "message": f"Failed to delete preset '{args.preset_name}'"
                }))
            return 1
        
        return 0
    
    def _handle_show_preset(self, args: UnifiedArgs) -> int:
        """Handle preset configuration display."""
        from src.scripts.preset_manager import get_preset_manager
        import toml
        
        preset_manager = get_preset_manager()
        preset_info = preset_manager.get_preset(args.preset_name)
        
        if not preset_info:
            if args.json:
                import json
                print(json.dumps({
                    "status": "error",
                    "message": f"Preset '{args.preset_name}' not found"
                }))
            else:
                print(f"Error: Preset '{args.preset_name}' not found")
            return 1
        
        if args.json:
            import json
            output = {
                "name": preset_info.name,
                "description": preset_info.description,
                "type": preset_info.preset_type,
                "is_custom": preset_info.is_custom,
                "base_preset": preset_info.base_preset,
                "model_type": preset_info.model_type,
                "is_lora": preset_info.is_lora,
                "training_script": preset_info.training_script,
                "config": preset_info.defaults
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n\033[96m=== Preset: {preset_info.name} ===\033[0m")
            print(f"Description: {preset_info.description}")
            print(f"Type: {preset_info.preset_type}")
            if preset_info.is_custom:
                print(f"Base preset: {preset_info.base_preset}")
            print(f"Model type: {preset_info.model_type}")
            print(f"Training type: {'LoRA' if preset_info.is_lora else 'Full'}")
            print(f"Training script: {preset_info.training_script}")
            print(f"\n\033[94mConfiguration:\033[0m")
            print(toml.dumps(preset_info.defaults))
        
        return 0
    
    def _handle_set_config(self, args: UnifiedArgs) -> int:
        """Handle configuration setting (like ComfyUI path)."""
        # For now, this is handled in main.py before pipeline creation
        # Just show a success message
        if not args.json:
            print("✓ Configuration updated successfully")
        else:
            import json
            print(json.dumps({"success": True, "message": "Configuration updated"}, indent=2))
        return 0
    
    def _handle_validate_preview(self, args: UnifiedArgs) -> int:
        """Handle preview system validation."""
        try:
            from src.image_preview import PreviewSystemValidator
            PreviewSystemValidator.print_validation_report()
            return 0
        except ImportError:
            print("Error: Preview system not available (missing dependencies)")
            return 1
    
    def _handle_diagnose_comfyui(self, args: UnifiedArgs) -> int:
        """Handle ComfyUI diagnosis."""
        try:
            from src.config import Config
            from src.image_preview.utils import ComfyUIManager
            
            comfyui_path = Config.get_comfyui_path()
            
            if not comfyui_path:
                print("❌ ComfyUI path not configured.")
                print("Use: python main.py --comfyui-path /path/to/ComfyUI")
                return 1
            
            print(f"\n=== ComfyUI Diagnosis ===")
            print(f"ComfyUI Path: {comfyui_path}\n")
            
            diagnosis = ComfyUIManager.diagnose_comfyui_environment(comfyui_path)
            
            # Print diagnosis results
            status_icon = lambda x: "✅" if x else "❌"
            
            print("Environment Checks:")
            print(f"  {status_icon(diagnosis['comfyui_path_exists'])} ComfyUI directory exists")
            print(f"  {status_icon(diagnosis['main_py_exists'])} main.py file found")
            print(f"  {status_icon(diagnosis['requirements_exist'])} Requirements file found")
            print(f"  {status_icon(diagnosis['venv_detected'])} Virtual environment detected")
            print(f"  {status_icon(diagnosis['gpu_available'])} GPU available")
            print(f"  {status_icon(diagnosis['port_available'])} Port 8188 available")
            
            if diagnosis['python_executable']:
                print(f"\nPython: {diagnosis['python_executable']}")
            
            if diagnosis['errors']:
                print(f"\n⚠️  Issues found:")
                for error in diagnosis['errors']:
                    print(f"  - {error}")
            
            # Test connection if ComfyUI might be running
            print(f"\n🔍 Testing ComfyUI connection...")
            if ComfyUIManager.is_comfyui_running("http://127.0.0.1:8188"):
                print("✅ ComfyUI is running and accessible!")
            else:
                print("❌ ComfyUI is not responding")
                print("   Try starting ComfyUI manually:")
                print(f"   cd {comfyui_path}")
                print(f"   python main.py --listen 127.0.0.1 --port 8188")
            
            print("\n" + "="*30 + "\n")
            return 0
            
        except ImportError:
            print("Error: ComfyUI diagnosis not available (missing dependencies)")
            return 1
    
    def _train_single(self, args: UnifiedArgs, prepare_result, trainer) -> int:
        """Train a single dataset."""
        dataset_name = prepare_result.dataset_name
        preset_info = get_preset_info(args.preset)
        
        if not preset_info:
            print(f"Error: Preset '{args.preset}' not found")
            return 1
        
        # Get the actual config path from the pipeline result
        if hasattr(prepare_result, 'results') and dataset_name in prepare_result.results:
            dataset_result = prepare_result.results[dataset_name]
            if dataset_result.configs and len(dataset_result.configs) > 0:
                # Find the config for this preset
                config_path = None
                for config in dataset_result.configs:
                    if preset_info.name in config:
                        config_path = Path(config)
                        break
                
                if config_path and config_path.exists():
                    toml_path = config_path
                else:
                    print(f"Error: Configuration file not found for {dataset_name} with preset {preset_info.name}")
                    return 1
            else:
                print(f"Error: No configuration files generated for {dataset_name}")
                return 1
        else:
            # Fallback to old behavior (shouldn't happen with new code)
            toml_path = self.pipeline.base_path / "workspace" / "Presets" / preset_info.name / f"{dataset_name}_{preset_info.name}.toml"
            
            if not toml_path.exists():
                print(f"Error: Configuration file not found: {toml_path}")
                return 1
        
        # Extract job_id from TOML config
        job_id = None
        try:
            import toml
            with open(toml_path, 'r') as f:
                config = toml.load(f)
                job_id = config.get('job_id')
        except Exception:
            pass
        
        success = trainer.execute_training(toml_path, preset_info, dataset_name, job_id, mode="single")
        
        # Execute post-training hooks if training was successful
        if success and hasattr(self.pipeline, 'execute_hooks'):
            # Import tracker dependencies
            from src.utils.job_tracker import get_tracker
            from src.database import ExecutionStatus
            tracker = get_tracker() if job_id else None
            
            # Update status to GENERATING_PREVIEW if preview is requested
            if job_id and args.preview and args.preview > 0:
                tracker.update_status(job_id, ExecutionStatus.GENERATING_PREVIEW)
            
            hook_context = {
                'success': True,  # FileMoveHook checks for this field
                'training_success': True,  # Keep for backward compatibility
                'dataset_name': dataset_name,
                'preset': args.preset,
                'model_type': args.preset,  # For backward compatibility
                'preview_count': args.preview or 0,  # Pass preview count from args
                'job_id': job_id,
                'mode': 'single',
                'config_path': str(toml_path),
                'preview_enabled': bool(args.preview and args.preview > 0)
            }
            
            try:
                hook_results = self.pipeline.execute_hooks('post_training', hook_context)
                
                # Display file move results to user
                self._display_hook_results(hook_results, args.json)
                
                # Update to DONE after successful preview (or if no preview)
                if job_id and tracker:
                    tracker.update_status(job_id, ExecutionStatus.DONE)
                    # Update output path with exact model file
                    self._update_model_path(job_id, dataset_name, preset_info.name)
                    
            except Exception as e:
                # If preview generation fails, still mark as done (training succeeded)
                if job_id and tracker:
                    tracker.update_status(job_id, ExecutionStatus.DONE)
                import logging
                logging.error(f"Preview generation failed: {e}")
        else:
            # Training failed, status already updated by trainer
            pass
        
        return 0 if success else 1
    
    def _train_batch(self, args: UnifiedArgs, prepare_result, trainer) -> int:
        """Train multiple datasets in batch."""
        preset_info = get_preset_info(args.preset)
        if not preset_info:
            print(f"Error: Preset '{args.preset}' not found")
            return 1
        
        total_success = True
        
        # Iterate through results dictionary
        for dataset_name, dataset_result in prepare_result.results.items():
            if dataset_result.success:
                # Get the actual config path from dataset result
                config_path = None
                if dataset_result.configs and len(dataset_result.configs) > 0:
                    for config in dataset_result.configs:
                        if preset_info.name in config:
                            config_path = Path(config)
                            break
                
                if config_path and config_path.exists():
                    toml_path = config_path
                else:
                    # Fallback to old behavior
                    toml_path = self.pipeline.base_path / "workspace" / "Presets" / preset_info.name / f"{dataset_name}_{preset_info.name}.toml"
                
                if toml_path.exists():
                    # Extract job_id from TOML config
                    job_id = None
                    try:
                        import toml
                        with open(toml_path, 'r') as f:
                            config = toml.load(f)
                            job_id = config.get('job_id')
                    except Exception:
                        pass
                    
                    # Get current and total for batch mode
                    current_idx = list(prepare_result.results.keys()).index(dataset_name) + 1
                    total_datasets = len(prepare_result.results)
                    
                    success = trainer.execute_training(toml_path, preset_info, dataset_name, job_id, 
                                                     mode="batch", current=current_idx, total=total_datasets)
                    
                    # Execute post-training hooks if training was successful
                    if success and hasattr(self.pipeline, 'execute_hooks'):
                        # Update status to GENERATING_PREVIEW if preview is requested
                        if job_id and args.preview and args.preview > 0:
                            from src.utils.job_tracker import get_tracker
                            from src.database import ExecutionStatus
                            tracker = get_tracker()
                            tracker.update_status(job_id, ExecutionStatus.GENERATING_PREVIEW)
                        
                        hook_context = {
                            'success': True,  # FileMoveHook checks for this field
                            'training_success': True,  # Keep for backward compatibility
                            'dataset_name': dataset_name,
                            'preset': args.preset,
                            'model_type': args.preset,
                            'preview_count': args.preview or 0,
                            'job_id': job_id,
                            'mode': 'batch',
                            'config_path': str(toml_path),
                            'preview_enabled': bool(args.preview and args.preview > 0)
                        }
                        
                        try:
                            hook_results = self.pipeline.execute_hooks('post_training', hook_context)
                            
                            # Display file move results to user (compact for batch mode)
                            self._display_hook_results(hook_results, args.json, compact=True)
                            
                            # Update to DONE after successful preview (or if no preview)
                            if job_id:
                                tracker.update_status(job_id, ExecutionStatus.DONE)
                                # Update output path with exact model file
                                self._update_model_path(job_id, dataset_name, preset_info.name)
                                
                        except Exception as e:
                            # If preview generation fails, still mark as done (training succeeded)
                            if job_id:
                                tracker.update_status(job_id, ExecutionStatus.DONE)
                            import logging
                            logging.error(f"Preview generation failed for {dataset_name}: {e}")
                    else:
                        # Training failed, status already updated by trainer
                        pass
                    
                    if not success:
                        total_success = False
                        if not args.continue_on_error:
                            return 1
                else:
                    print(f"Warning: Configuration file not found for {dataset_name}, skipping")
        
        return 0 if total_success else 1
    
    def _train_variations(self, args: UnifiedArgs, prepare_result, trainer) -> int:
        """Train all variations."""
        total_success = True
        
        # Iterate through results dictionary for variations
        for variation_name, variation_result in prepare_result.results.items():
            if variation_result.success:
                # Get the first config path from the configs list
                if variation_result.configs:
                    config_path = Path(variation_result.configs[0])
                    # Extract preset from metadata or use args.preset
                    preset_name = variation_result.metadata.get('base_preset', args.preset)
                    preset_info = get_preset_info(preset_name)
                    
                    if preset_info and config_path.exists():
                        # Extract job_id from TOML config
                        job_id = None
                        try:
                            import toml
                            with open(config_path, 'r') as f:
                                config = toml.load(f)
                                job_id = config.get('job_id')
                        except Exception:
                            pass
                        
                        # Get current and total for variations mode
                        current_idx = list(prepare_result.results.keys()).index(variation_name) + 1
                        total_variations = len(prepare_result.results)
                        
                        # Extract experiment name and variation parameters from metadata
                        experiment_name = variation_result.metadata.get('experiment_name', None)
                        variation_params = variation_result.metadata.get('variation_params', None)
                        
                        success = trainer.execute_training(config_path, preset_info, variation_name, job_id,
                                                         mode="variations", current=current_idx, total=total_variations,
                                                         experiment_name=experiment_name, variation_params=variation_params)
                        
                        # Execute post-training hooks if training was successful
                        if success and hasattr(self.pipeline, 'execute_hooks'):
                            # Update status to GENERATING_PREVIEW if preview is requested
                            if job_id and args.preview and args.preview > 0:
                                from src.utils.job_tracker import get_tracker
                                from src.database import ExecutionStatus
                                tracker = get_tracker()
                                tracker.update_status(job_id, ExecutionStatus.GENERATING_PREVIEW)
                            
                            # Extract variation_id from metadata
                            variation_id = variation_result.metadata.get('variation_id', None)
                            
                            hook_context = {
                                'success': True,  # FileMoveHook checks for this field
                                'training_success': True,  # Keep for backward compatibility
                                'dataset_name': variation_name,
                                'preset': preset_name,
                                'model_type': preset_name,
                                'preview_count': args.preview or 0,
                                'variation_id': variation_id,  # Add variation_id to context
                                'job_id': job_id,
                                'mode': 'variations',
                                'experiment_name': variation_name,
                                'config_path': str(config_path),
                                'preview_enabled': bool(args.preview and args.preview > 0)
                            }
                            
                            try:
                                hook_results = self.pipeline.execute_hooks('post_training', hook_context)
                                
                                # Display file move results to user (compact for variations mode)
                                self._display_hook_results(hook_results, args.json, compact=True)
                                
                                # Update to DONE after successful preview (or if no preview)
                                if job_id:
                                    tracker.update_status(job_id, ExecutionStatus.DONE)
                                    # Update output path with exact model file for variations
                                    self._update_variation_model_path(job_id, variation_name)
                                    
                            except Exception as e:
                                # If preview generation fails, still mark as done (training succeeded)
                                if job_id:
                                    tracker.update_status(job_id, ExecutionStatus.DONE)
                                import logging
                                logging.error(f"Preview generation failed for {variation_name}: {e}")
                        else:
                            # Training failed, status already updated by trainer
                            pass
                        
                        if not success:
                            total_success = False
        
        return 0 if total_success else 1
    
    def _scan_for_datasets(self, source_dir: Path, args: UnifiedArgs) -> List[Dict[str, Any]]:
        """Scan directory for valid dataset subdirectories."""
        batch_datasets = []
        
        for subdir in source_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                # Check if it contains images
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
    
    def _create_error_result(self, error_message: str):
        """Create an error result object."""
        class ErrorResult:
            def __init__(self, message):
                self.success = False
                self.error_message = message
                self.mode = 'error'
                self.status = type('obj', (object,), {'value': 'FAILED'})
        
        return ErrorResult(error_message)
    
    def _handle_job_history(self, args: UnifiedArgs) -> int:
        """Handle job history display."""
        from src.utils.job_tracker import get_tracker
        from src.database import ExecutionStatus
        from datetime import datetime
        import json
        
        tracker = get_tracker()
        
        # Convert filter_status string to enum if provided
        status_filter = None
        if args.filter_status:
            try:
                status_filter = ExecutionStatus(args.filter_status)
            except ValueError:
                print(f"Invalid status: {args.filter_status}")
                return 1
        
        # Get recent jobs
        jobs = tracker.get_recent_jobs(limit=args.limit)
        
        # Apply filters
        if args.filter_dataset:
            jobs = [j for j in jobs if j.get('dataset_name', '').lower() == args.filter_dataset.lower()]
        
        if status_filter:
            jobs = [j for j in jobs if j.get('status') == status_filter.value]
        
        if args.json:
            print(json.dumps(jobs, indent=2))
        else:
            # Format as table
            print("\n\033[1mJob Execution History\033[0m\n")
            
            if not jobs:
                print("No jobs found matching the criteria.")
                return 0
            
            # Print header
            print(f"{'JobID':<10} {'Status':<20} {'Mode':<12} {'Dataset':<25} {'Preset':<15} {'Duration':<10} {'Created':<20}")
            print("-" * 117)
            
            # Print jobs
            for job in jobs:
                job_id = job.get('job_id', 'N/A')
                status = job.get('status', 'unknown')
                job_type = job.get('type', 'unknown')
                dataset = job.get('dataset_name', 'N/A')[:24]
                preset = job.get('preset', 'N/A')[:14]
                
                # Format duration - handle both formatted strings and numeric values
                duration = job.get('duration_seconds', 0)
                if duration:
                    if isinstance(duration, str):
                        # Already formatted
                        duration_str = duration
                    else:
                        # Format numeric value
                        duration_str = f"{int(duration)}s"
                else:
                    duration_str = "N/A"
                
                # Format created time
                created = job.get('created_at', '')
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        created_str = created[:19]
                else:
                    created_str = "N/A"
                
                # Color status
                status_colors = {
                    'done': '\033[92m',      # Green
                    'failed': '\033[91m',    # Red
                    'training': '\033[93m',  # Yellow
                    'pending': '\033[90m',   # Gray
                    'ready_for_training': '\033[96m',  # Cyan
                    'preparing_dataset': '\033[94m',   # Blue
                    'configuring_preset': '\033[95m',  # Magenta
                    'generating_preview': '\033[93m',  # Yellow
                }
                color = status_colors.get(status, '')
                reset = '\033[0m' if color else ''
                
                # Map status to display text
                status_display = {
                    'done': 'Done',
                    'failed': 'Failed',
                    'training': 'Training',
                    'pending': 'Pending',
                    'ready_for_training': 'Ready to train',
                    'preparing_dataset': 'Preparing dataset',
                    'configuring_preset': 'Configuring preset',
                    'generating_preview': 'Generating preview',
                    'in_queue': 'In queue',
                    'cancelled': 'Cancelled'
                }
                display_status = status_display.get(status, status)
                
                print(f"{job_id:<10} {color}{display_status:<20}{reset} {job_type:<12} {dataset:<25} {preset:<15} {duration_str:<10} {created_str:<20}")
        
        return 0
    
    def _handle_job_info(self, args: UnifiedArgs) -> int:
        """Handle detailed job information display."""
        from src.utils.job_tracker import get_tracker
        import json
        
        tracker = get_tracker()
        job = tracker.get_job_info(args.job_id)
        
        if not job:
            if args.json:
                print(json.dumps({"error": f"Job {args.job_id} not found"}))
            else:
                print(f"Error: Job {args.job_id} not found")
            return 1
        
        if args.json:
            print(json.dumps(job, indent=2))
        else:
            print(f"\n\033[1mJob Details: {args.job_id}\033[0m\n")
            
            # Basic info
            print(f"Status:       {job.get('status', 'N/A')}")
            print(f"Type:         {job.get('type', 'N/A')}")
            print(f"Dataset:      {job.get('dataset_name', 'N/A')}")
            print(f"Preset:       {job.get('preset', 'N/A')}")
            
            # Timing info
            print(f"\nTiming:")
            print(f"Started:      {job.get('start_time', 'N/A')}")
            print(f"Ended:        {job.get('end_time', 'N/A')}")
            
            duration = job.get('duration_seconds')
            if duration:
                if isinstance(duration, str):
                    # Already formatted
                    print(f"Duration:     {duration}")
                else:
                    # Format numeric value
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"Duration:     {minutes}m {seconds}s")
            
            # Progress info
            if job.get('total_steps'):
                current = job.get('current_step', 0)
                total = job.get('total_steps')
                progress = (current / total) * 100 if total > 0 else 0
                print(f"\nProgress:     {current}/{total} steps ({progress:.1f}%)")
            
            # Output info
            if job.get('output_path'):
                print(f"\nOutput:       {job['output_path']}")
            
            # Error info
            if job.get('error_message'):
                print(f"\n\033[91mError:        {job['error_message']}\033[0m")
            
            # Variation-specific info
            if job.get('type') == 'variation':
                print(f"\nVariation Details:")
                print(f"Experiment:   {job.get('experiment_name', 'N/A')}")
                print(f"Variation ID: {job.get('variation_id', 'N/A')}")
                print(f"Parent Exp:   {job.get('parent_experiment_id', 'N/A')}")
                
                if job.get('varied_parameters'):
                    print(f"\nVaried Parameters:")
                    for param, values in job['varied_parameters'].items():
                        print(f"  {param}: {values}")
                
                if job.get('parameter_values'):
                    print(f"\nParameter Values:")
                    for param, value in job['parameter_values'].items():
                        print(f"  {param}: {value}")
        
        return 0
    
    def _handle_db_stats(self, args: UnifiedArgs) -> int:
        """Handle database statistics display."""
        from src.utils.job_tracker import get_tracker
        import json
        
        tracker = get_tracker()
        stats = tracker.get_statistics()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n\033[1mDatabase Statistics\033[0m\n")
            
            # Total counts
            print(f"Total Executions:     {stats.get('total_executions', 0)}")
            print(f"Total Variations:     {stats.get('total_variations', 0)}")
            total = stats.get('total_executions', 0) + stats.get('total_variations', 0)
            print(f"Total Jobs:           {total}")
            
            # Success rate
            success_rate = stats.get('success_rate', 0) * 100
            print(f"\nSuccess Rate:         {success_rate:.1f}%")
            
            # Average duration
            avg_duration = stats.get('average_duration', 0)
            if avg_duration:
                if isinstance(avg_duration, str):
                    # Already formatted
                    print(f"Average Duration:     {avg_duration}")
                else:
                    # Format numeric value
                    minutes = int(avg_duration // 60)
                    seconds = int(avg_duration % 60)
                    print(f"Average Duration:     {minutes}m {seconds}s")
            
            # Status breakdown
            print("\nExecutions by Status:")
            exec_status = stats.get('executions_by_status', {})
            for status, count in exec_status.items():
                print(f"  {status:<20} {count}")
            
            if stats.get('variations_by_status'):
                print("\nVariations by Status:")
                var_status = stats.get('variations_by_status', {})
                for status, count in var_status.items():
                    print(f"  {status:<20} {count}")
        
        return 0
    
    def _handle_clear_db(self, args: UnifiedArgs) -> int:
        """Handle database clearing with confirmation."""
        from src.database import DatabaseManager
        from src.database.config import db_settings
        from src.utils.quiet_mode import quiet_database_init
        import sys
        
        # Get current statistics first with quiet DB init
        with quiet_database_init():
            db = DatabaseManager()
        stats = db.get_statistics()
        
        total_records = stats.get('total_executions', 0) + stats.get('total_variations', 0)
        
        if total_records == 0:
            print("Database is already empty.")
            return 0
        
        # Show database type
        db_type = db_settings.db_type.upper()
        db_info = ""
        if db_type == 'SQLITE':
            db_info = f" (SQLite: {db_settings._config.get('path', 'unknown')})"
        elif db_type == 'POSTGRESQL':
            host = db_settings._config.get('host', 'localhost')
            database = db_settings._config.get('database', 'autotrainx')
            db_info = f" (PostgreSQL: {database}@{host})"
        
        # Show warning
        print(f"\n\033[93m⚠️  WARNING: This will permanently delete all records from the {db_type} database{db_info}!\033[0m")
        print(f"\nCurrent database contains:")
        print(f"  • {stats.get('total_executions', 0)} execution records")
        print(f"  • {stats.get('total_variations', 0)} variation records")
        print(f"  • \033[1m{total_records} total records\033[0m")
        
        # Ask for confirmation
        print("\n\033[91mThis action cannot be undone!\033[0m")
        response = input("\nAre you sure you want to delete all records? Type 'yes' to confirm: ")
        
        if response.lower() != 'yes':
            print("\n\033[90mOperation cancelled.\033[0m")
            return 0
        
        # Second confirmation for safety
        response2 = input("\nType the word 'DELETE' to confirm deletion: ")
        
        if response2 != 'DELETE':
            print("\n\033[90mOperation cancelled.\033[0m")
            return 0
        
        # Perform deletion
        print("\n\033[93mDeleting all records...\033[0m")
        
        try:
            deleted_counts = db.clear_all_records()
            
            print("\n\033[92m✓ Database cleared successfully!\033[0m")
            print(f"  • Deleted {deleted_counts['executions']} execution records")
            print(f"  • Deleted {deleted_counts['variations']} variation records")
            total = deleted_counts['executions'] + deleted_counts['variations']
            print(f"  • Total: {total} records deleted")
            
            return 0
            
        except Exception as e:
            print(f"\n\033[91mError clearing database: {e}\033[0m")
            return 1
    
    def _handle_cleanup_stale(self, args: UnifiedArgs) -> int:
        """Handle cleanup of stale processes."""
        from src.database import DatabaseManager
        from src.utils.quiet_mode import quiet_database_init
        
        print("\n\033[96m🔍 Cleaning up stale processes...\033[0m")
        
        try:
            with quiet_database_init():
                db = DatabaseManager()
            cleaned_count = db.cleanup_stale_processes()
            
            if cleaned_count > 0:
                print(f"\n\033[92m✓ Cleaned up {cleaned_count} stale process(es)\033[0m")
                print("\nThese jobs were stuck in active states but their processes were no longer running.")
                print("They have been marked as 'failed' with appropriate error messages.")
            else:
                print("\n\033[92m✓ No stale processes found\033[0m")
                print("All active jobs appear to have running processes.")
            
            return 0
            
        except Exception as e:
            print(f"\n\033[91mError during stale process cleanup: {e}\033[0m")
            return 1
    
    def _update_model_path(self, job_id: str, dataset_name: str, preset_name: str):
        """Update the job with the exact model file path."""
        try:
            # Determine output directory
            output_dir = self.pipeline.base_path / "workspace" / "output" / dataset_name / "model"
            
            if output_dir.exists():
                # Find the most recent .safetensors file
                model_files = list(output_dir.glob("*.safetensors"))
                if model_files:
                    # Get the most recent file
                    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
                    
                    # Update the job with the exact path
                    from src.utils.job_tracker import get_tracker
                    tracker = get_tracker()
                    tracker.set_output_path(job_id, str(latest_model))
        except Exception as e:
            import logging
            logging.warning(f"Could not update model path for job {job_id}: {e}")
    
    def _update_variation_model_path(self, job_id: str, variation_name: str):
        """Update the job with the exact model file path for variations."""
        try:
            # Variations are stored in workspace/Variations/
            output_dir = self.pipeline.base_path / "workspace" / "Variations" / variation_name / "model"
            
            if output_dir.exists():
                # Find the most recent .safetensors file
                model_files = list(output_dir.glob("*.safetensors"))
                if model_files:
                    # Get the most recent file
                    latest_model = max(model_files, key=lambda p: p.stat().st_mtime)
                    
                    # Update the job with the exact path
                    from src.utils.job_tracker import get_tracker
                    tracker = get_tracker()
                    tracker.set_output_path(job_id, str(latest_model))
        except Exception as e:
            import logging
            logging.warning(f"Could not update variation model path for job {job_id}: {e}")
    
    def _handle_list_profiles(self, args: UnifiedArgs) -> int:
        """Handle listing path profiles."""
        profile_manager = PathProfile(base_path=args.base_path)
        profiles = profile_manager.list_profiles()
        
        if args.json:
            import json
            print(json.dumps(profiles, indent=2))
        else:
            print("\n=== Path Profiles ===")
            active_profile = Config.get_active_profile(args.base_path)
            
            for name, profile in profiles.items():
                is_active = " (active)" if name == active_profile else ""
                print(f"\n📁 {name}{is_active}")
                print(f"   Description: {profile.get('description', 'No description')}")
                
                custom_path = profile.get('custom_output_path')
                if custom_path:
                    print(f"   Custom path: {custom_path}")
                else:
                    print(f"   Custom path: None (uses default workspace)")
                
                if profile.get('created'):
                    print(f"   Created: {profile['created']}")
        
        return 0
    
    def _handle_save_profile(self, args: UnifiedArgs) -> int:
        """Handle saving a path profile."""
        profile_name = args.save_profile
        
        # Get current custom path from args or config
        custom_path = args.custom_path or Config.get_custom_output_path(args.base_path)
        
        # Create description
        if custom_path:
            description = f"Custom output path: {custom_path}"
        else:
            description = "Default workspace configuration"
        
        # Save profile
        profile_manager = PathProfile(base_path=args.base_path)
        profile_manager.create_profile(
            name=profile_name,
            custom_output_path=custom_path,
            description=description
        )
        
        print(f"✓ Profile '{profile_name}' saved successfully")
        
        # Optionally set as active
        response = input(f"\nSet '{profile_name}' as the active profile? (y/N): ")
        if response.lower() == 'y':
            Config.set_active_profile(profile_name, args.base_path)
        
        return 0
    
    def _handle_delete_profile(self, args: UnifiedArgs) -> int:
        """Handle deleting a path profile."""
        profile_name = args.delete_profile
        
        if profile_name == "default":
            print("Error: Cannot delete the default profile")
            return 1
        
        profile_manager = PathProfile(base_path=args.base_path)
        if profile_manager.delete_profile(profile_name):
            print(f"✓ Profile '{profile_name}' deleted successfully")
            
            # If it was the active profile, switch to default
            if Config.get_active_profile(args.base_path) == profile_name:
                Config.set_active_profile("default", args.base_path)
                print("ℹ️  Switched to default profile")
            
            return 0
        else:
            print(f"Error: Profile '{profile_name}' not found")
            return 1
            
    def _handle_set_profile(self, args: UnifiedArgs) -> int:
        """Set the active profile."""
        profile_name = args.set_profile
        profile_manager = PathProfile(base_path=args.base_path)
        
        # Check if profile exists
        profile = profile_manager.get_profile(profile_name)
        if not profile:
            print(f"Error: Profile '{profile_name}' not found")
            print("\nAvailable profiles:")
            for name in profile_manager.list_profiles():
                print(f"  - {name}")
            return 1
        
        # Set as active profile
        Config.set_active_profile(profile_name, args.base_path)
        
        # Show profile details
        print(f"\n✓ Active profile set to: {profile_name}")
        if profile_name != 'default':
            custom_path = profile.get('custom_output_path')
            if custom_path:
                print(f"  Custom output path: {custom_path}")
        else:
            print("  Using default workspace paths")
        
        print(f"\nThis profile will be used automatically for all future commands.")
        print(f"To use a different profile temporarily, use --use-profile <name>")
        
        return 0
            
    def _display_hook_results(self, hook_results: Dict[str, Any], json_output: bool = False, compact: bool = False) -> None:
        """Display post-training hook results to user."""
        if not hook_results:
            return
            
        try:
            from src.pipeline.utils.file_move_reporter import FileMoveReporter
            
            # Check if file move hook was executed
            file_move_results = hook_results.get('FileMoveHook', {})
            
            if json_output:
                # For JSON output, include hook results in structured format
                import json
                if hook_results:
                    hook_output = {
                        "post_training_hooks": {
                            "executed": hook_results.get('_summary', {}).get('executed_hooks', []),
                            "results": {k: v for k, v in hook_results.items() if k != '_summary'}
                        }
                    }
                    print(json.dumps(hook_output, indent=2))
            else:
                # Display file move results if available
                if file_move_results and 'file_move_results' in file_move_results:
                    results = file_move_results.get('file_move_results', [])
                    
                    # Use compact style for file move results
                    # For batch/variations use ultra compact, for single use compact
                    if compact or len(results) > 1:
                        # Ultra compact for multiple files
                        report = FileMoveReporter.report_results(
                            results, 
                            style=FileMoveReporter.STYLE_COMPACT
                        )
                    else:
                        # Regular compact for single file
                        report = FileMoveReporter.report_results(
                            results,
                            mode='compact',
                            verbose=False
                        )
                    
                    if report:
                        print(report)
                    
                    # Report summary for multiple datasets
                    if len(results) > 1 and not compact:
                        summary = file_move_results.get('file_move_summary', {})
                        summary_report = FileMoveReporter.report_summary(summary)
                        if summary_report:
                            print(summary_report)
                        
        except ImportError:
            # Fallback if reporter is not available
            if not json_output and file_move_results.get('success'):
                target = file_move_results.get('destination', 'custom location')
                print(f"✅ Files moved to: {target}")