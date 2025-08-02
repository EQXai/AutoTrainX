"""
Command-line argument parser for AutoTrainX.

This module handles all CLI argument parsing and validation,
providing a clean interface for the main application.
"""

import argparse
from typing import Optional
from pathlib import Path

from src.config import Config


class CLIParser:
    """Handles command-line argument parsing for AutoTrainX."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            description="AutoTrainX Pipeline - Dataset preparation and preset configuration",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Single mode (default) - Process one dataset
  python main.py --prepare --source /home/eqx/datasets/1/b09g13
  python main.py --prepare --source /home/eqx/datasets/1/b09g13 --mode single --repeats 50 --class character
  
  # Batch mode - Process all datasets in a directory
  # The directory should contain subdirectories, each being a dataset
  python main.py --prepare --mode batch --source /home/eqx/datasets/collection1
  python main.py --prepare --mode batch --source /home/eqx/datasets/collection1 --parallel
  python main.py --prepare --mode batch --source /home/eqx/datasets/collection1 --continue-on-error
  
  # Variations mode - Create configuration variations for experimentation
  # --source should be the dataset name or path (will extract name)
  python main.py --prepare --mode variations --source b09g13 --preset FluxLORA --variations learning_rate=1e-4,1e-5,1e-6 batch_size=1,2,4
  python main.py --prepare --mode variations --source /workspace/output/b09g13 --preset FluxLORA --variations network_dim=32,64,128 network_alpha=16,32
  
  # Training - Train model with prepared dataset
  python main.py --train --source /home/eqx/datasets/1/b09g13 --preset FluxLORA
  python main.py --train --mode batch --source /home/eqx/datasets/collection1 --preset FluxLORA
  python main.py --train --mode variations --source b09g13 --preset FluxLORA --variations learning_rate=1e-4,1e-5
  
  # Only generate configurations for all existing datasets
  python main.py --configure
  
  # Show status and available resources
  python main.py --status
  
  # List available presets
  python main.py --list-presets
  
  # Show dataset information
  python main.py --dataset-info b09g13
        """
        )
        
        # Operation modes (mutually exclusive)
        operation_group = parser.add_mutually_exclusive_group(required=True)
        operation_group.add_argument(
            '--prepare',
            action='store_true',
            help='Prepare dataset and generate configurations (requires --source)'
        )
        operation_group.add_argument(
            '--configure',
            action='store_true',
            help='Generate configurations only for existing datasets'
        )
        operation_group.add_argument(
            '--train',
            action='store_true',
            help='Train model with prepared dataset and configuration'
        )
        operation_group.add_argument(
            '--status',
            action='store_true',
            help='Show pipeline status and available resources'
        )
        operation_group.add_argument(
            '--list-presets',
            action='store_true',
            help='List available presets with descriptions'
        )
        operation_group.add_argument(
            '--dataset-info',
            type=str,
            metavar='DATASET_NAME',
            help='Show detailed information about a specific dataset'
        )
        
        # Pipeline mode selection
        parser.add_argument(
            '--mode', '-m',
            type=str,
            choices=['single', 'batch', 'variations'],
            default='single',
            help='Pipeline execution mode (default: single)'
        )
        
        # Common source argument - interpreted differently based on mode
        parser.add_argument(
            '--source', '-s',
            type=str,
            help='Source path: dataset path (single), directory of datasets (batch), or dataset name (variations)'
        )
        
        # Batch mode specific arguments
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Process datasets in parallel (batch mode)'
        )
        
        parser.add_argument(
            '--continue-on-error',
            action='store_true',
            help='Continue processing even if some datasets fail (batch mode)'
        )
        
        # Variations mode specific arguments
        parser.add_argument(
            '--preset',
            type=str,
            help='Base preset for variations mode'
        )
        
        parser.add_argument(
            '--variations',
            nargs='+',
            type=str,
            help='Parameter variations in format: param=val1,val2,val3 (variations mode)'
        )
        
        parser.add_argument(
            '--naming-template',
            type=str,
            default="{dataset}_{preset}_{variation}",
            help='Naming template for variations (default: {dataset}_{preset}_{variation})'
        )
        
        # Common arguments
        parser.add_argument(
            '--repeats', '-r',
            type=int,
            default=30,
            help='Number of repetitions for training (default: 30)'
        )
        
        parser.add_argument(
            '--class', '-c',
            dest='class_name',
            type=str,
            default="person",
            help='Class name for the object (default: "person")'
        )
        
        parser.add_argument(
            '--base-path', '-b',
            type=str,
            default=Config.get_default_base_path(),
            help=f'Base path for AutoTrainX project (default: auto-detected or AUTOTRAINX_BASE_PATH env var)'
        )
        
        parser.add_argument(
            '--auto-clean',
            action='store_true',
            help='Skip interactive prompts and automatically clean existing datasets (batch mode)'
        )
        
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results in JSON format'
        )
        
        return parser
    
    @staticmethod
    def parse_args():
        """Parse command-line arguments."""
        parser = CLIParser.create_parser()
        return parser.parse_args()
    
    @staticmethod
    def validate_args(args) -> Optional[str]:
        """
        Validate parsed arguments.
        
        Returns:
            Optional[str]: Error message if validation fails, None if valid.
        """
        if args.prepare or args.train:
            mode = args.mode or 'single'
            
            if not args.source:
                return f"--source is required for {mode} mode"
            
            if mode == 'batch':
                source_path = Path(args.source)
                if not source_path.is_dir():
                    return "For batch mode, --source must be a directory containing dataset subdirectories"
            
            elif mode == 'variations':
                if not args.preset:
                    return "--preset is required for variations mode"
                
                if not args.variations:
                    return "--variations is required for variations mode"
                
                # Validate variation format
                for var_spec in args.variations:
                    if '=' not in var_spec:
                        return f"Invalid variation format: {var_spec}. Expected format: param=value1,value2,value3"
        
        # For training, preset is required except for variations mode
        if args.train and args.mode != 'variations' and not args.preset:
            return "--preset is required for training"
        
        return None