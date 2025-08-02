#!/usr/bin/env python3
"""
Dataset Preparation Script for AutoTrainX

This script prepares datasets for training by organizing files into the required structure:
- Copies source files to input directory
- Creates output directory structure with proper naming
- Generates sample prompts file
- Validates image-text pairs

Usage:
    python dataset_preparation.py --source /path/to/dataset --name dataset_name
"""

import os
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import re
import sys

# Add parent directory to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import Config
from src.utils.path_manager import PathManager
from src.pipeline.utils.shared_pipeline_utils import (
    print_dataset_extraction,
    print_cleaning_table,
    print_dataset_prep_header,
    print_dataset_prep_progress,
    print_summary_table,
    print_table_header
)


class DatasetPreparator:
    """Main class for dataset preparation operations."""
    
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def __init__(self, base_path: str = None, quiet_mode: bool = False, path_manager: Optional[PathManager] = None):
        """Initialize with base project path."""
        if base_path is None:
            base_path = Config.get_default_base_path()
        self.base_path = Path(base_path)
        self.path_manager = path_manager
        
        # Use PathManager if available
        if self.path_manager:
            self.input_path = self.path_manager.get_input_base_path()
            self.output_path = self.path_manager.get_output_base_path()
            self.presets_path = self.path_manager.get_workspace_path() / "Presets"
        else:
            self.input_path = self.base_path / "workspace/input"
            self.output_path = self.base_path / "workspace/output"
            self.presets_path = self.base_path / "workspace/Presets"
        self.quiet_mode = quiet_mode
        
    def validate_source_dataset(self, source_path: Path) -> List[Tuple[Path, Path]]:
        """
        Validate source dataset and return valid image-text pairs.
        
        Args:
            source_path: Path to source dataset
            
        Returns:
            List of tuples (image_file, text_file)
            
        Raises:
            ValueError: If no valid pairs found or validation fails
        """
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
            
        # Find all image files
        image_files = []
        for ext in self.SUPPORTED_IMAGE_FORMATS:
            image_files.extend(source_path.glob(f"*{ext}"))
            image_files.extend(source_path.glob(f"*{ext.upper()}"))
            
        if not image_files:
            raise ValueError(f"No image files found in {source_path}")
            
        # Find corresponding text files and validate pairs
        valid_pairs = []
        for image_file in image_files:
            # Look for corresponding .txt file
            txt_file = image_file.with_suffix('.txt')
            
            if txt_file.exists() and txt_file.stat().st_size > 0:
                valid_pairs.append((image_file, txt_file))
            else:
                if not self.quiet_mode:
                    print(f"  ⚠️  Warning: No valid text file found for {image_file.name}")
                
        if not valid_pairs:
            raise ValueError("No valid image-text pairs found")
            
        # Print validation info only in non-quiet mode
        if not self.quiet_mode and len(valid_pairs) > 0:
            print(f"  ℹ️  Found {len(valid_pairs)} valid image-text pairs")
        return valid_pairs
    
    def check_existing_dataset(self, dataset_name: str) -> bool:
        """
        Check if a dataset with the given name already exists.
        
        Args:
            dataset_name: Name of the dataset to check
            
        Returns:
            True if dataset exists in any location, False otherwise
        """
        input_exists = (self.input_path / dataset_name).exists()
        output_exists = (self.output_path / dataset_name).exists()
        
        # Check for preset configurations
        presets_exist = False
        if self.presets_path.exists():
            for preset_dir in self.presets_path.iterdir():
                if preset_dir.is_dir():
                    config_file = preset_dir / f"{dataset_name}_{preset_dir.name}.toml"
                    if config_file.exists():
                        presets_exist = True
                        break
        
        return input_exists or output_exists or presets_exist
    
    def clean_existing_dataset(self, dataset_name: str) -> Dict[str, List[str]]:
        """
        Clean all files and directories related to an existing dataset.
        
        Args:
            dataset_name: Name of the dataset to clean
            
        Returns:
            Dictionary with lists of cleaned items by category
        """
        cleaned = {
            'input': [],
            'output': [],
            'presets': []
        }
        
        # Clean input directory
        input_dir = self.input_path / dataset_name
        if input_dir.exists():
            shutil.rmtree(input_dir)
            cleaned['input'].append(str(input_dir))
        
        # Clean output directory
        output_dir = self.output_path / dataset_name
        if output_dir.exists():
            shutil.rmtree(output_dir)
            cleaned['output'].append(str(output_dir))
        
        # Clean preset configurations
        if self.presets_path.exists():
            for preset_dir in self.presets_path.iterdir():
                if preset_dir.is_dir():
                    config_file = preset_dir / f"{dataset_name}_{preset_dir.name}.toml"
                    if config_file.exists():
                        config_file.unlink()
                        cleaned['presets'].append(str(config_file))
        
        # Display cleaning table if not in quiet mode
        if not self.quiet_mode and any(cleaned.values()):
            print_cleaning_table(cleaned)
        
        return cleaned
        
    def copy_to_input(self, source_path: Path, dataset_name: str) -> Path:
        """
        Copy dataset files to input directory.
        
        Args:
            source_path: Source dataset path
            dataset_name: Name of the dataset
            
        Returns:
            Path to created input directory
        """
        # Create input directory structure
        if self.path_manager:
            input_dir = self.path_manager.get_input_path(dataset_name)
        else:
            input_dir = self.input_path / dataset_name
        input_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate source dataset
        valid_pairs = self.validate_source_dataset(source_path)
        
        # Copy files
        copied_files = 0
        for image_file, txt_file in valid_pairs:
            # Copy image file
            shutil.copy2(image_file, input_dir / image_file.name)
            # Copy text file
            shutil.copy2(txt_file, input_dir / txt_file.name)
            copied_files += 2
            
        # Return info for progress display
        return input_dir, copied_files
        
    def create_output_structure(self, dataset_name: str, repeats: int = 30, 
                              class_name: str = "person") -> Path:
        """
        Create output directory structure for training.
        
        Args:
            dataset_name: Name of the dataset
            repeats: Number of repetitions for training
            class_name: Class name for the object
            
        Returns:
            Path to created output directory
        """
        # Create main output directory
        if self.path_manager:
            output_dir = self.path_manager.get_output_path(dataset_name)
            self.path_manager.ensure_output_structure(dataset_name)
        else:
            output_dir = self.output_path / dataset_name
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create training images directory with proper naming
        img_dir_name = f"{repeats}_{dataset_name} {class_name}"
        img_dir = output_dir / "img" / img_dir_name
        img_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log and model directories
        log_dir = output_dir / "log"
        model_dir = output_dir / "model"
        log_dir.mkdir(exist_ok=True)
        model_dir.mkdir(exist_ok=True)
        
        # Copy files from input to training directory
        input_dir = self.input_path / dataset_name
        if input_dir.exists():
            for file in input_dir.iterdir():
                if file.is_file():
                    shutil.copy2(file, img_dir / file.name)
                    
        # Return info for progress display
        return output_dir, img_dir, log_dir, model_dir
        
    def generate_sample_prompts(self, dataset_name: str) -> Path:
        """
        Generate sample_prompts.txt file based on dataset content.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Path to created sample_prompts.txt file
        """
        input_dir = self.input_path / dataset_name
        output_dir = self.output_path / dataset_name
        
        if not input_dir.exists():
            raise ValueError(f"Input directory not found: {input_dir}")
            
        # Read text files to extract common prompts
        prompts = []
        txt_files = list(input_dir.glob("*.txt"))
        
        if txt_files:
            # Read first few text files to get sample prompts
            for txt_file in txt_files[:5]:  # Limit to first 5 files
                try:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            prompts.append(content)
                except Exception as e:
                    print(f"Warning: Could not read {txt_file}: {e}")
                    
        # Create sample prompts file
        prompts_file = output_dir / "sample_prompts.txt"
        
        with open(prompts_file, 'w', encoding='utf-8') as f:
            if prompts:
                for prompt in prompts:
                    # Add dataset_name prefix if not already present
                    if not prompt.startswith(dataset_name):
                        full_prompt = f"{dataset_name}, {prompt}"
                    else:
                        full_prompt = prompt
                    f.write(f"{full_prompt}\n")
            else:
                f.write(f"{dataset_name}, a photo\n")
                f.write(f"{dataset_name}, portrait\n")
                f.write(f"{dataset_name}, high quality\n")
                
        # Return for progress display
        return prompts_file
        
    def prepare_dataset(self, source_path: str, dataset_name: str, 
                       repeats: int = 30, class_name: str = "person") -> dict:
        """
        Main function to prepare a complete dataset.
        
        Args:
            source_path: Path to source dataset
            dataset_name: Name of the dataset
            repeats: Number of repetitions for training
            class_name: Class name for the object
            
        Returns:
            Dictionary with paths to created directories and files
        """
        source_path = Path(source_path)
        
        # Show header in non-quiet mode
        if not self.quiet_mode:
            print_dataset_prep_header(dataset_name, str(source_path), repeats, class_name)
        
        try:
            steps = []
            
            # Step 1: Copy to input
            input_dir, copied_files = self.copy_to_input(source_path, dataset_name)
            valid_pairs = self.validate_source_dataset(source_path)
            steps.append({
                'number': '1',
                'task': 'Copying files to input directory',
                'status': '✓ Complete',
                'details': [
                    f'Found {len(valid_pairs)} valid image-text pairs',
                    f'Copied {copied_files} files'
                ]
            })
            
            # Step 2: Create output structure
            output_dir, img_dir, log_dir, model_dir = self.create_output_structure(dataset_name, repeats, class_name)
            steps.append({
                'number': '2',
                'task': 'Creating output directory structure',
                'status': '✓ Complete',
                'details': [
                    f'Training images: {repeats}_{dataset_name} {class_name}',
                    'Log directory created',
                    'Model directory created'
                ]
            })
            
            # Step 3: Generate sample prompts
            prompts_file = self.generate_sample_prompts(dataset_name)
            steps.append({
                'number': '3',
                'task': 'Generating sample prompts',
                'status': '✓ Complete',
                'details': ['Created sample_prompts.txt']
            })
            
            # Display progress table
            if not self.quiet_mode:
                print_dataset_prep_progress(steps)
            
            result = {
                'input_dir': str(input_dir),
                'output_dir': str(output_dir),
                'prompts_file': str(prompts_file),
                'dataset_name': dataset_name,
                'repeats': repeats,
                'class_name': class_name,
                'valid_pairs': len(valid_pairs)
            }
            
            return result
            
        except Exception as e:
            print(f"Error during dataset preparation: {e}")
            raise


def extract_dataset_name(source_path: str, quiet: bool = False) -> str:
    """
    Extract dataset name from source path.
    
    Args:
        source_path: Source dataset path
        
    Returns:
        Dataset name extracted from path
    """
    path = Path(source_path).resolve()
    
    # Remove trailing slash if present and get the final directory name
    # For /home/eqx/datasets/1/b09g13/ -> b09g13
    # For /home/eqx/datasets/1/b09g13 -> b09g13
    dataset_name = path.name
    
    # If the path ends with '/' and name is empty, get the parent name
    if not dataset_name:
        dataset_name = path.parent.name
    
    # Validate that we have a valid name
    if not dataset_name or dataset_name in ['/', '.', '..']:
        raise ValueError(f"Cannot extract valid dataset name from path: {source_path}")
    
    # Show extraction in table format (unless quiet)
    if not quiet:
        print_dataset_extraction(dataset_name, source_path)
    return dataset_name


def main():
    """Command line interface for dataset preparation."""
    parser = argparse.ArgumentParser(
        description="Prepare datasets for AutoTrainX training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dataset_preparation.py --source /home/eqx/datasets/1/dl4r0s4/
  python dataset_preparation.py --source /path/to/my_dataset --repeats 50 --class_name "character"
        """
    )
    
    parser.add_argument(
        '--source', '-s',
        type=str,
        required=True,
        help='Source dataset path containing image-text pairs'
    )
    
    
    parser.add_argument(
        '--repeats', '-r',
        type=int,
        default=30,
        help='Number of repetitions for training (default: 30)'
    )
    
    parser.add_argument(
        '--class_name', '-c',
        type=str,
        default="person",
        help='Class name for the object (default: "person")'
    )
    
    parser.add_argument(
        '--base_path', '-b',
        type=str,
        default=Config.get_default_base_path(),
        help=f'Base path for AutoTrainX project (default: auto-detected or AUTOTRAINX_BASE_PATH env var)'
    )
    
    args = parser.parse_args()
    
    # Extract dataset name from source path
    dataset_name = extract_dataset_name(args.source, quiet=False)
    
    # Initialize preparator
    preparator = DatasetPreparator(args.base_path)
    
    try:
        # Prepare dataset
        result = preparator.prepare_dataset(
            source_path=args.source,
            dataset_name=dataset_name,
            repeats=args.repeats,
            class_name=args.class_name
        )
        
        # Display summary table
        summary_data = {
            'Dataset Name': result['dataset_name'],
            'Input Directory': result['input_dir'],
            'Output Directory': result['output_dir'],
            'Sample Prompts': result['prompts_file'],
            'Training Config': f"{result['repeats']} repeats, class '{result['class_name']}'"
        }
        print_summary_table(summary_data)
        
    except Exception as e:
        print(f"Failed to prepare dataset: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())