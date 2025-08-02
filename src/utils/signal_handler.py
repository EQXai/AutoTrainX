"""
Signal handler for graceful shutdown of AutoTrainX pipeline.

This module provides SIGINT (Ctrl+C) handling with:
- Confirmation prompt before exit
- Current process status display
- Cleanup of running processes
- ComfyUI shutdown
- Database status updates
"""

import signal
import sys
import time
import subprocess
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path
from datetime import datetime
import logging

from ..database import DatabaseManager, ExecutionStatus
from ..image_preview.utils import ComfyUIManager

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """Handles graceful shutdown when SIGINT (Ctrl+C) is received."""
    
    def __init__(self):
        """Initialize the shutdown handler."""
        self.active_processes: List[subprocess.Popen] = []
        self.current_job_id: Optional[str] = None
        self.current_dataset: Optional[str] = None
        self.current_preset: Optional[str] = None
        self.current_mode: Optional[str] = None
        self.comfyui_url: Optional[str] = None
        self.original_handler = None
        self._shutdown_requested = False
        self._in_handler = False
        
    def register(self):
        """Register the signal handler."""
        self.original_handler = signal.signal(signal.SIGINT, self._handle_sigint)
        logger.info(f"Registered graceful shutdown handler at {id(self)}")
        logger.debug("Registered graceful shutdown handler")
        
    def unregister(self):
        """Unregister the signal handler and restore original."""
        if self.original_handler is not None:
            signal.signal(signal.SIGINT, self.original_handler)
            logger.debug("Unregistered graceful shutdown handler")
            
    def set_current_job(self, job_id: str, dataset: str, preset: str, mode: str = "single"):
        """Set the current job information."""
        self.current_job_id = job_id
        self.current_dataset = dataset
        self.current_preset = preset
        self.current_mode = mode
        logger.debug(f"Set current job: {job_id} - {dataset} - {preset} - {mode}")
        
    def clear_current_job(self):
        """Clear the current job information and cleanup process files."""
        # Clean up process files before clearing job info
        if self.current_job_id:
            try:
                from ..database.process_monitor import ProcessStatusMonitor
                from ..database import DatabaseManager
                from .quiet_mode import quiet_database_operations
                with quiet_database_operations():
                    monitor = ProcessStatusMonitor(DatabaseManager())
                monitor._cleanup_process_files(self.current_job_id)
            except Exception as e:
                logger.debug(f"Error cleaning up process files: {e}")
                
        self.current_job_id = None
        self.current_dataset = None
        self.current_preset = None
        self.current_mode = None
        
    def add_subprocess(self, process: subprocess.Popen):
        """Add a subprocess to track for cleanup."""
        self.active_processes.append(process)
        
    def remove_subprocess(self, process: subprocess.Popen):
        """Remove a subprocess from tracking."""
        if process in self.active_processes:
            self.active_processes.remove(process)
            
    def set_comfyui_url(self, url: str):
        """Set the ComfyUI URL for shutdown."""
        self.comfyui_url = url
        
    def _handle_sigint(self, signum, frame):
        """Handle SIGINT signal."""
        # Prevent recursive calls
        if self._in_handler:
            return
            
        self._in_handler = True
        
        # Log the state when signal is received (only to file, not console)
        logger.debug(f"SIGINT received at handler {id(self)}")
        logger.debug(f"Current job state: job_id={self.current_job_id}, dataset={self.current_dataset}")
        
        try:
            # Clear the line and move cursor to beginning
            print("\r" + " " * 80 + "\r", end="", flush=True)
            
            # Show interruption notice with compact formatting
            print("\n━━━ \033[93m⚠️  INTERRUPT SIGNAL RECEIVED (Ctrl+C)\033[0m ━━━")
            
            # Show current status
            self._show_current_status()
            
            # Ask for confirmation
            if self._confirm_exit():
                self._perform_cleanup()
                sys.exit(0)
            else:
                print("\n\033[92m✓ Resuming operation...\033[0m\n")
                self._in_handler = False
                
        except Exception as e:
            logger.error(f"Error in signal handler: {e}")
            self._in_handler = False
            
    def _show_current_status(self):
        """Display current process status in a nice table format."""
        
        # Collect all active jobs (from memory and database)
        active_jobs = []
        
        # First check if we have a job in memory
        if self.current_job_id:
            active_jobs.append({
                'job_id': self.current_job_id,
                'dataset': self.current_dataset,
                'preset': self.current_preset,
                'mode': self.current_mode,
                'status': 'training',
                'source': 'memory',
                'type': 'current'
            })
        
        # Also check database for all active jobs
        try:
            from .quiet_mode import quiet_database_operations
            with quiet_database_operations():
                db = DatabaseManager()
            with db.get_session() as session:
                from ..database.models import Execution, Variation
                
                # Find all active executions (including queued)
                active_execs = session.query(Execution).filter(
                    Execution.status.in_([
                        ExecutionStatus.TRAINING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.GENERATING_PREVIEW.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value,
                        ExecutionStatus.PENDING.value
                    ])
                ).order_by(Execution.created_at.asc()).all()
                
                for exec in active_execs:
                    # Skip if already in memory
                    if exec.job_id == self.current_job_id:
                        # Update the memory entry with DB info
                        for job in active_jobs:
                            if job['job_id'] == exec.job_id:
                                job['start_time'] = exec.start_time
                                job['status'] = exec.status
                                if exec.start_time:
                                    job['duration'] = datetime.utcnow() - exec.start_time
                                break
                    else:
                        duration = None
                        if exec.start_time:
                            duration = datetime.utcnow() - exec.start_time
                        
                        active_jobs.append({
                            'job_id': exec.job_id,
                            'dataset': exec.dataset_name,
                            'preset': exec.preset,
                            'mode': exec.pipeline_mode,
                            'status': exec.status,
                            'start_time': exec.start_time,
                            'duration': duration,
                            'source': 'database',
                            'type': 'execution'
                        })
                
                # Find all active variations (including queued)
                active_vars = session.query(Variation).filter(
                    Variation.status.in_([
                        ExecutionStatus.TRAINING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.GENERATING_PREVIEW.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value,
                        ExecutionStatus.PENDING.value
                    ])
                ).order_by(Variation.created_at.asc()).all()
                
                for var in active_vars:
                    if var.job_id != self.current_job_id:
                        duration = None
                        if var.start_time:
                            duration = datetime.utcnow() - var.start_time
                        
                        active_jobs.append({
                            'job_id': var.job_id,
                            'dataset': var.dataset_name,
                            'preset': var.preset,
                            'mode': 'variations',
                            'status': var.status,
                            'start_time': var.start_time,
                            'duration': duration,
                            'experiment': var.experiment_name,
                            'source': 'database',
                            'type': 'variation'
                        })
                        
        except Exception as e:
            logger.debug(f"Could not query database: {e}")
        
        print("\n━━━ \033[1mACTIVE JOBS STATUS\033[0m ━━━")
        
        if active_jobs:
            # Create table header
            print("┌─────┬──────────┬─────────────────┬─────────────┬────────────┬─────────────┐")
            print("│  #  │ Job ID   │ Dataset         │ Preset      │ Mode       │ Status      │")
            print("├─────┼──────────┼─────────────────┼─────────────┼────────────┼─────────────┤")
            
            # Display each job
            for idx, job in enumerate(active_jobs, 1):
                # Format fields with proper truncation
                job_id = job['job_id'][:8]
                dataset = job['dataset'][:15] + "..." if len(job['dataset']) > 15 else job['dataset']
                preset = job['preset'][:11] + "..." if len(job['preset']) > 11 else job['preset']
                mode = job['mode'][:10]
                raw_status = job['status']
                status = raw_status.replace('_', ' ').title()[:11]
                
                # Determine color based on status
                if job.get('type') == 'current' or raw_status == ExecutionStatus.TRAINING.value:
                    # Green for current/active training
                    print(f"│ \033[92m{idx:^3}\033[0m │ \033[92m{job_id:<8}\033[0m │ {dataset:<15} │ {preset:<11} │ {mode:<10} │ \033[92m{status:<11}\033[0m │")
                elif raw_status in [ExecutionStatus.READY_FOR_TRAINING.value, ExecutionStatus.IN_QUEUE.value, ExecutionStatus.PENDING.value]:
                    # Yellow for queued
                    print(f"│ \033[93m{idx:^3}\033[0m │ {job_id:<8} │ {dataset:<15} │ {preset:<11} │ {mode:<10} │ \033[93m{status:<11}\033[0m │")
                else:
                    # Normal for other states
                    print(f"│ {idx:^3} │ {job_id:<8} │ {dataset:<15} │ {preset:<11} │ {mode:<10} │ {status:<11} │")
            
            print("└─────┴──────────┴─────────────────┴─────────────┴────────────┴─────────────┘")
            
            # Count jobs by status
            active_count = sum(1 for j in active_jobs if j['status'] in [
                ExecutionStatus.TRAINING.value,
                ExecutionStatus.PREPARING_DATASET.value,
                ExecutionStatus.CONFIGURING_PRESET.value,
                ExecutionStatus.GENERATING_PREVIEW.value
            ])
            queued_count = sum(1 for j in active_jobs if j['status'] in [
                ExecutionStatus.READY_FOR_TRAINING.value,
                ExecutionStatus.IN_QUEUE.value,
                ExecutionStatus.PENDING.value
            ])
            
            # Show summary
            print(f"\n\033[92m►\033[0m Active: {active_count} job(s) running")
            if queued_count > 0:
                print(f"\033[93m►\033[0m Queued: {queued_count} job(s) waiting")
            
            # Show additional details for current job
            current_job = next((j for j in active_jobs if j.get('type') == 'current'), None)
            if current_job and 'duration' in current_job and current_job['duration']:
                minutes = int(current_job['duration'].total_seconds() // 60)
                seconds = int(current_job['duration'].total_seconds() % 60)
                print(f"\033[92m►\033[0m Current job running for: {minutes}m {seconds}s")
            
            # Show note about signal isolation if applicable
            if any(job['source'] == 'database' for job in active_jobs) and not self.current_job_id:
                print("\n\033[93mNote:\033[0m Job info retrieved from database (signal isolation active)")
        else:
            print("│" + " " * 25 + "\033[91mNo active training jobs found\033[0m" + " " * 24 + "│")
            print("└" + "─" * 78 + "┘")
            
        # Show system status
        active_count = len([p for p in self.active_processes if p.poll() is None])
        if active_count > 0 or self.comfyui_url:
            print("\n" + "─" * 80)
            if active_count > 0:
                print(f"Active subprocesses: {active_count}")
            
            # Show ComfyUI status
            if self.comfyui_url and ComfyUIManager.is_comfyui_running(self.comfyui_url):
                print(f"ComfyUI: Running at {self.comfyui_url}")
        
    def _confirm_exit(self) -> bool:
        """Ask user for exit confirmation."""
        print("\n━━━ \033[93m⚠️  CONFIRM CANCELLATION\033[0m ━━━")
        print("• Stop all running training processes")
        print("• Mark pending jobs as cancelled") 
        print("• Shutdown ComfyUI if running")
        print("• Clean up temporary files")
        
        try:
            # Set a timeout for the input
            import select
            print("\nType 'yes' to exit or press Enter to continue: ", end="", flush=True)
            
            # Give user 30 seconds to respond
            timeout = 30
            start_time = time.time()
            
            # For non-Windows systems
            if hasattr(select, 'select'):
                while time.time() - start_time < timeout:
                    ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if ready:
                        response = sys.stdin.readline().strip().lower()
                        return response == 'yes'
                        
                # Timeout - continue running
                print("\n\033[90mNo response received within 30 seconds, continuing...\033[0m")
                return False
            else:
                # Windows fallback - simple input with no timeout
                try:
                    response = input().strip().lower()
                    return response == 'yes'
                except EOFError:
                    # Handle case where input is not available
                    print("\n\033[90mNo input available, continuing...\033[0m")
                    return False
                
        except Exception as e:
            logger.debug(f"Error in confirmation: {e}")
            # On error, don't exit
            return False
            
    def _perform_cleanup(self):
        """Perform cleanup operations."""
        print("\n━━━ \033[93mPERFORMING CLEANUP\033[0m ━━━")
        
        # Create a status list for cleanup operations
        cleanup_status = []
        
        # 1. Terminate active subprocesses
        if self.active_processes:
            status_msg = "Terminating training processes..."
            print(f"• {status_msg:<50} ", end="", flush=True)
            terminated_count = 0
            for process in self.active_processes:
                if process.poll() is None:  # Still running
                    try:
                        # For Unix-like systems, terminate the entire session
                        if hasattr(process, 'pid') and sys.platform != "win32":
                            import os
                            import signal as sig
                            try:
                                # Try to get session ID and terminate entire session
                                sid = os.getsid(process.pid)
                                # Kill all processes in the session
                                os.killpg(sid, sig.SIGTERM)
                            except (ProcessLookupError, PermissionError, OSError):
                                try:
                                    # Fallback to process group
                                    pgid = os.getpgid(process.pid)
                                    os.killpg(pgid, sig.SIGTERM)
                                except:
                                    # Final fallback to regular terminate
                                    process.terminate()
                        else:
                            process.terminate()
                            
                        # Give it a moment to terminate gracefully
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            # Force kill if needed
                            if hasattr(process, 'pid') and sys.platform != "win32":
                                try:
                                    # Try session kill first
                                    sid = os.getsid(process.pid)
                                    os.killpg(sid, sig.SIGKILL)
                                except (ProcessLookupError, PermissionError, OSError):
                                    try:
                                        # Fallback to process group kill
                                        pgid = os.getpgid(process.pid)
                                        os.killpg(pgid, sig.SIGKILL)
                                    except:
                                        # Final fallback
                                        process.kill()
                            else:
                                process.kill()
                        terminated_count += 1
                    except Exception as e:
                        logger.debug(f"Error terminating process: {e}")
            print("\033[92m✓\033[0m")
            cleanup_status.append(f"Terminated {terminated_count} process(es)")
        
        # 2. Update database status for ALL active jobs
        jobs_to_cancel = []
        
        # Debug logging (only to file, not console)
        logger.debug(f"Current job_id in signal handler: {self.current_job_id}")
        logger.debug(f"Current dataset: {self.current_dataset}")
        logger.debug(f"Current preset: {self.current_preset}")
        
        # Find all active jobs to cancel
        status_msg = "Finding active jobs to cancel..."
        print(f"• {status_msg:<50} ", end="", flush=True)
        try:
            from .quiet_mode import quiet_database_operations
            with quiet_database_operations():
                db = DatabaseManager()
            with db.get_session() as session:
                from ..database.models import Execution, Variation
                
                # Find ALL active jobs (including queued)
                active_execs = session.query(Execution).filter(
                    Execution.status.in_([
                        ExecutionStatus.TRAINING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.GENERATING_PREVIEW.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value,
                        ExecutionStatus.PENDING.value
                    ])
                ).all()
                
                active_vars = session.query(Variation).filter(
                    Variation.status.in_([
                        ExecutionStatus.TRAINING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.GENERATING_PREVIEW.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value,
                        ExecutionStatus.PENDING.value
                    ])
                ).all()
                
                # Collect all jobs
                for exec in active_execs:
                    jobs_to_cancel.append({
                        'job_id': exec.job_id,
                        'type': 'execution',
                        'dataset': exec.dataset_name
                    })
                    
                for var in active_vars:
                    jobs_to_cancel.append({
                        'job_id': var.job_id,
                        'type': 'variation',
                        'dataset': var.dataset_name,
                        'experiment': var.experiment_name
                    })
                
                if jobs_to_cancel:
                    print("\033[92m✓\033[0m")
                    cleanup_status.append(f"Found {len(jobs_to_cancel)} active job(s) to cancel")
                else:
                    print("\033[93m-\033[0m")
                    cleanup_status.append("No active jobs found")
                    
        except Exception as e:
            print("\033[91m✗\033[0m")
            cleanup_status.append(f"Error finding jobs: {e}")
        
        # Cancel all active jobs
        if jobs_to_cancel:
            status_msg = f"Cancelling {len(jobs_to_cancel)} active job(s)..."
            print(f"• {status_msg:<50} ", end="", flush=True)
            
            from ..utils.job_tracker import get_tracker
            from ..database.process_monitor import ProcessStatusMonitor
            
            tracker = get_tracker()
            with quiet_database_operations():
                monitor = ProcessStatusMonitor(DatabaseManager())
            cancelled_count = 0
            
            try:
                for job in jobs_to_cancel:
                    success = tracker.update_status(
                        job['job_id'], 
                        ExecutionStatus.CANCELLED,
                        error_message="Cancelled by user (Ctrl+C)"
                    )
                    
                    if success:
                        # Clean up process monitoring files
                        monitor._cleanup_process_files(job['job_id'])
                        cancelled_count += 1
                
                # Force a sync to ensure all updates are written
                try:
                    with quiet_database_operations():
                        db = DatabaseManager()
                    with db.get_session() as session:
                        session.commit()
                except:
                    pass
                
                if cancelled_count == len(jobs_to_cancel):
                    print("\033[92m✓\033[0m")
                    cleanup_status.append(f"Cancelled {cancelled_count} job(s) successfully")
                else:
                    print("\033[93m!\033[0m")
                    cleanup_status.append(f"Cancelled {cancelled_count}/{len(jobs_to_cancel)} jobs")
                    
            except Exception as e:
                print("\033[91m✗\033[0m")
                cleanup_status.append(f"Error cancelling jobs: {e}")
                
        # 3. Mark all pending jobs as cancelled
        status_msg = "Marking pending jobs as cancelled..."
        print(f"• {status_msg:<50} ", end="", flush=True)
        try:
            with quiet_database_operations():
                db = DatabaseManager()
            with db.get_session() as session:
                from ..database.models import Execution, Variation
                
                # Update executions
                pending_execs = session.query(Execution).filter(
                    Execution.status.in_([
                        ExecutionStatus.PENDING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value
                    ])
                ).all()
                
                exec_count = len(pending_execs)
                for exec in pending_execs:
                    exec.status = ExecutionStatus.CANCELLED.value
                    exec.error_message = "Cancelled due to pipeline shutdown"
                    exec.end_time = datetime.utcnow()
                    
                # Update variations
                pending_vars = session.query(Variation).filter(
                    Variation.status.in_([
                        ExecutionStatus.PENDING.value,
                        ExecutionStatus.PREPARING_DATASET.value,
                        ExecutionStatus.CONFIGURING_PRESET.value,
                        ExecutionStatus.READY_FOR_TRAINING.value,
                        ExecutionStatus.IN_QUEUE.value
                    ])
                ).all()
                
                var_count = len(pending_vars)
                for var in pending_vars:
                    var.status = ExecutionStatus.CANCELLED.value
                    var.error_message = "Cancelled due to pipeline shutdown"
                    var.end_time = datetime.utcnow()
                    
                session.commit()
                total_count = exec_count + var_count
                print("\033[92m✓\033[0m")
                cleanup_status.append(f"Cancelled {total_count} pending job(s)")
                
        except Exception as e:
            print("\033[91m✗\033[0m")
            cleanup_status.append(f"Error cancelling pending jobs: {e}")
            
        # 4. Shutdown ComfyUI
        if self.comfyui_url and ComfyUIManager.is_comfyui_running(self.comfyui_url):
            status_msg = "Shutting down ComfyUI..."
            print(f"• {status_msg:<50} ", end="", flush=True)
            try:
                if ComfyUIManager.shutdown_comfyui(self.comfyui_url):
                    print("\033[92m✓\033[0m")
                    cleanup_status.append("ComfyUI shutdown successfully")
                else:
                    print("\033[91m✗\033[0m")
                    cleanup_status.append("Failed to shutdown ComfyUI")
            except Exception as e:
                print("\033[91m✗\033[0m")
                cleanup_status.append(f"Error shutting down ComfyUI: {e}")
        
        # Show cleanup summary
        print("\n━━━ \033[92m✓ CLEANUP COMPLETED\033[0m ━━━")
        
        # Clear current job info after all cleanup is done
        self.clear_current_job()
        
        print("\n\033[90mGoodbye!\033[0m\n")


# Global instance
_shutdown_handler = GracefulShutdownHandler()


def get_shutdown_handler() -> GracefulShutdownHandler:
    """Get the global shutdown handler instance."""
    logger.debug(f"Getting shutdown handler instance at {id(_shutdown_handler)}")
    return _shutdown_handler