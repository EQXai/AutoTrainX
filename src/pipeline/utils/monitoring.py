"""Progress monitoring utilities for pipeline execution."""

from typing import Callable, Optional, Any, Dict, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import threading
from enum import Enum
from contextlib import contextmanager
import functools
import time


class ProgressState(Enum):
    """Progress state enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressInfo:
    """Information about current progress."""
    current_step: str
    total_steps: int
    current_progress: int
    total_progress: int
    state: ProgressState
    message: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_progress == 0:
            return 0.0
        return (self.current_progress / self.total_progress) * 100
        
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


class ProgressMonitor:
    """
    Monitor and report pipeline execution progress.
    
    Supports callbacks for progress updates and thread-safe operations.
    """
    
    def __init__(self, callback: Optional[Callable[[ProgressInfo], None]] = None):
        """
        Initialize progress monitor.
        
        Args:
            callback: Optional callback function for progress updates
        """
        self.callback = callback
        self._progress_info = ProgressInfo(
            current_step="Initializing",
            total_steps=0,
            current_progress=0,
            total_progress=0,
            state=ProgressState.PENDING
        )
        self._lock = threading.Lock()
        
    def start(self, total_steps: int, total_progress: int) -> None:
        """
        Start progress monitoring.
        
        Args:
            total_steps: Total number of steps
            total_progress: Total progress units
        """
        with self._lock:
            self._progress_info.total_steps = total_steps
            self._progress_info.total_progress = total_progress
            self._progress_info.state = ProgressState.RUNNING
            self._progress_info.start_time = datetime.now()
            self._notify()
            
    def update_step(self, step_name: str, step_number: int) -> None:
        """
        Update current step.
        
        Args:
            step_name: Name of current step
            step_number: Current step number
        """
        with self._lock:
            self._progress_info.current_step = step_name
            self._progress_info.current_progress = step_number
            self._notify()
            
    def update_progress(self, progress: int, message: str = "") -> None:
        """
        Update progress within current step.
        
        Args:
            progress: Current progress value
            message: Optional progress message
        """
        with self._lock:
            self._progress_info.current_progress = progress
            self._progress_info.message = message
            self._notify()
            
    def complete(self) -> None:
        """Mark progress as completed."""
        with self._lock:
            self._progress_info.state = ProgressState.COMPLETED
            self._progress_info.end_time = datetime.now()
            self._progress_info.current_progress = self._progress_info.total_progress
            self._notify()
            
    def fail(self, error_message: str) -> None:
        """
        Mark progress as failed.
        
        Args:
            error_message: Error message
        """
        with self._lock:
            self._progress_info.state = ProgressState.FAILED
            self._progress_info.message = error_message
            self._progress_info.end_time = datetime.now()
            self._notify()
            
    def cancel(self) -> None:
        """Mark progress as cancelled."""
        with self._lock:
            self._progress_info.state = ProgressState.CANCELLED
            self._progress_info.end_time = datetime.now()
            self._notify()
            
    def get_info(self) -> ProgressInfo:
        """Get current progress information."""
        with self._lock:
            # Return a copy to avoid thread safety issues
            return ProgressInfo(
                current_step=self._progress_info.current_step,
                total_steps=self._progress_info.total_steps,
                current_progress=self._progress_info.current_progress,
                total_progress=self._progress_info.total_progress,
                state=self._progress_info.state,
                message=self._progress_info.message,
                start_time=self._progress_info.start_time,
                end_time=self._progress_info.end_time
            )
            
    def _notify(self) -> None:
        """Notify callback of progress update."""
        if self.callback:
            # Create a copy for the callback
            info = self.get_info()
            try:
                self.callback(info)
            except Exception:
                # Ignore callback errors
                pass


class ConsoleProgressReporter:
    """Enhanced console progress reporter with better visualization."""
    
    @staticmethod
    def report(info: ProgressInfo) -> None:
        """
        Report progress to console with enhanced formatting.
        
        Args:
            info: Progress information
        """
        if info.state == ProgressState.RUNNING:
            # Create progress bar
            bar_length = 30
            filled_length = int(bar_length * info.percentage / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Format time
            elapsed = info.elapsed_time
            if elapsed < 60:
                time_str = f"{elapsed:.1f}s"
            else:
                time_str = f"{int(elapsed//60)}m {int(elapsed%60)}s"
            
            # Print progress line
            print(f"\r[{bar}] {info.percentage:.1f}% | {info.current_step} | {time_str} | {info.message}", 
                  end="", flush=True)
        elif info.state == ProgressState.COMPLETED:
            print(f"\n✅ Completed in {info.elapsed_time:.1f}s")
        elif info.state == ProgressState.FAILED:
            print(f"\n❌ Failed: {info.message}")
        elif info.state == ProgressState.CANCELLED:
            print(f"\n⚠️  Cancelled after {info.elapsed_time:.1f}s")