"""
Hook management system for pipeline post-processing.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import PipelineHook, HookType
from .preview_hook import ImagePreviewHook
from .file_move_hook import FileMoveHook
from ...utils.path_manager import PathManager
from ...config import Config

logger = logging.getLogger(__name__)


class HookManager:
    """
    Manages and executes pipeline hooks for post-processing actions.
    
    Handles hook registration, execution order, and error handling.
    """
    
    def __init__(self, base_path: str, path_manager: Optional[PathManager] = None):
        """
        Initialize hook manager.
        
        Args:
            base_path: Base path for the project
            path_manager: Optional path manager for custom profiles
        """
        self.base_path = Path(base_path)
        self.path_manager = path_manager
        self.hooks: Dict[HookType, List[PipelineHook]] = {}
        
        # Register default hooks
        self._register_default_hooks()
        
    def register_hook(self, hook: PipelineHook) -> None:
        """
        Register a hook for execution.
        
        Args:
            hook: The hook to register
        """
        hook_type = hook.hook_type
        if hook_type not in self.hooks:
            self.hooks[hook_type] = []
            
        self.hooks[hook_type].append(hook)
        logger.debug(f"Registered hook: {hook.name} for {hook_type.value}")
        
    def execute_hooks(self, hook_type: HookType, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all hooks of a specific type.
        
        Args:
            hook_type: Type of hooks to execute
            context: Execution context
            
        Returns:
            Aggregated results from all hooks
        """
        if hook_type not in self.hooks:
            return {}
            
        results = {}
        executed_hooks = []
        
        for hook in self.hooks[hook_type]:
            if hook.should_execute(context):
                try:
                    logger.info(f"Executing hook: {hook.name}")
                    hook_result = hook.execute(context)
                    
                    if hook_result:
                        results[hook.name] = hook_result
                        executed_hooks.append(hook.name)
                        
                        # Log hook results
                        if hook_result.get('success', True):
                            logger.info(f"Hook {hook.name} completed successfully")
                        else:
                            logger.warning(f"Hook {hook.name} failed: {hook_result.get('error', 'Unknown error')}")
                    else:
                        logger.info(f"Hook {hook.name} completed (no results)")
                        executed_hooks.append(hook.name)
                        
                except Exception as e:
                    logger.error(f"Hook {hook.name} failed with exception: {e}")
                    results[hook.name] = {
                        'success': False,
                        'error': str(e),
                        'hook_name': hook.name
                    }
            else:
                logger.debug(f"Skipping hook {hook.name} (conditions not met)")
                
        # Add summary to results
        results['_summary'] = {
            'executed_hooks': executed_hooks,
            'total_hooks': len(self.hooks[hook_type]),
            'success_count': sum(1 for r in results.values() 
                               if isinstance(r, dict) and r.get('success', True)),
            'hook_type': hook_type.value
        }
        
        return results
        
    def execute_post_training_hooks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all post-training hooks.
        
        This is a convenience method for the most common hook execution.
        
        Args:
            context: Training context
            
        Returns:
            Combined results from all post-training hooks
        """
        return self.execute_hooks(HookType.POST_TRAINING, context)
        
    def _register_default_hooks(self) -> None:
        """Register default hooks based on configuration."""
        
        # 1. Image Preview Hook (if ComfyUI is configured)
        if self._should_register_preview_hook():
            preview_hook = ImagePreviewHook(
                base_path=str(self.base_path),
                enabled=True
            )
            self.register_hook(preview_hook)
            
        # 2. File Move Hook (if using custom profile)
        if self._should_register_file_move_hook():
            file_move_hook = FileMoveHook(
                path_manager=self.path_manager
            )
            self.register_hook(file_move_hook)
            
    def _should_register_preview_hook(self) -> bool:
        """Check if preview hook should be registered."""
        # Always register preview hook - it will check conditions at execution time
        return True
        
    def _should_register_file_move_hook(self) -> bool:
        """Check if file move hook should be registered."""
        # Only register if using custom path manager
        return self.path_manager is not None and self.path_manager.is_custom_mode
        
    def get_registered_hooks(self, hook_type: Optional[HookType] = None) -> Dict[str, List[str]]:
        """
        Get information about registered hooks.
        
        Args:
            hook_type: Optional filter by hook type
            
        Returns:
            Dictionary with hook information
        """
        if hook_type:
            hook_types = [hook_type]
        else:
            hook_types = list(self.hooks.keys())
            
        result = {}
        for ht in hook_types:
            if ht in self.hooks:
                result[ht.value] = [hook.name for hook in self.hooks[ht]]
            else:
                result[ht.value] = []
                
        return result
        
    def disable_hook(self, hook_name: str) -> bool:
        """
        Disable a hook by name.
        
        Args:
            hook_name: Name of the hook to disable
            
        Returns:
            True if hook was found and disabled
        """
        for hook_list in self.hooks.values():
            for hook in hook_list:
                if hook.name == hook_name:
                    hook.enabled = False
                    logger.info(f"Disabled hook: {hook_name}")
                    return True
                    
        logger.warning(f"Hook not found: {hook_name}")
        return False
        
    def enable_hook(self, hook_name: str) -> bool:
        """
        Enable a hook by name.
        
        Args:
            hook_name: Name of the hook to enable
            
        Returns:
            True if hook was found and enabled
        """
        for hook_list in self.hooks.values():
            for hook in hook_list:
                if hook.name == hook_name:
                    hook.enabled = True
                    logger.info(f"Enabled hook: {hook_name}")
                    return True
                    
        logger.warning(f"Hook not found: {hook_name}")
        return False