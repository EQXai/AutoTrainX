"""
File move hook for moving training outputs to custom profile locations.

This hook is executed after successful training to move generated files
from the default workspace locations to custom profile paths.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from datetime import datetime

from .base import PipelineHook, HookType
from ...utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class FileMoveHook(PipelineHook):
    """
    Hook for moving training outputs to custom profile locations.
    
    This hook only activates when:
    1. A custom (non-default) profile is active
    2. Training has completed successfully
    3. Files exist in the expected locations
    """
    
    def __init__(self, path_manager: Optional[PathManager] = None):
        """
        Initialize file move hook.
        
        Args:
            path_manager: PathManager instance with custom profile configuration
        """
        super().__init__(enabled=True)
        self.path_manager = path_manager
        self.move_manager = FileMoveManager()
        
    @property
    def hook_type(self) -> HookType:
        """This is a post-training hook."""
        return HookType.POST_TRAINING
        
    @property
    def name(self) -> str:
        """Return the name of this hook."""
        return "FileMoveHook"
        
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """
        Determine if files should be moved.
        
        Files are only moved when:
        1. PathManager is configured with custom output path
        2. Training was successful
        3. We're not in dry-run mode
        """
        # Check if we have a custom path configured
        if not self.path_manager or not self.path_manager.is_custom_mode:
            logger.info("File move hook skipped: no custom profile active")
            return False
            
        # Check if training was successful
        if not context.get('success', False):
            logger.info("File move hook skipped: training was not successful")
            return False
            
        # Check if we're in dry-run mode
        if context.get('dry_run', False):
            logger.info("File move hook skipped: dry-run mode")
            return False
            
        logger.info(f"File move hook will execute for mode: {context.get('mode', 'unknown')}, dataset: {context.get('dataset_name', 'unknown')}")
        return True
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute file moving based on context.
        
        Args:
            context: Execution context with training results
            
        Returns:
            Results of file moving operations
        """
        try:
            mode = context.get('mode', 'single')
            dataset_results = context.get('dataset_results', [])
            preview_enabled = context.get('preview_count', 0) > 0
            
            # Debug logging
            logger.info(f"FileMoveHook execute - mode: {mode}")
            logger.info(f"FileMoveHook execute - context keys: {list(context.keys())}")
            if mode == 'variations':
                logger.info(f"Variations context - dataset_name: {context.get('dataset_name')}")
                logger.info(f"Variations context - variation_id: {context.get('variation_id')}")
                logger.info(f"Variations context - experiment_name: {context.get('experiment_name')}")
            
            if mode == 'single':
                # Single mode - one dataset
                dataset_name = context.get('dataset_name')
                if not dataset_name:
                    logger.error("No dataset_name in context for single mode")
                    return {'file_move_results': []}
                    
                results = [self._move_single_dataset(
                    dataset_name=dataset_name,
                    context=context,
                    preview_enabled=preview_enabled
                )]
                
            elif mode == 'batch':
                # Batch mode - check if we have dataset_results or single dataset
                if dataset_results:
                    # Multiple datasets passed together
                    results = []
                    for dataset_result in dataset_results:
                        if dataset_result.get('success', False):
                            result = self._move_single_dataset(
                                dataset_name=dataset_result['dataset_name'],
                                context=dataset_result,
                                preview_enabled=preview_enabled
                            )
                            results.append(result)
                else:
                    # Single dataset in batch mode (called individually)
                    dataset_name = context.get('dataset_name')
                    if dataset_name:
                        results = [self._move_single_dataset(
                            dataset_name=dataset_name,
                            context=context,
                            preview_enabled=preview_enabled
                        )]
                    else:
                        logger.error("No dataset_name in context for batch mode")
                        return {'file_move_results': []}
                        
            elif mode == 'variations':
                # Variations mode - check if we have variation_results or single variation
                variation_results = context.get('variation_results', [])
                
                if variation_results:
                    # Multiple variations passed together
                    results = []
                    base_dataset = context.get('dataset_name')
                    for var_result in variation_results:
                        if var_result.get('success', False):
                            variation_name = var_result.get('variation_name')
                            result = self._move_variation_dataset(
                                base_dataset=base_dataset,
                                variation_name=variation_name,
                                variation_id=var_result.get('variation_id'),
                                context=var_result,
                                preview_enabled=preview_enabled
                            )
                            results.append(result)
                else:
                    # Single variation (called individually)
                    variation_name = context.get('dataset_name')
                    variation_id = context.get('variation_id')
                    experiment_name = context.get('experiment_name')
                    
                    # Try to extract variation_id from experiment_name if not provided
                    if not variation_id and experiment_name and '_v' in experiment_name:
                        # Extract variation number from name like "dataset_FluxLORA_v4"
                        try:
                            parts = experiment_name.split('_v')
                            if len(parts) > 1 and parts[-1].isdigit():
                                variation_id = f"var_{parts[-1]}"
                        except:
                            pass
                    
                    if variation_name:
                        # Even without variation_id, we can still move files
                        if not variation_id:
                            logger.warning(f"No variation_id provided, using default naming for {variation_name}")
                            # Generate a simple variation_id based on timestamp
                            from datetime import datetime
                            variation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        results = [self._move_variation_dataset(
                            base_dataset=variation_name.split('_')[0],  # Extract base dataset from variation name
                            variation_name=variation_name,
                            variation_id=variation_id,
                            context=context,
                            preview_enabled=preview_enabled
                        )]
                    else:
                        logger.error("No dataset_name in context for variations mode")
                        return {'file_move_results': []}
                        
            else:
                logger.warning(f"Unknown mode for file move: {mode}")
                results = []
                
            return {
                'file_move_results': results,
                'file_move_summary': self._create_summary(results)
            }
            
        except Exception as e:
            logger.error(f"File move hook failed: {e}")
            return {
                'file_move_results': [],
                'file_move_error': str(e)
            }
            
    def _move_single_dataset(self, dataset_name: str, context: Dict[str, Any], 
                           preview_enabled: bool) -> Dict[str, Any]:
        """Move files for a single dataset."""
        try:
            # Get source paths
            source_base = self.path_manager.get_workspace_path() / "output" / dataset_name
            model_dir = source_base / "model"
            preview_dir = source_base / "Preview" if preview_enabled else None
            
            # Find model file
            model_file = self._find_latest_model(model_dir)
            if not model_file:
                return {
                    'dataset_name': dataset_name,
                    'success': False,
                    'error': 'No model file found'
                }
                
            # Find config file
            config_file = self._find_config_file(dataset_name, context)
            
            # Get destination path
            model_name = model_file.stem
            dest_path = Path(self.path_manager.custom_output_path) / model_name
            
            # Move files
            moved_files = self.move_manager.move_training_files(
                model_file=model_file,
                config_file=config_file,
                preview_dir=preview_dir,
                destination=dest_path
            )
            
            return {
                'dataset_name': dataset_name,
                'model_name': model_name,
                'destination': str(dest_path),
                'success': True,
                'moved_files': moved_files
            }
            
        except Exception as e:
            logger.error(f"Failed to move files for {dataset_name}: {e}")
            return {
                'dataset_name': dataset_name,
                'success': False,
                'error': str(e)
            }
            
    def _move_variation_dataset(self, base_dataset: str, variation_name: str,
                              variation_id: str, context: Dict[str, Any],
                              preview_enabled: bool) -> Dict[str, Any]:
        """Move files for a variation dataset."""
        try:
            # Try multiple possible source paths for variations
            possible_paths = [
                # Standard variations path
                self.path_manager.get_workspace_path() / "variations" / f"exp_{variation_id}" / variation_name,
                # Alternative: output path (if variations are stored like regular outputs)
                self.path_manager.get_workspace_path() / "output" / variation_name,
                # Alternative: direct variation path
                self.path_manager.get_workspace_path() / "variations" / variation_name
            ]
            
            source_base = None
            model_dir = None
            
            # Find which path exists
            for path in possible_paths:
                if path.exists():
                    test_model_dir = path / "model"
                    if test_model_dir.exists():
                        source_base = path
                        model_dir = test_model_dir
                        logger.info(f"Found variation files at: {source_base}")
                        break
            
            if not source_base or not model_dir:
                logger.error(f"Could not find variation files. Searched paths: {[str(p) for p in possible_paths]}")
                return {
                    'dataset_name': variation_name,
                    'success': False,
                    'error': f'Variation files not found in any expected location'
                }
            
            preview_dir = source_base / "Preview" if preview_enabled else None
            
            # Find model file
            model_file = self._find_latest_model(model_dir)
            if not model_file:
                return {
                    'dataset_name': variation_name,
                    'success': False,
                    'error': f'No model file found in {model_dir}'
                }
                
            # Find config file for variation
            config_file = self._find_variation_config(variation_name, variation_id)
            
            # Get destination path
            model_name = model_file.stem
            dest_path = Path(self.path_manager.custom_output_path) / model_name
            
            # Move files
            moved_files = self.move_manager.move_training_files(
                model_file=model_file,
                config_file=config_file,
                preview_dir=preview_dir,
                destination=dest_path
            )
            
            return {
                'dataset_name': variation_name,
                'model_name': model_name,
                'destination': str(dest_path),
                'success': True,
                'moved_files': moved_files,
                'variation_id': variation_id
            }
            
        except Exception as e:
            logger.error(f"Failed to move files for variation {variation_name}: {e}")
            return {
                'dataset_name': variation_name,
                'success': False,
                'error': str(e),
                'variation_id': variation_id
            }
            
    def _find_latest_model(self, model_dir: Path) -> Optional[Path]:
        """Find the most recent .safetensors file in model directory."""
        if not model_dir.exists():
            return None
            
        model_files = list(model_dir.glob("*.safetensors"))
        if not model_files:
            return None
            
        # Return most recent file
        return max(model_files, key=lambda p: p.stat().st_mtime)
        
    def _find_config_file(self, dataset_name: str, context: Dict[str, Any]) -> Optional[Path]:
        """Find the TOML config file used for training."""
        preset = context.get('preset', '')
        
        # First check workspace/Presets
        config_path = (self.path_manager.get_workspace_path() / 
                      "Presets" / preset / f"{dataset_name}_{preset}.toml")
        if config_path.exists():
            return config_path
            
        # Check custom config location if applicable
        if self.path_manager.is_custom_mode:
            custom_config = (self.path_manager.get_output_path(dataset_name) / 
                           "config" / f"{dataset_name}_{preset}.toml")
            if custom_config.exists():
                return custom_config
                
        return None
        
    def _find_variation_config(self, variation_name: str, variation_id: str) -> Optional[Path]:
        """Find config file for a variation."""
        # Try multiple possible config locations
        possible_configs = [
            # In variations directory
            self.path_manager.get_workspace_path() / "variations" / f"exp_{variation_id}" / variation_name / f"{variation_name}.toml",
            # In workspace/Presets
            self.path_manager.get_workspace_path() / "Presets" / f"{variation_name}.toml",
        ]
        
        # If we can extract preset name, check preset-specific location
        parts = variation_name.split('_')
        if len(parts) >= 2:
            # Try to find preset name (usually second to last part before version)
            for i in range(len(parts)-1, 0, -1):
                potential_preset = parts[i]
                config_path = self.path_manager.get_workspace_path() / "Presets" / potential_preset / f"{variation_name}.toml"
                possible_configs.append(config_path)
        
        # Check each possible location
        for config_path in possible_configs:
            if config_path.exists():
                logger.info(f"Found variation config at: {config_path}")
                return config_path
        
        logger.warning(f"Could not find config for variation {variation_name}. Searched: {[str(p) for p in possible_configs]}")
        return None
        
    def _create_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of file move operations."""
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = total - successful
        
        return {
            'total_datasets': total,
            'successful_moves': successful,
            'failed_moves': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "0%"
        }


class FileMoveManager:
    """Handles the actual file moving operations with error handling."""
    
    def move_training_files(self, model_file: Path, config_file: Optional[Path],
                          preview_dir: Optional[Path], destination: Path) -> Dict[str, Any]:
        """
        Move training files to destination with atomic operations.
        
        Args:
            model_file: Path to .safetensors model
            config_file: Path to .toml config (optional)
            preview_dir: Path to Preview directory (optional)
            destination: Destination directory
            
        Returns:
            Dictionary with moved file information
        """
        moved_files = {
            'models': [],
            'configs': [],
            'previews': []
        }
        
        # Create destination directory
        destination.mkdir(parents=True, exist_ok=True)
        
        # Track operations for rollback
        operations = []
        
        try:
            # Move model file
            if model_file and model_file.exists():
                dest_model = destination / model_file.name
                # Get size before moving
                size = model_file.stat().st_size
                logger.info(f"Moving model: {model_file} -> {dest_model}")
                shutil.move(str(model_file), str(dest_model))
                operations.append(('move', dest_model, model_file))
                moved_files['models'].append({
                    'source': str(model_file),
                    'destination': str(dest_model),
                    'size': size
                })
                
            # Copy config file (don't move, as it might be shared)
            if config_file and config_file.exists():
                config_dir = destination / "config"
                config_dir.mkdir(exist_ok=True)
                dest_config = config_dir / config_file.name
                logger.info(f"Copying config: {config_file} -> {dest_config}")
                shutil.copy2(str(config_file), str(dest_config))
                operations.append(('copy', dest_config, None))
                moved_files['configs'].append({
                    'source': str(config_file),
                    'destination': str(dest_config),
                    'size': config_file.stat().st_size if config_file.exists() else 0
                })
                
            # Move preview directory
            if preview_dir and preview_dir.exists():
                dest_preview = destination / "Preview"
                logger.info(f"Moving preview dir: {preview_dir} -> {dest_preview}")
                
                # Count files in preview directory
                preview_files = list(preview_dir.glob("*.png"))
                file_count = len(preview_files)
                
                shutil.move(str(preview_dir), str(dest_preview))
                operations.append(('move', dest_preview, preview_dir))
                moved_files['previews'].append({
                    'source': str(preview_dir),
                    'destination': str(dest_preview),
                    'file_count': file_count
                })
                
            return moved_files
            
        except Exception as e:
            logger.error(f"Error during file move: {e}")
            # Rollback operations
            self._rollback_operations(operations)
            raise
            
    def _rollback_operations(self, operations: List[Tuple[str, Path, Optional[Path]]]):
        """Rollback file operations on error."""
        logger.info("Rolling back file operations due to error")
        
        for op_type, dest_path, source_path in reversed(operations):
            try:
                if op_type == 'move' and dest_path.exists():
                    # Move back to original location
                    if source_path:
                        logger.info(f"Rolling back move: {dest_path} -> {source_path}")
                        shutil.move(str(dest_path), str(source_path))
                elif op_type == 'copy' and dest_path.exists():
                    # Just delete the copy
                    logger.info(f"Rolling back copy: removing {dest_path}")
                    dest_path.unlink()
            except Exception as e:
                logger.error(f"Error during rollback of {dest_path}: {e}")