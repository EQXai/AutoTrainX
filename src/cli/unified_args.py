"""
Unified argument handling system for AutoTrainX.

This module provides a centralized configuration for all CLI arguments,
simplifying the command structure and making it more intuitive.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
import argparse


class Operation(Enum):
    """Available operations."""
    TRAIN = "train"
    PREPARE = "prepare"
    CONFIGURE = "configure"
    STATUS = "status"
    LIST_PRESETS = "list-presets"
    DATASET_INFO = "dataset-info"
    SET_CONFIG = "set-config"
    VALIDATE_PREVIEW = "validate-preview"
    DIAGNOSE_COMFYUI = "diagnose-comfyui"
    CREATE_PRESET = "create-preset"
    DELETE_PRESET = "delete-preset"
    SHOW_PRESET = "show-preset"
    # Database operations
    JOB_HISTORY = "job-history"
    JOB_INFO = "job-info"
    DB_STATS = "db-stats"
    CLEAR_DB = "clear-db"
    CLEANUP_STALE = "cleanup-stale"
    # Path profile operations
    LIST_PROFILES = "list-profiles"
    SAVE_PROFILE = "save-profile"
    DELETE_PROFILE = "delete-profile"
    SET_PROFILE = "set-profile"


class Mode(Enum):
    """Execution modes."""
    SINGLE = "single"
    BATCH = "batch"
    VARIATIONS = "variations"


@dataclass
class UnifiedArgs:
    """Unified argument structure for all operations."""
    # Main operation
    operation: Operation
    
    # Common arguments
    source: Optional[str] = None
    preset: Optional[str] = None
    mode: Mode = Mode.SINGLE
    base_path: Optional[str] = None
    
    # Mode-specific arguments
    variations: Optional[Dict[str, List[Any]]] = None
    parallel: bool = False
    continue_on_error: bool = False
    
    # Dataset preparation arguments
    repeats: int = 30
    class_name: str = "person"
    
    # Output control
    json: bool = False
    auto_clean: bool = False
    raw_output: bool = False  # Show raw training logs instead of progress bar
    
    # Additional arguments
    dataset_name: Optional[str] = None
    naming_template: str = "{dataset}_{preset}_{variation}"
    
    # ComfyUI configuration
    comfyui_path: Optional[str] = None
    preview: Optional[int] = None
    set_progress_display: Optional[str] = None
    
    # Custom path configuration
    custom_path: Optional[str] = None
    save_profile: Optional[str] = None
    use_profile: Optional[str] = None
    list_profiles: bool = False
    delete_profile: Optional[str] = None
    set_profile: Optional[str] = None
    
    # Preset management arguments
    preset_name: Optional[str] = None
    base_preset: Optional[str] = None
    preset_description: Optional[str] = None
    preset_overrides: Optional[Dict[str, Any]] = None
    
    # Database query arguments
    job_id: Optional[str] = None
    limit: int = 20
    filter_status: Optional[str] = None
    filter_dataset: Optional[str] = None
    

class UnifiedArgumentParser:
    """Centralized argument parser for AutoTrainX."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create the argument parser with simplified structure."""
        parser = argparse.ArgumentParser(
            description="AutoTrainX - Automated training pipeline for image generation models",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Train a single dataset
  python main.py --train --single --source /home/eqx/datasets/3/dl4r0s4 --preset FluxLORA
  
  # Train multiple datasets in batch
  python main.py --train --batch --source /home/eqx/datasets/3 --preset FluxLORA
  
  # Train with configuration variations
  python main.py --train --mode variations --source /home/eqx/datasets/1/b09g13 --preset FluxLORA \\
         --variations network_dim=32,64,128 network_alpha=16,32
  
  # Just prepare dataset without training
  python main.py --prepare --single --source /home/eqx/datasets/1/b09g13
  
  # Show status
  python main.py --status
            """
        )
        
        # Main operation (required)
        parser.add_argument(
            '--train',
            action='store_const',
            const=Operation.TRAIN,
            dest='operation',
            help='Train model (includes dataset preparation)'
        )
        parser.add_argument(
            '--prepare',
            action='store_const',
            const=Operation.PREPARE,
            dest='operation',
            help='Only prepare dataset without training'
        )
        parser.add_argument(
            '--configure',
            action='store_const',
            const=Operation.CONFIGURE,
            dest='operation',
            help='Generate configurations for existing datasets'
        )
        parser.add_argument(
            '--status',
            action='store_const',
            const=Operation.STATUS,
            dest='operation',
            help='Show pipeline status'
        )
        parser.add_argument(
            '--list-presets',
            action='store_const',
            const=Operation.LIST_PRESETS,
            dest='operation',
            help='List available presets'
        )
        parser.add_argument(
            '--dataset-info',
            metavar='DATASET',
            dest='dataset_name',
            help='Show information about a dataset'
        )
        parser.add_argument(
            '--validate-preview',
            action='store_const',
            const=Operation.VALIDATE_PREVIEW,
            dest='operation',
            help='Validate image preview system requirements'
        )
        parser.add_argument(
            '--diagnose-comfyui',
            action='store_const',
            const=Operation.DIAGNOSE_COMFYUI,
            dest='operation',
            help='Diagnose ComfyUI installation and environment'
        )
        
        # Preset management operations
        parser.add_argument(
            '--create-preset',
            action='store_const',
            const=Operation.CREATE_PRESET,
            dest='operation',
            help='Create a new custom preset'
        )
        parser.add_argument(
            '--delete-preset',
            action='store_const',
            const=Operation.DELETE_PRESET,
            dest='operation',
            help='Delete a custom preset'
        )
        parser.add_argument(
            '--show-preset',
            action='store_const',
            const=Operation.SHOW_PRESET,
            dest='operation',
            help='Show preset configuration details'
        )
        
        # Database operations
        parser.add_argument(
            '--job-history',
            action='store_const',
            const=Operation.JOB_HISTORY,
            dest='operation',
            help='Show job execution history'
        )
        parser.add_argument(
            '--job-info',
            action='store_const',
            const=Operation.JOB_INFO,
            dest='operation',
            help='Show detailed information for a specific job'
        )
        parser.add_argument(
            '--db-stats',
            action='store_const',
            const=Operation.DB_STATS,
            dest='operation',
            help='Show database statistics'
        )
        parser.add_argument(
            '--clear-db',
            action='store_const',
            const=Operation.CLEAR_DB,
            dest='operation',
            help='Clear all records from the database (requires confirmation)'
        )
        parser.add_argument(
            '--cleanup-stale',
            action='store_const',
            const=Operation.CLEANUP_STALE,
            dest='operation',
            help='Clean up stale processes that are stuck in active states'
        )
        
        # Mode selection (shortcuts for common modes)
        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument(
            '--single',
            action='store_const',
            const=Mode.SINGLE,
            dest='mode',
            help='Process single dataset (default)'
        )
        mode_group.add_argument(
            '--batch',
            action='store_const',
            const=Mode.BATCH,
            dest='mode',
            help='Process multiple datasets'
        )
        mode_group.add_argument(
            '--mode',
            type=str,
            choices=['single', 'batch', 'variations'],
            dest='mode_str',
            help='Execution mode'
        )
        
        # Common arguments
        parser.add_argument(
            '--source', '-s',
            type=str,
            help='Source path (dataset, directory, or dataset name for variations)'
        )
        parser.add_argument(
            '--preset', '-p',
            type=str,
            help='Training preset (e.g., FluxLORA, FluxCheckpoint, SDXLCheckpoint)'
        )
        parser.add_argument(
            '--base-path',
            type=str,
            help='Base path for AutoTrainX project'
        )
        
        # Variation mode arguments
        parser.add_argument(
            '--variations',
            nargs='+',
            type=str,
            help='Parameter variations: param=val1,val2,val3'
        )
        
        # Batch mode arguments
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Process datasets in parallel (batch mode)'
        )
        parser.add_argument(
            '--continue-on-error',
            action='store_true',
            help='Continue processing if some datasets fail'
        )
        
        # Dataset preparation arguments
        parser.add_argument(
            '--repeats', '-r',
            type=int,
            default=30,
            help='Training repetitions (default: 30)'
        )
        parser.add_argument(
            '--class', '-c',
            dest='class_name',
            type=str,
            default="person",
            help='Class name (default: person)'
        )
        
        # Output control
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )
        parser.add_argument(
            '--auto-clean',
            action='store_true',
            help='Automatically clean existing datasets'
        )
        parser.add_argument(
            '--raw-output',
            action='store_true',
            help='Show raw training logs instead of progress bar'
        )
        
        # Additional arguments
        parser.add_argument(
            '--naming-template',
            type=str,
            default="{dataset}_{preset}_{variation}",
            help='Naming template for variations'
        )
        
        # ComfyUI configuration
        parser.add_argument(
            '--comfyui-path',
            type=str,
            help='Path to ComfyUI installation directory (will be saved for future use)'
        )
        parser.add_argument(
            '--preview',
            type=int,
            metavar='N',
            help='Generate N preview images after training (requires ComfyUI)'
        )
        
        # Training display settings
        parser.add_argument(
            '--set-progress-display',
            choices=['progress', 'raw'],
            help='Set default training output display (progress bar or raw logs)'
        )
        
        # Custom path arguments
        parser.add_argument(
            '--custom-path',
            type=str,
            help='Custom output path for models, configs, and previews'
        )
        parser.add_argument(
            '--save-profile',
            type=str,
            help='Save current path configuration as a profile'
        )
        parser.add_argument(
            '--use-profile',
            type=str,
            help='Use a saved path profile'
        )
        parser.add_argument(
            '--list-profiles',
            action='store_true',
            help='List available path profiles'
        )
        parser.add_argument(
            '--delete-profile',
            type=str,
            help='Delete a saved path profile'
        )
        parser.add_argument(
            '--set-profile',
            type=str,
            help='Set active path profile (will be used by default in future commands)'
        )
        
        # Preset management arguments
        parser.add_argument(
            '--name',
            dest='preset_name',
            type=str,
            help='Name for the preset (for create/delete/show operations)'
        )
        parser.add_argument(
            '--base',
            dest='base_preset',
            type=str,
            help='Base preset to inherit from (for create-preset)'
        )
        parser.add_argument(
            '--description',
            dest='preset_description',
            type=str,
            help='Description for the custom preset (for create-preset)'
        )
        parser.add_argument(
            '--overrides',
            dest='preset_overrides',
            nargs='+',
            type=str,
            help='Configuration overrides: param=value (for create-preset)'
        )
        
        # Database query arguments
        parser.add_argument(
            '--job-id',
            dest='job_id',
            type=str,
            help='Job ID for job-info operation'
        )
        parser.add_argument(
            '--limit',
            dest='limit',
            type=int,
            default=20,
            help='Maximum number of results to show (default: 20)'
        )
        parser.add_argument(
            '--filter-status',
            dest='filter_status',
            type=str,
            choices=['pending', 'in_queue', 'preparing_dataset', 'configuring_preset', 
                    'ready_for_training', 'training', 'generating_preview', 'done', 'failed', 'cancelled'],
            help='Filter results by status'
        )
        parser.add_argument(
            '--filter-dataset',
            dest='filter_dataset',
            type=str,
            help='Filter results by dataset name'
        )
        
        return parser
    
    @staticmethod
    def parse_args(args=None) -> UnifiedArgs:
        """Parse arguments and return unified args object."""
        parser = UnifiedArgumentParser.create_parser()
        parsed = parser.parse_args(args)
        
        # Determine operation
        if parsed.dataset_name:
            operation = Operation.DATASET_INFO
        elif parsed.list_profiles:
            operation = Operation.LIST_PROFILES
        elif parsed.save_profile:
            operation = Operation.SAVE_PROFILE
        elif parsed.delete_profile:
            operation = Operation.DELETE_PROFILE
        elif hasattr(parsed, 'set_profile') and parsed.set_profile:
            operation = Operation.SET_PROFILE
        elif parsed.comfyui_path and not parsed.operation:
            # If only comfyui-path is provided, treat it as a config operation
            operation = Operation.SET_CONFIG
        elif hasattr(parsed, 'set_progress_display') and parsed.set_progress_display:
            # If only set-progress-display is provided, treat it as a config operation
            operation = Operation.SET_CONFIG
        elif parsed.operation:
            operation = parsed.operation
        else:
            parser.error("No operation specified. Use --train, --prepare, --configure, --status, or --list-presets")
        
        # Determine mode
        if parsed.mode:
            mode = parsed.mode
        elif hasattr(parsed, 'mode_str') and parsed.mode_str:
            mode = Mode(parsed.mode_str)
        else:
            mode = Mode.SINGLE
        
        # Parse variations
        variations = None
        if parsed.variations:
            variations = UnifiedArgumentParser._parse_variations(parsed.variations)
        
        # Parse preset overrides
        preset_overrides = None
        if hasattr(parsed, 'preset_overrides') and parsed.preset_overrides:
            preset_overrides = UnifiedArgumentParser._parse_overrides(parsed.preset_overrides)
        
        # Get base path
        base_path = parsed.base_path
        if not base_path:
            from src.config import Config
            base_path = Config.get_default_base_path()
        
        return UnifiedArgs(
            operation=operation,
            source=parsed.source,
            preset=parsed.preset,
            mode=mode,
            base_path=base_path,
            variations=variations,
            parallel=parsed.parallel,
            continue_on_error=parsed.continue_on_error,
            repeats=parsed.repeats,
            class_name=parsed.class_name,
            json=parsed.json,
            auto_clean=parsed.auto_clean,
            raw_output=parsed.raw_output,
            dataset_name=parsed.dataset_name,
            naming_template=parsed.naming_template,
            comfyui_path=parsed.comfyui_path,
            preview=parsed.preview,
            set_progress_display=parsed.set_progress_display if hasattr(parsed, 'set_progress_display') else None,
            preset_name=parsed.preset_name if hasattr(parsed, 'preset_name') else None,
            base_preset=parsed.base_preset if hasattr(parsed, 'base_preset') else None,
            preset_description=parsed.preset_description if hasattr(parsed, 'preset_description') else None,
            preset_overrides=preset_overrides,
            job_id=parsed.job_id if hasattr(parsed, 'job_id') else None,
            limit=parsed.limit if hasattr(parsed, 'limit') else 20,
            filter_status=parsed.filter_status if hasattr(parsed, 'filter_status') else None,
            filter_dataset=parsed.filter_dataset if hasattr(parsed, 'filter_dataset') else None,
            custom_path=parsed.custom_path if hasattr(parsed, 'custom_path') else None,
            save_profile=parsed.save_profile if hasattr(parsed, 'save_profile') else None,
            use_profile=parsed.use_profile if hasattr(parsed, 'use_profile') else None,
            list_profiles=parsed.list_profiles if hasattr(parsed, 'list_profiles') else False,
            delete_profile=parsed.delete_profile if hasattr(parsed, 'delete_profile') else None,
            set_profile=parsed.set_profile if hasattr(parsed, 'set_profile') else None
        )
    
    @staticmethod
    def _parse_variations(variations_args: List[str]) -> Dict[str, List[Any]]:
        """Parse variation arguments into a dictionary."""
        variations = {}
        
        for var_spec in variations_args:
            if '=' not in var_spec:
                raise ValueError(f"Invalid variation format: {var_spec}. Expected: param=val1,val2,val3")
            
            param, values = var_spec.split('=', 1)
            parsed_values = []
            
            for value in values.split(','):
                try:
                    # Try to parse as number
                    if '.' in value or 'e' in value.lower():
                        parsed_values.append(float(value))
                    else:
                        parsed_values.append(int(value))
                except ValueError:
                    # Keep as string
                    parsed_values.append(value.strip())
            
            variations[param] = parsed_values
        
        return variations
    
    @staticmethod
    def _parse_overrides(overrides_args: List[str]) -> Dict[str, Any]:
        """Parse override arguments into a dictionary."""
        overrides = {}
        
        for override_spec in overrides_args:
            if '=' not in override_spec:
                raise ValueError(f"Invalid override format: {override_spec}. Expected: param=value")
            
            param, value = override_spec.split('=', 1)
            
            # Try to parse the value
            try:
                # Try to parse as number
                if '.' in value or 'e' in value.lower():
                    parsed_value = float(value)
                else:
                    parsed_value = int(value)
            except ValueError:
                # Try to parse as boolean
                if value.lower() in ['true', 'false']:
                    parsed_value = value.lower() == 'true'
                else:
                    # Keep as string
                    parsed_value = value.strip()
            
            # Handle nested parameters (e.g., optimizer_args.lr)
            if '.' in param:
                keys = param.split('.')
                current = overrides
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[keys[-1]] = parsed_value
            else:
                overrides[param] = parsed_value
        
        return overrides
    
    @staticmethod
    def validate_args(args: UnifiedArgs) -> Optional[str]:
        """
        Validate parsed arguments.
        
        Returns:
            Error message if validation fails, None if valid.
        """
        # Operation-specific validation
        if args.operation in [Operation.TRAIN, Operation.PREPARE]:
            if not args.source:
                return f"--source is required for {args.operation.value}"
            
            if args.mode == Mode.BATCH:
                source_path = Path(args.source)
                if not source_path.is_dir():
                    return "For batch mode, --source must be a directory"
            
            elif args.mode == Mode.VARIATIONS:
                if not args.preset:
                    return "--preset is required for variations mode"
                if not args.variations:
                    return "--variations is required for variations mode"
        
        # Training requires preset (except variations which can detect it)
        if args.operation == Operation.TRAIN:
            if args.mode != Mode.VARIATIONS and not args.preset:
                return "--preset is required for training"
        
        # Status, list-presets don't need additional args
        if args.operation in [Operation.STATUS, Operation.LIST_PRESETS]:
            pass
        
        # Dataset info needs dataset name
        if args.operation == Operation.DATASET_INFO and not args.dataset_name:
            return "Dataset name is required for --dataset-info"
        
        # Preset management validation
        if args.operation == Operation.CREATE_PRESET:
            if not args.preset_name:
                return "--name is required for --create-preset"
            if not args.base_preset:
                return "--base is required for --create-preset"
        
        if args.operation in [Operation.DELETE_PRESET, Operation.SHOW_PRESET]:
            if not args.preset_name:
                return "--name is required for this operation"
        
        # Database operations validation
        if args.operation == Operation.JOB_INFO:
            if not args.job_id:
                return "--job-id is required for --job-info"
        
        return None