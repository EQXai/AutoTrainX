"""Enhanced SD-Scripts training module with progress monitoring."""

import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Optional, List, Tuple
import logging
import toml
from datetime import datetime

from ..scripts.preset_manager import PresetInfo
from .minimal_progress_monitor import MinimalProgressMonitor as ProgressMonitor, TrainingProgressTracker
from ..config import Config
from ..utils.job_tracker import get_tracker
from ..database import ExecutionStatus

logger = logging.getLogger(__name__)


class EnhancedSDScriptsTrainer:
    """Enhanced trainer with progress monitoring for sd-scripts."""
    
    def __init__(self, base_path: Path, show_progress: bool = True, progress_display_mode: str = "line"):
        """
        Initialize enhanced trainer.
        
        Args:
            base_path: Base project path
            show_progress: Whether to show progress bar (True) or raw logs (False)
            progress_display_mode: Display mode for progress ("line" or "box")
        """
        self.base_path = base_path
        self.sd_scripts_path = base_path / "sd-scripts"
        self.show_progress = show_progress
        self.progress_display_mode = progress_display_mode
        self.progress_tracker = TrainingProgressTracker()
        
    def execute_training(self, toml_path: Path, preset_info: PresetInfo, dataset_name: str, 
                       job_id: Optional[str] = None, mode: str = "single", 
                       current: int = 1, total: int = 1, 
                       experiment_name: Optional[str] = None,
                       variation_params: Optional[str] = None) -> bool:
        """
        Execute training with progress monitoring.
        
        Args:
            toml_path: Path to the TOML configuration file
            preset_info: PresetInfo object containing training script and args
            dataset_name: Name of the dataset being trained
            job_id: Optional job ID for tracking
            mode: Execution mode ("single", "batch", "variations")
            current: Current dataset/variation number
            total: Total number of datasets/variations
            experiment_name: Name of the experiment (for variations mode)
            variation_params: Current variation parameters (for variations mode)
            
        Returns:
            bool: True if training completed successfully, False otherwise
        """
        if not toml_path.exists():
            logger.error(f"TOML configuration not found: {toml_path}")
            return False
        
        # Get tracker instance
        tracker = get_tracker()
        
        # If no job_id provided, try to extract from TOML config
        if not job_id:
            try:
                with open(toml_path, 'r') as f:
                    config = toml.load(f)
                    job_id = config.get('job_id')
            except Exception as e:
                logger.warning(f"Could not extract job_id from config: {e}")
        
        # Extract total steps from config if available
        total_steps = None
        try:
            with open(toml_path, 'r') as f:
                config = toml.load(f)
                total_steps = config.get('max_train_steps')
        except Exception:
            pass
            
        # Construct the training command
        command = self._get_training_command(preset_info, toml_path)
        
        # Import the dashboard formatter
        from ..pipeline.utils.shared_pipeline_utils import format_training_dashboard
        
        # Display training information in dashboard format
        dashboard = format_training_dashboard(
            dataset_name=dataset_name,
            preset_name=preset_info.name,
            training_script=preset_info.training_script,
            config_file=str(toml_path),
            job_id=job_id or "N/A",
            command=command,
            mode=mode,
            current=current,
            total=total,
            experiment_name=experiment_name,
            variation_params=variation_params
        )
        print(dashboard)
        
        # Only log minimal info for log files (detailed info is in dashboard)
        logger.debug(f"Starting training for dataset: {dataset_name} with preset: {preset_info.name}")
        logger.debug(f"Command: {' '.join(command)}")
        
        # Update status to TRAINING
        if job_id:
            tracker.update_status(job_id, ExecutionStatus.TRAINING)
            if total_steps:
                # Update total steps if we found it
                from ..database import DatabaseManager
                from ..utils.quiet_mode import quiet_database_operations
                with quiet_database_operations():
                    db = DatabaseManager()
                with db.get_session() as session:
                    from ..database.models import Execution, Variation
                    # Try both tables
                    record = session.query(Execution).filter_by(job_id=job_id).first()
                    if not record:
                        record = session.query(Variation).filter_by(job_id=job_id).first()
                    if record:
                        record.total_steps = total_steps
                        session.commit()
        
        # Choose execution method based on show_progress setting
        if self.show_progress:
            return self._execute_with_progress(command, dataset_name, preset_info, toml_path, job_id,
                                             mode, experiment_name, variation_params)
        else:
            return self._execute_with_raw_output(command, dataset_name, preset_info, toml_path, job_id,
                                               mode, experiment_name, variation_params)
            
    def _execute_with_progress(self, command: List[str], dataset_name: str, 
                              preset_info: PresetInfo, toml_path: Path, job_id: Optional[str] = None,
                              mode: str = "single", experiment_name: Optional[str] = None,
                              variation_params: Optional[str] = None) -> bool:
        """Execute training with progress monitoring."""
        # Create progress monitor with configured display mode
        monitor = self.progress_tracker.create_monitor(dataset_name, preset_info.name)
        monitor.set_display_mode(self.progress_display_mode)
        
        # Track training start time
        start_time = time.time()
        
        try:
            # Set environment to suppress warnings
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore::FutureWarning,ignore::DeprecationWarning'
            
            # Execute the training process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=str(self.base_path),
                env=env
            )
            
            # Create train_log directory and prepare log file
            train_log_dir = self.base_path / "logs" / "train_log"
            train_log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create log filename with timestamp and dataset info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_dataset_name = dataset_name.replace("/", "_").replace(" ", "_")
            log_filename = f"train_{safe_dataset_name}_{timestamp}_{job_id or 'no_job_id'}.log"
            log_file_path = train_log_dir / log_filename
            
            # Open log file for writing
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                # Write header information
                log_file.write(f"# AutoTrainX Training Log\n")
                log_file.write(f"# Dataset: {dataset_name}\n")
                log_file.write(f"# Preset: {preset_info.name}\n")
                log_file.write(f"# Job ID: {job_id or 'N/A'}\n")
                log_file.write(f"# Start Time: {datetime.now().isoformat()}\n")
                log_file.write(f"# Mode: {mode}\n")
                if experiment_name:
                    log_file.write(f"# Experiment: {experiment_name}\n")
                if variation_params:
                    log_file.write(f"# Variation: {variation_params}\n")
                log_file.write(f"# Command: {' '.join(command)}\n")
                log_file.write("=" * 80 + "\n\n")
                log_file.flush()
            
                # Process output lines
                output_lines = []
                
                for line in process.stdout:
                    # Write to log file
                    log_file.write(line)
                    log_file.flush()
                    
                    # Store line for potential debugging
                    output_lines.append(line.strip())
                    
                    # Parse the line to update state
                    monitor.parse_line(line)
                    
                    # Update display
                    monitor.display()
                    
                    # Only show actual errors (not warnings)
                    if "error" in line.lower() and "warning" not in line.lower():
                        # Skip certain non-critical error messages
                        if not any(skip in line.lower() for skip in ["futurewarn", "deprecat"]):
                            print(f"\n❌ {line.strip()}\n")
                    
                # Wait for process to complete
                return_code = process.wait()
            
            # Update final state
            if return_code == 0:
                monitor.state.phase = "completed"
            else:
                monitor.state.phase = "failed"
                
            # Final display update
            monitor.display(force=True)
                
            # Calculate duration
            duration = time.time() - start_time
            duration_str = self._format_duration(duration)
            
            if return_code == 0:
                logger.info(f"Training completed for dataset: {dataset_name}")
                self._print_training_summary(dataset_name, preset_info.name, duration_str, toml_path)
                # Note: Don't update to DONE here - that's handled by the pipeline
                return True
            else:
                logger.error(f"Training failed with return code: {return_code}")
                # Update tracker with failure
                if job_id:
                    tracker = get_tracker()
                    tracker.update_status(job_id, ExecutionStatus.FAILED, 
                                        error_message=f"Training failed with return code: {return_code}")
                # Print last few lines of output for debugging
                print("\nLast output lines:")
                for line in output_lines[-10:]:
                    print(f"  {line}")
                return False
                
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            if job_id:
                tracker = get_tracker()
                tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=str(e))
            return False
            
    def _execute_with_raw_output(self, command: List[str], dataset_name: str,
                                preset_info: PresetInfo, toml_path: Path, job_id: Optional[str] = None,
                                mode: str = "single", experiment_name: Optional[str] = None,
                                variation_params: Optional[str] = None) -> bool:
        """Execute training with raw output (original behavior)."""
        # Track training start time
        start_time = time.time()
        
        try:
            # Set environment to suppress warnings
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore::FutureWarning,ignore::DeprecationWarning'
            
            # Execute the training process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=str(self.base_path),
                env=env
            )
            
            # Create train_log directory and prepare log file
            train_log_dir = self.base_path / "logs" / "train_log"
            train_log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create log filename with timestamp and dataset info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_dataset_name = dataset_name.replace("/", "_").replace(" ", "_")
            log_filename = f"train_{safe_dataset_name}_{timestamp}_{job_id or 'no_job_id'}.log"
            log_file_path = train_log_dir / log_filename
            
            # Open log file for writing
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                # Write header information
                log_file.write(f"# AutoTrainX Training Log\n")
                log_file.write(f"# Dataset: {dataset_name}\n")
                log_file.write(f"# Preset: {preset_info.name}\n")
                log_file.write(f"# Job ID: {job_id or 'N/A'}\n")
                log_file.write(f"# Start Time: {datetime.now().isoformat()}\n")
                log_file.write(f"# Command: {' '.join(command)}\n")
                log_file.write("=" * 80 + "\n\n")
                log_file.flush()
            
                # Stream output in real-time and parse for progress
                import re
                step_pattern = re.compile(r'steps:\s*(\d+)/(\d+)')
                epoch_pattern = re.compile(r'epoch\s+(\d+)/(\d+)', re.IGNORECASE)
                
                for line in process.stdout:
                    # Write to log file
                    log_file.write(line)
                    log_file.flush()
                    
                    print(line, end='')
                    
                    # Try to extract progress information
                    if job_id:
                        # Check for step progress
                        step_match = step_pattern.search(line)
                        if step_match:
                            current_step = int(step_match.group(1))
                            # Progress tracking removed - using total_steps in config instead
                
                # Wait for process to complete
                return_code = process.wait()
            
            # Calculate duration
            duration = time.time() - start_time
            duration_str = self._format_duration(duration)
            
            if return_code == 0:
                logger.info(f"Training completed for dataset: {dataset_name}")
                self._print_training_summary(dataset_name, preset_info.name, duration_str, toml_path)
                # Note: Don't update to DONE here - that's handled by the pipeline
                return True
            else:
                logger.error(f"Training failed with return code: {return_code}")
                if job_id:
                    tracker = get_tracker()
                    tracker.update_status(job_id, ExecutionStatus.FAILED, 
                                        error_message=f"Training failed with return code: {return_code}")
                return False
                
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            if job_id:
                tracker = get_tracker()
                tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=str(e))
            return False
            
    def _get_training_command(self, preset_info: PresetInfo, toml_path: Path) -> List[str]:
        """
        Construct the training command with all arguments.
        
        Args:
            preset_info: PresetInfo containing script and default args
            toml_path: Path to TOML configuration
            
        Returns:
            List of command arguments
        """
        # Base command
        script_path = self.sd_scripts_path / preset_info.training_script
        command = [sys.executable, str(script_path), "--config_file", str(toml_path)]
        
        # Add default arguments if any
        if preset_info.default_args:
            command.extend(preset_info.default_args)
            
        return command
        
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
            
    def _print_training_summary(self, dataset_name: str, preset_name: str, 
                               duration: str, toml_path: Path, log_file_path: Optional[Path] = None) -> None:
        """Print training summary."""
        output_dir = self.base_path / "workspace" / "output" / dataset_name
        model_dir = output_dir / "model"
        log_dir = output_dir / "log"
        
        # Find the generated model file
        model_files = list(model_dir.glob("*.safetensors")) if model_dir.exists() else []
        model_path = model_files[0] if model_files else "Model not found"
        
        # Print training summary
        print("\n" + "=" * 80)
        print(f"{'TRAINING SUMMARY':^80}")
        print("=" * 80)
        print(f"Dataset:      {dataset_name}")
        print(f"Preset:       {preset_name}")
        print(f"Duration:     {duration}")
        
        if isinstance(model_path, Path):
            print(f"Output Model: {model_path}")
            
        print(f"Training logs: {log_dir}")
        
        # Also show train log path if available
        if log_file_path:
            print(f"\nTraining process log saved to:")
            print(f"  {log_file_path}")
        
        print("=" * 80 + "\n")
        
    def display_all_progress(self) -> None:
        """Display progress summary for all training sessions."""
        self.progress_tracker.display_summary()


# Factory function to get appropriate trainer
def get_trainer(base_path: Path, show_progress: Optional[bool] = None) -> 'SDScriptsTrainer':
    """
    Get appropriate trainer instance based on configuration.
    
    Args:
        base_path: Base project path
        show_progress: Whether to show progress bar. If None, reads from config.
        
    Returns:
        Either EnhancedSDScriptsTrainer or original SDScriptsTrainer
    """
    # If not specified, check config
    if show_progress is None:
        from ..config import Config
        show_progress = Config.get_training_progress_setting(str(base_path))
            
    # Always return enhanced trainer, but it can show raw output if needed
    return EnhancedSDScriptsTrainer(base_path, show_progress)