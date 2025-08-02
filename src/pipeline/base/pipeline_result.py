"""Result types for pipeline operations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class PipelineStatus(Enum):
    """Pipeline execution status."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DatasetResult:
    """Result for individual dataset processing."""
    dataset_name: str
    success: bool
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    prompts_file: Optional[str] = None
    configs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """
    Comprehensive result object for pipeline operations.
    
    Supports both single and batch operations with detailed
    tracking of successes, failures, and partial results.
    """
    status: PipelineStatus
    mode: str  # 'single', 'batch', 'variations'
    total_datasets: int
    successful_datasets: int
    failed_datasets: int
    results: Dict[str, DatasetResult] = field(default_factory=dict)
    execution_time: float = 0.0
    context: Optional['PipelineContext'] = None
    
    # Backward compatibility fields
    success: bool = field(init=False)
    dataset_name: str = field(default="")
    dataset_prepared: bool = field(default=False)
    configs_generated: bool = field(default=False)
    input_dir: Optional[str] = field(default=None)
    output_dir: Optional[str] = field(default=None)
    prompts_file: Optional[str] = field(default=None)
    preset_configs: Optional[Dict[str, List[str]]] = field(default=None)
    error_message: Optional[str] = field(default=None)
    repeats: int = field(default=30)
    class_name: str = field(default="person")
    
    def __post_init__(self):
        """Initialize backward compatibility fields."""
        self.success = self.status == PipelineStatus.SUCCESS
        
        # For single mode, populate legacy fields
        if self.mode == 'single' and self.results:
            first_result = next(iter(self.results.values()))
            self.dataset_name = first_result.dataset_name
            self.dataset_prepared = first_result.success
            self.configs_generated = bool(first_result.configs)
            self.input_dir = first_result.input_dir
            self.output_dir = first_result.output_dir
            self.prompts_file = first_result.prompts_file
            if first_result.configs:
                self.preset_configs = {first_result.dataset_name: first_result.configs}
            self.error_message = first_result.error
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_datasets == 0:
            return 0.0
        return self.successful_datasets / self.total_datasets
        
    def get_summary(self) -> str:
        """Get human-readable summary."""
        return (
            f"Pipeline {self.mode} mode: {self.status.value}\n"
            f"Processed {self.total_datasets} datasets "
            f"({self.successful_datasets} successful, {self.failed_datasets} failed)\n"
            f"Success rate: {self.success_rate:.1%}\n"
            f"Execution time: {self.execution_time:.2f}s"
        )