"""Resource management and cleanup utilities for AutoTrainX.

This module provides utilities for managing system resources,
temporary files, and automatic cleanup operations.
"""

import os
import shutil

# Try to import psutil, but make it optional
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import tempfile
import atexit
from pathlib import Path
from typing import List, Optional, Set, Dict, Any
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages system resources and temporary files.
    
    This class provides centralized resource management including:
    - Temporary file tracking and cleanup
    - Memory usage monitoring
    - Disk space validation
    - Automatic cleanup on exit
    """
    
    def __init__(self):
        """Initialize the resource manager."""
        self._temp_dirs: Set[Path] = set()
        self._temp_files: Set[Path] = set()
        self._cleanup_handlers: List[callable] = []
        
        # Register cleanup on program exit
        atexit.register(self.cleanup_all)
    
    @property
    def memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics.
        
        Returns:
            Dict with memory usage in GB:
                - total: Total system memory
                - available: Available memory
                - used: Used memory
                - percent: Usage percentage
        """
        if not PSUTIL_AVAILABLE:
            # Return default values when psutil is not available
            return {
                'total': 16.0,  # Assume 16GB total
                'available': 8.0,  # Assume 8GB available
                'used': 8.0,
                'percent': 50.0
            }
        
        mem = psutil.virtual_memory()
        return {
            'total': mem.total / (1024**3),
            'available': mem.available / (1024**3),
            'used': mem.used / (1024**3),
            'percent': mem.percent
        }
    
    def disk_usage(self, path: str = '/') -> Dict[str, float]:
        """Get disk usage statistics for a path.
        
        Args:
            path: Path to check disk usage for
            
        Returns:
            Dict with disk usage in GB:
                - total: Total disk space
                - available: Available space
                - used: Used space
                - percent: Usage percentage
        """
        if not PSUTIL_AVAILABLE:
            # Return default values when psutil is not available
            return {
                'total': 500.0,  # Assume 500GB total
                'available': 100.0,  # Assume 100GB available
                'used': 400.0,
                'percent': 80.0
            }
            
        usage = psutil.disk_usage(path)
        return {
            'total': usage.total / (1024**3),
            'available': usage.free / (1024**3),
            'used': usage.used / (1024**3),
            'percent': usage.percent
        }
    
    def check_memory_available(self, required_gb: float) -> bool:
        """Check if sufficient memory is available.
        
        Args:
            required_gb: Required memory in gigabytes
            
        Returns:
            True if sufficient memory is available
        """
        return self.memory_usage['available'] >= required_gb
    
    def check_disk_space(self, path: str, required_gb: float) -> bool:
        """Check if sufficient disk space is available.
        
        Args:
            path: Path to check
            required_gb: Required space in gigabytes
            
        Returns:
            True if sufficient space is available
        """
        usage = self.disk_usage(path)
        return usage['available'] >= required_gb
    
    @contextmanager
    def temporary_directory(self, prefix: str = "autotrainx_", 
                          cleanup: bool = True):
        """Create a temporary directory with automatic cleanup.
        
        Args:
            prefix: Directory name prefix
            cleanup: Whether to cleanup on exit
            
        Yields:
            Path to temporary directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        
        if cleanup:
            self._temp_dirs.add(temp_dir)
        
        try:
            yield temp_dir
        finally:
            if cleanup and temp_dir.exists():
                self._cleanup_directory(temp_dir)
                self._temp_dirs.discard(temp_dir)
    
    @contextmanager
    def temporary_file(self, suffix: str = "", prefix: str = "autotrainx_",
                      cleanup: bool = True):
        """Create a temporary file with automatic cleanup.
        
        Args:
            suffix: File suffix
            prefix: File name prefix
            cleanup: Whether to cleanup on exit
            
        Yields:
            Path to temporary file
        """
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        temp_file = Path(temp_path)
        
        if cleanup:
            self._temp_files.add(temp_file)
        
        try:
            yield temp_file
        finally:
            if cleanup and temp_file.exists():
                temp_file.unlink()
                self._temp_files.discard(temp_file)
    
    def register_cleanup_handler(self, handler: callable):
        """Register a cleanup handler to be called on exit.
        
        Args:
            handler: Callable to execute during cleanup
        """
        self._cleanup_handlers.append(handler)
    
    def cleanup_all(self):
        """Clean up all tracked resources."""
        # Clean temporary files
        for temp_file in list(self._temp_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean temp file {temp_file}: {e}")
        
        # Clean temporary directories
        for temp_dir in list(self._temp_dirs):
            try:
                if temp_dir.exists():
                    self._cleanup_directory(temp_dir)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean temp directory {temp_dir}: {e}")
        
        # Run cleanup handlers
        for handler in self._cleanup_handlers:
            try:
                handler()
            except Exception as e:
                logger.warning(f"Cleanup handler failed: {e}")
        
        # Clear tracking
        self._temp_files.clear()
        self._temp_dirs.clear()
        self._cleanup_handlers.clear()
    
    def _cleanup_directory(self, directory: Path):
        """Recursively clean up a directory.
        
        Args:
            directory: Directory to clean up
        """
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)


class WorkspaceManager:
    """Manages the AutoTrainX workspace directory structure.
    
    This class handles:
    - Workspace organization
    - Old file cleanup
    - Cache management
    """
    
    def __init__(self, base_path: Path):
        """Initialize workspace manager.
        
        Args:
            base_path: Base path for AutoTrainX
        """
        self.base_path = Path(base_path)
        self.workspace_path = self.base_path / "workspace"
        self.logs_path = self.base_path / "logs"
    
    def clean_old_logs(self, days: int = 7):
        """Clean log files older than specified days.
        
        Args:
            days: Number of days to keep logs
        """
        if not self.logs_path.exists():
            return
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for log_file in self.logs_path.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_time:
                    log_file.unlink()
                    logger.info(f"Removed old log file: {log_file}")
            except Exception as e:
                logger.warning(f"Failed to remove log file {log_file}: {e}")
    
    def clean_empty_directories(self):
        """Remove empty directories in workspace."""
        for root, dirs, files in os.walk(self.workspace_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logger.debug(f"Removed empty directory: {dir_path}")
                except Exception as e:
                    logger.debug(f"Could not remove directory {dir_path}: {e}")
    
    def get_workspace_size(self) -> float:
        """Get total size of workspace in GB.
        
        Returns:
            Size in gigabytes
        """
        total_size = 0
        
        for path in self.workspace_path.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
        
        return total_size / (1024**3)
    
    def clean_dataset_cache(self, dataset_name: str):
        """Clean cache files for a specific dataset.
        
        Args:
            dataset_name: Name of the dataset
        """
        # Clean input cache
        input_cache = self.workspace_path / "input" / dataset_name / ".cache"
        if input_cache.exists():
            shutil.rmtree(input_cache)
            logger.info(f"Cleaned input cache for {dataset_name}")
        
        # Clean output cache
        output_cache = self.workspace_path / "output" / dataset_name / ".cache"
        if output_cache.exists():
            shutil.rmtree(output_cache)
            logger.info(f"Cleaned output cache for {dataset_name}")


# Global resource manager instance
_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance.
    
    Returns:
        ResourceManager instance
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


@contextmanager
def managed_resource(required_memory_gb: float = 0, 
                    required_disk_gb: float = 0,
                    workspace_path: str = None):
    """Context manager for resource-aware operations.
    
    Args:
        required_memory_gb: Required memory in GB
        required_disk_gb: Required disk space in GB
        workspace_path: Path to check disk space for
        
    Raises:
        MemoryError: If insufficient memory
        IOError: If insufficient disk space
        
    Yields:
        ResourceManager instance
    """
    manager = get_resource_manager()
    
    # Check memory
    if required_memory_gb > 0:
        if not manager.check_memory_available(required_memory_gb):
            raise MemoryError(
                f"Insufficient memory. Required: {required_memory_gb}GB, "
                f"Available: {manager.memory_usage['available']:.2f}GB"
            )
    
    # Check disk space
    if required_disk_gb > 0 and workspace_path:
        if not manager.check_disk_space(workspace_path, required_disk_gb):
            usage = manager.disk_usage(workspace_path)
            raise IOError(
                f"Insufficient disk space. Required: {required_disk_gb}GB, "
                f"Available: {usage['available']:.2f}GB"
            )
    
    yield manager