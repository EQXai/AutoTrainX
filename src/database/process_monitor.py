"""Process monitoring system for AutoTrainX execution tracking."""

import os
import time
import threading
import signal
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime, timedelta
import logging

from .models import Execution, Variation
from .enums import ExecutionStatus

# Try to import psutil for better process checking
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class ProcessStatusMonitor:
    """Monitor for detecting dead/terminated processes automatically."""
    
    def __init__(self, db_manager, check_interval: int = 30):
        """Initialize process monitor.
        
        Args:
            db_manager: Database manager instance
            check_interval: Interval in seconds between checks
        """
        self.db_manager = db_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.thread = None
        self.base_path = Path.cwd()  # Current working directory
        
    def start_monitoring(self):
        """Start automatic process monitoring."""
        if not self.monitoring:
            self.monitoring = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("Process status monitoring started")
    
    def stop_monitoring(self):
        """Stop automatic process monitoring."""
        if self.monitoring:
            self.monitoring = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
            logger.info("Process status monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                cleaned_count = self._check_active_processes()
                if cleaned_count > 0:
                    logger.info(f"Auto-cleaned {cleaned_count} stale processes")
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                time.sleep(self.check_interval)
    
    def _check_active_processes(self) -> int:
        """Check active processes and mark dead ones as failed.
        
        Returns:
            Number of processes cleaned up
        """
        cleaned_count = 0
        
        with self.db_manager.get_session() as session:
            # Find executions in active states
            active_executions = session.query(Execution).filter(
                Execution.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PREPARING_DATASET.value,
                    ExecutionStatus.CONFIGURING_PRESET.value,
                    ExecutionStatus.GENERATING_PREVIEW.value
                ])
            ).all()
            
            # Find variations in active states
            active_variations = session.query(Variation).filter(
                Variation.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PREPARING_DATASET.value,
                    ExecutionStatus.CONFIGURING_PRESET.value,
                    ExecutionStatus.GENERATING_PREVIEW.value
                ])
            ).all()
            
            # Check executions
            for execution in active_executions:
                if not self._is_process_alive(execution.job_id):
                    self._mark_execution_as_failed(
                        session, execution, 
                        "Process terminated unexpectedly (auto-detected)"
                    )
                    cleaned_count += 1
                elif self._is_process_stale(execution.job_id, execution.updated_at):
                    self._mark_execution_as_failed(
                        session, execution,
                        "Process appears to be stale (no heartbeat)"
                    )
                    cleaned_count += 1
            
            # Check variations
            for variation in active_variations:
                if not self._is_process_alive(variation.job_id):
                    self._mark_variation_as_failed(
                        session, variation,
                        "Process terminated unexpectedly (auto-detected)"
                    )
                    cleaned_count += 1
                elif self._is_process_stale(variation.job_id, variation.updated_at):
                    self._mark_variation_as_failed(
                        session, variation,
                        "Process appears to be stale (no heartbeat)"
                    )
                    cleaned_count += 1
            
            session.commit()
            
        return cleaned_count
    
    def _is_process_alive(self, job_id: str) -> bool:
        """Check if a process is alive using PID file and system calls.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if process is alive, False otherwise
        """
        try:
            # Look for PID file
            pid_file = self.base_path / f".training_pid_{job_id}.pid"
            if not pid_file.exists():
                logger.debug(f"PID file not found for job {job_id}")
                return False
                
            pid_str = pid_file.read_text().strip()
            if not pid_str.isdigit():
                logger.warning(f"Invalid PID in file for job {job_id}: {pid_str}")
                return False
                
            pid = int(pid_str)
            
            # Check with psutil if available (more reliable)
            if HAS_PSUTIL:
                try:
                    if psutil.pid_exists(pid):
                        # Double-check that it's actually our process
                        proc = psutil.Process(pid)
                        # Check if it's a Python process (our training script)
                        cmdline = proc.cmdline()
                        if any('python' in arg.lower() for arg in cmdline):
                            return True
                    return False
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return False
            else:
                # Fallback: use os.kill with signal 0 (doesn't actually kill)
                try:
                    os.kill(pid, 0)
                    return True
                except (OSError, ProcessLookupError):
                    return False
                    
        except Exception as e:
            logger.warning(f"Error checking process {job_id}: {e}")
            return False
    
    def _is_process_stale(self, job_id: str, last_update: datetime) -> bool:
        """Check if a process is stale based on heartbeat and last update.
        
        Args:
            job_id: Job identifier
            last_update: Last database update time
            
        Returns:
            True if process appears stale
        """
        try:
            # Check heartbeat file first
            heartbeat_file = self.base_path / f".heartbeat_{job_id}.txt"
            if heartbeat_file.exists():
                try:
                    last_heartbeat_str = heartbeat_file.read_text().strip()
                    if last_heartbeat_str.isdigit():
                        last_heartbeat = int(last_heartbeat_str)
                        heartbeat_age = time.time() - last_heartbeat
                        
                        # Consider stale if no heartbeat in last 5 minutes
                        if heartbeat_age > 300:  # 5 minutes
                            logger.debug(f"Job {job_id} stale: no heartbeat for {heartbeat_age:.0f}s")
                            return True
                        return False
                except Exception as e:
                    logger.warning(f"Error reading heartbeat for {job_id}: {e}")
            
            # If no heartbeat file, check database update time
            # Consider stale if no database update in last 10 minutes
            if last_update:
                update_age = (datetime.utcnow() - last_update).total_seconds()
                if update_age > 600:  # 10 minutes
                    logger.debug(f"Job {job_id} stale: no DB update for {update_age:.0f}s")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking staleness for {job_id}: {e}")
            return False
    
    def _mark_execution_as_failed(self, session, execution: Execution, error_message: str):
        """Mark an execution as failed with cleanup."""
        logger.info(f"Marking execution {execution.job_id} as failed: {error_message}")
        
        execution.status = ExecutionStatus.FAILED.value
        execution.error_message = error_message
        execution.end_time = datetime.utcnow()
        execution.updated_at = datetime.utcnow()
        
        if execution.start_time:
            duration = (execution.end_time - execution.start_time).total_seconds()
            execution.duration_seconds = duration
        
        # Clean up associated files
        self._cleanup_process_files(execution.job_id)
    
    def _mark_variation_as_failed(self, session, variation: Variation, error_message: str):
        """Mark a variation as failed with cleanup."""
        logger.info(f"Marking variation {variation.job_id} as failed: {error_message}")
        
        variation.status = ExecutionStatus.FAILED.value
        variation.error_message = error_message
        variation.end_time = datetime.utcnow()
        variation.updated_at = datetime.utcnow()
        
        if variation.start_time:
            duration = (variation.end_time - variation.start_time).total_seconds()
            variation.duration_seconds = duration
        
        # Clean up associated files
        self._cleanup_process_files(variation.job_id)
    
    def _cleanup_process_files(self, job_id: str):
        """Clean up process-related files for a job."""
        try:
            # Remove PID file
            pid_file = self.base_path / f".training_pid_{job_id}.pid"
            if pid_file.exists():
                pid_file.unlink()
                logger.debug(f"Cleaned up PID file for {job_id}")
            
            # Remove heartbeat file
            heartbeat_file = self.base_path / f".heartbeat_{job_id}.txt"
            if heartbeat_file.exists():
                heartbeat_file.unlink()
                logger.debug(f"Cleaned up heartbeat file for {job_id}")
                
        except Exception as e:
            logger.warning(f"Error cleaning up files for {job_id}: {e}")
    
    def get_active_processes(self) -> Set[str]:
        """Get set of currently active job IDs.
        
        Returns:
            Set of active job IDs
        """
        active_jobs = set()
        
        with self.db_manager.get_session() as session:
            # Get active executions
            active_executions = session.query(Execution.job_id).filter(
                Execution.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PREPARING_DATASET.value,
                    ExecutionStatus.CONFIGURING_PRESET.value,
                    ExecutionStatus.GENERATING_PREVIEW.value
                ])
            ).all()
            
            # Get active variations
            active_variations = session.query(Variation.job_id).filter(
                Variation.status.in_([
                    ExecutionStatus.TRAINING.value,
                    ExecutionStatus.PREPARING_DATASET.value,
                    ExecutionStatus.CONFIGURING_PRESET.value,
                    ExecutionStatus.GENERATING_PREVIEW.value
                ])
            ).all()
            
            active_jobs.update(job_id for (job_id,) in active_executions)
            active_jobs.update(job_id for (job_id,) in active_variations)
        
        return active_jobs
    
    def manual_cleanup(self) -> int:
        """Perform manual cleanup of stale processes.
        
        Returns:
            Number of processes cleaned up
        """
        logger.info("Performing manual process cleanup")
        return self._check_active_processes()


class HeartbeatWriter:
    """Utility class for writing process heartbeats."""
    
    def __init__(self, job_id: str, base_path: Optional[Path] = None):
        """Initialize heartbeat writer.
        
        Args:
            job_id: Job identifier
            base_path: Base path for heartbeat files
        """
        self.job_id = job_id
        self.base_path = base_path or Path.cwd()
        self.heartbeat_file = self.base_path / f".heartbeat_{job_id}.txt"
        self.last_write = 0
        self.write_interval = 30  # Write every 30 seconds minimum
        
    def write_heartbeat(self, force: bool = False):
        """Write heartbeat timestamp.
        
        Args:
            force: Force write even if interval hasn't passed
        """
        try:
            current_time = time.time()
            
            # Only write if enough time has passed or forced
            if force or (current_time - self.last_write) >= self.write_interval:
                self.heartbeat_file.write_text(str(int(current_time)))
                self.last_write = current_time
                
        except Exception as e:
            logger.warning(f"Error writing heartbeat for {self.job_id}: {e}")
    
    def cleanup(self):
        """Clean up heartbeat file."""
        try:
            if self.heartbeat_file.exists():
                self.heartbeat_file.unlink()
        except Exception as e:
            logger.warning(f"Error cleaning up heartbeat for {self.job_id}: {e}")