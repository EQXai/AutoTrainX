"""Shared context and state management for pipelines."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import threading


@dataclass
class PipelineContext:
    """
    Shared context for pipeline execution.
    
    Manages state, dependencies, and shared resources across
    different pipeline components.
    """
    pipeline_id: str
    start_time: datetime = field(default_factory=datetime.now)
    processed_datasets: Set[str] = field(default_factory=set)
    generated_configs: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def add_processed_dataset(self, dataset_name: str) -> None:
        """Thread-safe addition of processed dataset."""
        with self._lock:
            self.processed_datasets.add(dataset_name)
            
    def add_error(self, error: Dict[str, Any]) -> None:
        """Thread-safe error recording."""
        with self._lock:
            self.errors.append({
                **error,
                'timestamp': datetime.now()
            })
            
    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            'pipeline_id': self.pipeline_id,
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'datasets_processed': len(self.processed_datasets),
            'configs_generated': sum(len(configs) for configs in self.generated_configs.values()),
            'errors': len(self.errors),
            'warnings': len(self.warnings)
        }