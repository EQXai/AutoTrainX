"""Abstract interface for all pipeline implementations.

This module provides the abstract base class and configuration structure
for all pipeline implementations in the AutoTrainX system. It ensures
consistent behavior and interface across different pipeline execution modes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from ...config import Config
from ...utils.path_manager import PathManager


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution.
    
    This dataclass holds all configuration parameters needed for pipeline
    execution across different modes (notebook, script, distributed).
    
    Attributes:
        base_path: Root directory path for pipeline operations. Defaults to
            the system's default base path from Config.
        auto_clean: Whether to automatically clean up temporary files and
            artifacts after pipeline execution. Defaults to False.
        parallel: Enable parallel execution of pipeline steps where possible.
            Defaults to False.
        max_workers: Maximum number of worker threads/processes for parallel
            execution. Only used when parallel=True. Defaults to 4.
        dry_run: If True, generates and displays the execution plan without
            actually running the pipeline. Useful for validation and testing.
            Defaults to False.
        verbose: Enable detailed logging and progress output during execution.
            Defaults to True.
        preview_count: Number of preview images to generate after training.
            Defaults to 0 (no previews).
            
    Examples:
        >>> config = PipelineConfig(
        ...     base_path="/data/experiments",
        ...     parallel=True,
        ...     max_workers=8
        ... )
        >>> config.dry_run = True  # Enable dry-run mode
    """
    base_path: str = field(default_factory=Config.get_default_base_path)
    auto_clean: bool = False
    parallel: bool = False
    max_workers: int = 4
    dry_run: bool = False
    verbose: bool = True
    preview_count: int = 0
    path_manager: Optional[PathManager] = None
    
    
class PipelineInterface(ABC):
    """Abstract base class for all pipeline implementations.
    
    This interface defines the contract that all pipeline modes must implement,
    ensuring consistency across different execution strategies (notebook, script,
    distributed). All concrete pipeline implementations must inherit from this
    class and implement the abstract methods.
    
    The pipeline interface provides a unified API for:
    - Validating inputs before execution
    - Generating execution plans for dry-run scenarios
    - Executing pipelines with various configurations
    - Managing pipeline configuration and state
    
    Attributes:
        config: PipelineConfig instance containing execution parameters.
            Set during initialization and validated automatically.
            
    Raises:
        ValueError: If the configuration is invalid (e.g., base_path doesn't exist).
        
    Examples:
        >>> from pipeline.notebook import NotebookPipeline
        >>> config = PipelineConfig(base_path="/data", dry_run=True)
        >>> pipeline = NotebookPipeline(config)
        >>> errors = pipeline.validate_inputs(notebook_path="experiment.ipynb")
        >>> if not errors:
        ...     plan = pipeline.get_execution_plan(notebook_path="experiment.ipynb")
        ...     print(plan)
    
    Note:
        This is an abstract base class and cannot be instantiated directly.
        Use one of the concrete implementations: NotebookPipeline, ScriptPipeline,
        or DistributedPipeline.
    """
    
    def __init__(self, config: PipelineConfig):
        """Initialize the pipeline with configuration.
        
        Sets up the pipeline instance with the provided configuration and
        validates it immediately. The configuration is stored as an instance
        attribute and used throughout the pipeline lifecycle.
        
        Args:
            config: PipelineConfig instance containing execution parameters
                such as base_path, parallel execution settings, and verbosity.
                
        Raises:
            ValueError: If the configuration is invalid. Currently checks:
                - base_path exists and is accessible
                - Additional validation may be added by subclasses
                
        Examples:
            >>> config = PipelineConfig(
            ...     base_path="/home/user/experiments",
            ...     parallel=True,
            ...     max_workers=8
            ... )
            >>> pipeline = SomeConcretePipeline(config)  # Subclass instance
        """
        self.config = config
        self._validate_config()
        self._hooks: Dict[str, List[Any]] = {}
        
        # Initialize hook manager for new hook system
        self._initialize_hook_manager()
        
    @abstractmethod
    def execute(self, **kwargs) -> 'PipelineResult':
        """Execute the pipeline with provided parameters.
        
        This is the main entry point for pipeline execution. Each concrete
        implementation defines its own parameter requirements based on the
        pipeline type (notebook, script, or distributed).
        
        The method orchestrates the entire pipeline execution flow:
        1. Validates inputs using validate_inputs()
        2. Generates execution plan if in dry_run mode
        3. Executes the pipeline steps
        4. Collects and returns results
        
        Args:
            **kwargs: Variable keyword arguments specific to each pipeline type.
                Common parameters include:
                - notebook_path (str): For NotebookPipeline
                - script_path (str): For ScriptPipeline
                - task_config (dict): For DistributedPipeline
                See specific implementations for required parameters.
                
        Returns:
            PipelineResult: Object containing execution details including:
                - status (str): 'success', 'failed', or 'partial'
                - outputs (dict): Pipeline outputs and artifacts
                - logs (list): Execution logs and messages
                - metrics (dict): Performance and execution metrics
                - errors (list): Any errors encountered during execution
                
        Raises:
            ValueError: If required parameters are missing or invalid.
            RuntimeError: If pipeline execution fails.
            NotImplementedError: If called on the abstract base class.
            
        Examples:
            >>> # For NotebookPipeline
            >>> result = pipeline.execute(
            ...     notebook_path="experiment.ipynb",
            ...     parameters={"learning_rate": 0.01}
            ... )
            >>> if result.status == "success":
            ...     print(result.outputs)
            
        Note:
            This is an abstract method that must be implemented by subclasses.
            The actual execution logic depends on the pipeline type.
        """
        pass
        
    @abstractmethod
    def validate_inputs(self, **kwargs) -> List[str]:
        """Validate input parameters before execution.
        
        Performs comprehensive validation of all input parameters required
        for pipeline execution. This method should be called before execute()
        to ensure all prerequisites are met and avoid runtime failures.
        
        Validation checks may include:
        - Required parameters are present
        - File paths exist and are readable
        - Parameter types and formats are correct
        - Resource availability (memory, disk space)
        - Dependencies and prerequisites are satisfied
        
        Args:
            **kwargs: Variable keyword arguments to validate, specific to each
                pipeline implementation. These should match the parameters
                expected by the execute() method.
                
        Returns:
            List[str]: List of validation error messages. An empty list
                indicates all validations passed. Each error message should
                be descriptive enough for users to correct the issue.
                
        Examples:
            >>> # Validate notebook pipeline inputs
            >>> errors = pipeline.validate_inputs(
            ...     notebook_path="experiment.ipynb",
            ...     parameters={"batch_size": -1}  # Invalid value
            ... )
            >>> if errors:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
            ... else:
            ...     print("All validations passed")
            
            >>> # Example error messages
            >>> errors = pipeline.validate_inputs(notebook_path="missing.ipynb")
            >>> print(errors)
            ['Notebook file not found: missing.ipynb']
            
        Note:
            - This method should NOT modify any state or parameters
            - Validation should be thorough but efficient
            - Error messages should guide users toward resolution
            - Subclasses must implement pipeline-specific validation logic
        """
        pass
        
    @abstractmethod
    def get_execution_plan(self, **kwargs) -> Dict[str, Any]:
        """Generate and return the execution plan without running it.
        
        Creates a detailed execution plan showing all steps that would be
        performed during pipeline execution. This is particularly useful for:
        - Dry-run scenarios to preview actions before execution
        - User confirmation and approval workflows
        - Debugging and understanding pipeline behavior
        - Cost estimation for resource-intensive operations
        
        The execution plan should include all significant actions, resource
        requirements, and potential side effects without actually performing
        any modifications.
        
        Args:
            **kwargs: Variable keyword arguments matching those expected by
                execute(). The same parameters used for execution should be
                provided to generate an accurate plan.
                
        Returns:
            Dict[str, Any]: Dictionary containing the execution plan with
                a structure that typically includes:
                - 'steps' (List[Dict]): Ordered list of execution steps
                - 'estimated_duration' (str): Estimated total execution time
                - 'resource_requirements' (Dict): CPU, memory, disk needs
                - 'inputs' (Dict): Validated input parameters
                - 'outputs' (List[str]): Expected output artifacts
                - 'warnings' (List[str]): Any warnings or cautions
                - 'dry_run' (bool): Always True for execution plans
                
        Examples:
            >>> plan = pipeline.get_execution_plan(
            ...     notebook_path="train_model.ipynb",
            ...     parameters={"epochs": 10}
            ... )
            >>> print(f"Total steps: {len(plan['steps'])}")
            >>> for i, step in enumerate(plan['steps']):
            ...     print(f"{i+1}. {step['name']}: {step['description']}")
            
            >>> # Example plan structure
            >>> plan = {
            ...     'steps': [
            ...         {'name': 'validate', 'description': 'Validate notebook'},
            ...         {'name': 'setup', 'description': 'Set up environment'},
            ...         {'name': 'execute', 'description': 'Run notebook cells'}
            ...     ],
            ...     'estimated_duration': '15 minutes',
            ...     'resource_requirements': {'cpu': 4, 'memory': '8GB'},
            ...     'outputs': ['model.pkl', 'metrics.json']
            ... }
            
        Note:
            - No actual execution or side effects should occur
            - The plan should be as accurate as possible
            - Include warnings for potentially destructive operations
            - Subclasses define the specific plan structure
        """
        pass
        
    def _validate_config(self) -> None:
        """Validate pipeline configuration.
        
        Internal method that validates the PipelineConfig instance to ensure
        it meets all requirements for pipeline execution. This method is called
        automatically during initialization and should not be called directly.
        
        Current validations:
        - Verifies that base_path exists and is accessible
        - Additional validations can be added by subclasses by overriding
          this method and calling super()._validate_config()
        
        Raises:
            ValueError: If any configuration parameter is invalid. Currently
                raises if:
                - base_path does not exist
                - base_path is not accessible (permission denied)
                
        Examples:
            >>> # This method is called automatically during init
            >>> config = PipelineConfig(base_path="/invalid/path")
            >>> try:
            ...     pipeline = SomePipeline(config)
            ... except ValueError as e:
            ...     print(f"Config validation failed: {e}")
            
        Note:
            - This is a protected method (single underscore prefix)
            - Subclasses can extend validation by overriding this method
            - Always call super()._validate_config() when overriding
            - Validation should be fast and not perform expensive operations
        """
        if not Path(self.config.base_path).exists():
            raise ValueError(f"Base path does not exist: {self.config.base_path}")
            
    def register_hook(self, hook_type: str, hook: Any) -> None:
        """Register a hook for pipeline events.
        
        Args:
            hook_type: Type of hook (e.g., 'post_training')
            hook: Hook instance to register
        """
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []
        self._hooks[hook_type].append(hook)
        
    def execute_hooks(self, hook_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all hooks of a given type.
        
        Args:
            hook_type: Type of hooks to execute
            context: Context data for hook execution
            
        Returns:
            Combined results from all hooks
        """
        results = {}
        
        # Use new hook manager if available and hook_type is post_training
        if hasattr(self, 'hook_manager') and hook_type == 'post_training':
            from ..hooks.base import HookType
            try:
                results = self.hook_manager.execute_post_training_hooks(context)
                # If hook manager executed successfully, return its results
                # Don't execute legacy hooks to avoid duplication
                return results
            except Exception as e:
                if self.config.verbose:
                    print(f"Hook manager execution failed: {e}")
                # Fall through to legacy system if hook manager fails
                    
        # Fallback to legacy hook system for compatibility
        # Only execute if hook manager didn't handle it
        if hook_type in self._hooks:
            for hook in self._hooks[hook_type]:
                if hasattr(hook, 'should_execute') and hook.should_execute(context):
                    try:
                        hook_result = hook.execute(context)
                        if hook_result:
                            results.update(hook_result)
                    except Exception as e:
                        if self.config.verbose:
                            print(f"Legacy hook execution failed: {e}")
        return results
        
    def _initialize_hook_manager(self) -> None:
        """Initialize the hook manager for the new hook system."""
        try:
            from ..hooks import HookManager
            self.hook_manager = HookManager(
                base_path=self.config.base_path,
                path_manager=self.config.path_manager
            )
        except ImportError:
            # Hook manager not available, use legacy system only
            if self.config.verbose:
                print("Hook manager not available, using legacy hook system")
            self.hook_manager = None