"""SD-Scripts training module."""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
from typing import Optional, List, Tuple
import logging
import toml
from datetime import datetime

from ..scripts.preset_manager import PresetInfo
from ..utils.job_tracker import get_tracker
from ..database import ExecutionStatus
from ..utils.signal_handler import get_shutdown_handler
from ..utils.path_manager import PathManager
from ..config import Config
from ..pipeline.utils.shared_pipeline_utils import ColoredOutput

logger = logging.getLogger(__name__)


class SDScriptsTrainer:
    """Handles training execution using sd-scripts."""
    
    def __init__(self, base_path: Path):
        """Initialize trainer with base project path."""
        self.base_path = base_path
        self.sd_scripts_path = base_path / "sd-scripts"
        
        # Check if custom path is configured
        custom_path = Config.get_custom_output_path(str(base_path))
        if custom_path:
            self.path_manager = PathManager(str(base_path), custom_path)
        else:
            self.path_manager = None
        
    def execute_training(self, toml_path: Path, preset_info: PresetInfo, dataset_name: str, 
                       job_id: Optional[str] = None, mode: str = "single", 
                       current: int = 1, total: int = 1, 
                       experiment_name: Optional[str] = None,
                       variation_params: Optional[str] = None) -> bool:
        """
        Execute training with sd-scripts.
        
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
        
        # Get tracker and shutdown handler instances
        tracker = get_tracker()
        shutdown_handler = get_shutdown_handler()
        
        # If no job_id provided, try to extract from TOML config
        if not job_id:
            try:
                with open(toml_path, 'r') as f:
                    config = toml.load(f)
                    job_id = config.get('job_id')
            except Exception as e:
                logger.warning(f"Could not extract job_id from config: {e}")
        
        # If still no job_id, generate one for tracking purposes
        if not job_id:
            from ..utils.job_id import generate_job_id
            job_id = generate_job_id()
            logger.info(f"Generated job_id for tracking: {job_id}")
        
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
        
        # Check if we should use signal isolation wrapper
        # Note: Signal isolation can prevent proper SIGINT handling
        use_isolation = os.environ.get('AUTOTRAINX_USE_ISOLATION', 'true').lower() == 'true'
        
        if use_isolation:
            logger.warning("Signal isolation is enabled. This may prevent proper Ctrl+C handling.")
            logger.info("To improve Ctrl+C handling, set AUTOTRAINX_USE_ISOLATION=false")
        if use_isolation and sys.platform != "win32":
            # Check if setsid command is available (most Unix systems)
            try:
                setsid_result = subprocess.run(['which', 'setsid'], capture_output=True, text=True)
                if setsid_result.returncode == 0:
                    # Use setsid for complete process isolation
                    command = ['setsid'] + command
                    logger.debug("Using setsid for complete process isolation")
                else:
                    # Use shell wrapper as fallback
                    shell_wrapper = Path(__file__).parent / "run_isolated.sh"
                    if shell_wrapper.exists():
                        command = [str(shell_wrapper)] + command
                        logger.debug("Using shell wrapper for signal isolation")
                    else:
                        # Final fallback to Python wrapper
                        wrapper_path = Path(__file__).parent / "subprocess_wrapper.py"
                        if wrapper_path.exists():
                            command = [sys.executable, str(wrapper_path)] + command
                            logger.debug("Using Python wrapper for signal isolation")
            except:
                # If which command fails, try shell wrapper
                shell_wrapper = Path(__file__).parent / "run_isolated.sh"
                if shell_wrapper.exists():
                    command = [str(shell_wrapper)] + command
                    logger.debug("Using shell wrapper for signal isolation")
        
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
        
        # Update status to TRAINING and set current job info
        if job_id:
            tracker.update_status(job_id, ExecutionStatus.TRAINING)
            # Set current job info for signal handler
            logger.info(f"Setting current job in shutdown handler: {job_id} at {id(shutdown_handler)}")
            shutdown_handler.set_current_job(job_id, dataset_name, preset_info.name, mode)
            
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
        
        # Track training start time
        start_time = time.time()
        
        try:
            # Execute the training process with signal isolation
            import os
            import signal
            
            # On Unix-like systems, we'll handle signals more robustly
            if sys.platform != "win32":
                # Store the PID for the signal handler before starting
                pid_file = self.base_path / f".training_pid_{job_id or 'temp'}.pid"
                
                # Check if we're already using external isolation (setsid command or wrapper)
                using_external_isolation = any(cmd in str(command[0]) for cmd in ['setsid', 'run_isolated.sh', 'subprocess_wrapper.py'])
                
                if using_external_isolation:
                    # Don't use preexec_fn if we're using external isolation
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                        cwd=str(self.base_path)
                    )
                else:
                    # Use internal isolation
                    def preexec_function():
                        """Pre-execution function to set up subprocess signal handling."""
                        # Create new session to completely detach from terminal
                        os.setsid()
                        # Reset all signal handlers to default to avoid inheritance issues
                        for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGQUIT]:
                            signal.signal(sig, signal.SIG_DFL)
                    
                    # Start the process with a clean environment
                    env = os.environ.copy()
                    # Tell subprocesses to ignore interrupts
                    env['PYTHONUNBUFFERED'] = '1'
                    
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1,
                        cwd=str(self.base_path),
                        preexec_fn=preexec_function,
                        env=env,
                        # Start in background, detached from terminal
                        start_new_session=True
                    )
                
                # Write PID to file for emergency cleanup
                try:
                    pid_file.write_text(str(process.pid))
                except:
                    pass
            else:
                # Windows
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    cwd=str(self.base_path),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
            
            # Register subprocess with shutdown handler
            shutdown_handler.add_subprocess(process)
            
            # Initialize heartbeat writer if job_id is available
            heartbeat_writer = None
            if job_id:
                from ..database.process_monitor import HeartbeatWriter
                heartbeat_writer = HeartbeatWriter(job_id, self.base_path)
                heartbeat_writer.write_heartbeat(force=True)  # Initial heartbeat
            
            # Create train_log directory and prepare log file
            train_log_dir = self.base_path / "logs" / "train_log"
            train_log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created train_log directory: {train_log_dir}")
            
            # Create log filename with timestamp and dataset info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_dataset_name = dataset_name.replace("/", "_").replace(" ", "_")
            log_filename = f"train_{safe_dataset_name}_{timestamp}_{job_id or 'no_job_id'}.log"
            log_file_path = train_log_dir / log_filename
            
            # Open log file for writing
            logger.info(f"Opening log file for writing: {log_file_path}")
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
            
                # Stream output in real-time and parse for progress
                import re
                step_pattern = re.compile(r'steps:\s*(\d+)/(\d+)')
                epoch_pattern = re.compile(r'epoch\s+(\d+)/(\d+)', re.IGNORECASE)
                line_counter = 0
                
                for line in process.stdout:
                    print(line, end='')
                    log_file.write(line)
                    log_file.flush()  # Ensure immediate write to disk
                    line_counter += 1
                
                # Write heartbeat periodically
                if heartbeat_writer and line_counter % 50 == 0:  # Every 50 lines
                    heartbeat_writer.write_heartbeat()
                
                # Try to extract progress information
                if job_id:
                    # Check for step progress
                    step_match = step_pattern.search(line)
                    if step_match:
                        current_step = int(step_match.group(1))
                        total = int(step_match.group(2))
                        # Progress tracking removed - using total_steps in config instead
                    
                    # Check for epoch progress (fallback)
                    epoch_match = epoch_pattern.search(line)
                    if epoch_match and total_steps:
                        current_epoch = int(epoch_match.group(1))
                        total_epochs = int(epoch_match.group(2))
                        # Progress tracking removed - using total_steps in config instead
                
                # Wait for process to complete
                return_code = process.wait()
            
            # Remove subprocess from tracking
            shutdown_handler.remove_subprocess(process)
            
            # Only clear current job info if NOT interrupted
            # (return_code -2 or 130 indicate SIGINT)
            if return_code != -2 and return_code != 130:
                logger.info(f"Process completed normally with code {return_code}, clearing job info")
                shutdown_handler.clear_current_job()
            else:
                # For interrupted processes, the signal handler needs the job info
                logger.info(f"Process interrupted (code {return_code}), preserving job info: {job_id}")
                logger.info(f"Current handler state - job_id: {shutdown_handler.current_job_id}")
            
            # Clean up process files if they exist
            if sys.platform != "win32" and 'pid_file' in locals():
                try:
                    pid_file.unlink(missing_ok=True)
                except:
                    pass
            
            # Clean up heartbeat file
            if heartbeat_writer:
                heartbeat_writer.cleanup()
            
            # Calculate duration
            duration = time.time() - start_time
            duration_str = self._format_duration(duration)
            
            if return_code == 0:
                logger.info(f"Training completed for dataset: {dataset_name}")
                logger.info(f"Training log saved to: {log_file_path}")
                self._print_training_summary(dataset_name, preset_info.name, duration_str, toml_path, job_id, log_file_path)
                
                # Note: Don't update to DONE here - that's handled by the pipeline
                # after post-processing (preview generation, etc.)
                
                # Save metadata if using custom paths
                if self.path_manager and self.path_manager.is_custom_mode:
                    metadata = {
                        "dataset_name": dataset_name,
                        "preset_name": preset_info.name,
                        "job_id": job_id,
                        "mode": mode,
                        "toml_path": str(toml_path),
                        "training_completed": True,
                        "experiment_name": experiment_name,
                        "variation_params": variation_params
                    }
                    self.path_manager.save_training_metadata(dataset_name, metadata)
                
                return True
            elif return_code == -2 or return_code == 130:  # -2 or 130 indicate SIGINT
                # SIGINT received - this means the process was interrupted
                logger.info(f"Training interrupted for dataset: {dataset_name} (return code: {return_code})")
                
                # Log diagnostic information
                logger.debug(f"Command used: {' '.join(command[:3])}...")  # Log first 3 parts of command
                logger.debug(f"Signal isolation was {'enabled' if use_isolation else 'disabled'}")
                
                if job_id:
                    # Check if the job was already marked as cancelled by signal handler
                    from ..database import DatabaseManager
                    from ..utils.quiet_mode import quiet_database_operations
                    with quiet_database_operations():
                        db = DatabaseManager()
                    with db.get_session() as session:
                        from ..database.models import Execution, Variation
                        record = session.query(Execution).filter_by(job_id=job_id).first()
                        if not record:
                            record = session.query(Variation).filter_by(job_id=job_id).first()
                        
                        if record and record.status != ExecutionStatus.CANCELLED.value:
                            # Not marked as cancelled, so this was an unexpected interrupt
                            error_msg = (
                                f"Training interrupted (SIGINT). This may indicate that signal isolation "
                                f"is not working properly. Try setting AUTOTRAINX_USE_ISOLATION=false "
                                f"if this persists."
                            )
                            tracker.update_status(job_id, ExecutionStatus.FAILED, error_message=error_msg)
                return False
            else:
                logger.error(f"Training failed with return code: {return_code}")
                if job_id:
                    tracker.update_status(job_id, ExecutionStatus.FAILED, 
                                        error_message=f"Training failed with return code: {return_code}")
                return False
                
        except Exception as e:
            logger.error(f"Training error: {str(e)}")
            # Ensure cleanup even on exception
            if 'process' in locals():
                shutdown_handler.remove_subprocess(process)
            
            # For exceptions, we should clear the job info since it's not a clean shutdown
            shutdown_handler.clear_current_job()
            
            # Clean up process files if they exist
            if sys.platform != "win32" and 'pid_file' in locals():
                try:
                    pid_file.unlink(missing_ok=True)
                except:
                    pass
            
            # Clean up heartbeat file
            if 'heartbeat_writer' in locals() and heartbeat_writer:
                heartbeat_writer.cleanup()
            
            if job_id:
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
                               duration: str, toml_path: Path, job_id: Optional[str] = None,
                               train_log_path: Optional[Path] = None) -> None:
        """Print training summary."""
        # Determine output directories based on configuration
        if self.path_manager:
            output_dir = self.path_manager.get_output_path(dataset_name)
            model_dir = self.path_manager.get_model_output_path(dataset_name)
            log_dir = self.path_manager.get_log_output_path(dataset_name)
        else:
            output_dir = self.base_path / "workspace" / "output" / dataset_name
            model_dir = output_dir / "model"
            log_dir = output_dir / "log"
        
        # Find the generated model file
        model_files = list(model_dir.glob("*.safetensors")) if model_dir.exists() else []
        model_path = str(model_files[0]) if model_files else "Model not found"
        
        # Find log file
        log_files = list(log_dir.glob("*.txt")) if log_dir.exists() else []
        log_path = str(log_files[0]) if log_files else str(log_dir)
        
        # Import and use the summary dashboard formatter
        from ..pipeline.utils.shared_pipeline_utils import format_training_summary_dashboard
        
        summary = format_training_summary_dashboard(
            dataset_name=dataset_name,
            preset_name=preset_name,
            duration=duration,
            model_path=model_path,
            log_path=log_path,
            job_id=job_id
        )
        print(summary)
        
        # Also show train log path if available
        if train_log_path:
            print(f"\n{ColoredOutput.CYAN}Training process log saved to:{ColoredOutput.RESET}")
            print(f"  {train_log_path}")