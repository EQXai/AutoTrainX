"""
Simple schemas for API requests and responses.

These schemas define the minimal data structures needed for
web-to-CLI translation and statistics display.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


# Request schemas for training
class SingleTrainingRequest(BaseModel):
    """Request for single mode training."""
    source_path: str = Field(..., description="Path to source dataset")
    preset: str = Field(default="all", description="Preset name or 'all'")
    dataset_name: Optional[str] = Field(None, description="Optional custom dataset name")
    repeats: int = Field(default=30, description="Number of repetitions")
    class_name: str = Field(default="person", description="Class name for object")
    preview_count: int = Field(default=0, description="Number of preview images")
    generate_configs: bool = Field(default=True, description="Generate configurations")
    auto_clean: bool = Field(default=True, description="Auto-clean existing datasets")


class DatasetConfig(BaseModel):
    """Configuration for a single dataset in batch mode."""
    source_path: str = Field(..., description="Path to source dataset")
    preset: str = Field(default="all", description="Preset to use")
    dataset_name: Optional[str] = Field(None, description="Optional custom name")
    repeats: int = Field(default=30, description="Number of repetitions")
    class_name: str = Field(default="person", description="Class name")


class BatchTrainingRequest(BaseModel):
    """Request for batch mode training."""
    datasets: List[DatasetConfig] = Field(..., description="List of datasets to train")
    strategy: str = Field(default="sequential", description="Execution strategy")
    auto_clean: bool = Field(default=True, description="Auto-clean existing datasets")


class VariationsTrainingRequest(BaseModel):
    """Request for variations mode training."""
    dataset_name: str = Field(..., description="Dataset name")
    base_preset: str = Field(..., description="Base preset name")
    variations: Dict[str, List[Any]] = Field(..., description="Parameter variations")
    auto_clean: bool = Field(default=True, description="Auto-clean existing datasets")


# Response schemas
class TrainingResponse(BaseModel):
    """Response after starting training."""
    success: bool = Field(..., description="Whether command was executed successfully")
    command: str = Field(..., description="CLI command that was executed")
    job_id: Optional[str] = Field(None, description="Job ID if extracted from output")
    output: Optional[str] = Field(None, description="Command output")
    error: Optional[str] = Field(None, description="Error message if failed")


class JobInfo(BaseModel):
    """Basic job information."""
    job_id: str
    dataset_name: Optional[str]
    pipeline_mode: str
    preset: str
    status: str
    created_at: datetime
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    success: Optional[bool]
    error_message: Optional[str]
    progress_percentage: Optional[float] = None


class JobStatistics(BaseModel):
    """Overall job statistics."""
    total_jobs: int
    status_breakdown: Dict[str, int]
    mode_breakdown: Dict[str, int]
    success_rate: float
    jobs_last_24h: int


class PresetStatistics(BaseModel):
    """Statistics for a preset."""
    total_jobs: int
    successful_jobs: int
    success_rate: float
    avg_duration_minutes: Optional[float]


class JobsListResponse(BaseModel):
    """Response for jobs list endpoint."""
    jobs: List[JobInfo]
    total: int
    page: int
    page_size: int


class RunningJobsResponse(BaseModel):
    """Response for running jobs endpoint."""
    running_jobs: List[JobInfo]
    count: int


class StatisticsResponse(BaseModel):
    """Response for statistics endpoint."""
    job_statistics: JobStatistics
    preset_statistics: Dict[str, PresetStatistics]
    recent_completions: List[JobInfo]