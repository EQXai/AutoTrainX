"""
Pydantic models for API requests and responses.

This module defines all the data models used for request validation
and response serialization in the AutoTrainX API.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, validator, ConfigDict


# =============================================================================
# Enums
# =============================================================================

class PipelineMode(str, Enum):
    """Pipeline execution modes."""
    SINGLE = "single"
    BATCH = "batch"
    VARIATIONS = "variations"


class JobStatus(str, Enum):
    """Job execution status - matches database ExecutionStatus."""
    PENDING = "pending"
    IN_QUEUE = "in_queue"
    PREPARING_DATASET = "preparing_dataset"
    CONFIGURING_PRESET = "configuring_preset"
    READY_FOR_TRAINING = "ready_for_training"
    TRAINING = "training"
    GENERATING_PREVIEW = "generating_preview"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingStrategy(str, Enum):
    """Training execution strategy for batch mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# =============================================================================
# Base Models
# =============================================================================

class BaseResponse(BaseModel):
    """Base response model with common fields."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Human-readable message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(default=False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any] = Field(..., description="List of items")
    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    @validator('total_pages', always=True)
    def calculate_total_pages(cls, v, values):
        """Calculate total pages from total_count and page_size."""
        total_count = values.get('total_count', 0)
        page_size = values.get('page_size', 1)
        return (total_count + page_size - 1) // page_size


# =============================================================================
# Job Models
# =============================================================================

class JobCreate(BaseModel):
    """Model for creating a new job."""
    mode: PipelineMode = Field(..., description="Pipeline execution mode")
    name: Optional[str] = Field(None, description="Optional job name")
    description: Optional[str] = Field(None, description="Optional job description")
    
    # Single mode parameters
    source_path: Optional[str] = Field(None, description="Source dataset path (for single mode)")
    dataset_name: Optional[str] = Field(None, description="Dataset name (for single mode)")
    preset: Optional[str] = Field(None, description="Training preset name")
    repeats: Optional[int] = Field(default=30, ge=1, description="Number of repeats")
    class_name: Optional[str] = Field(default="person", description="Class name for training")
    
    # Batch mode parameters
    datasets: Optional[List[Dict[str, Any]]] = Field(None, description="List of datasets (for batch mode)")
    strategy: Optional[TrainingStrategy] = Field(default=TrainingStrategy.SEQUENTIAL, description="Execution strategy")
    
    # Variations mode parameters
    base_preset: Optional[str] = Field(None, description="Base preset for variations")
    variations: Optional[Dict[str, List[Any]]] = Field(None, description="Parameter variations")
    
    # Common options
    generate_configs: bool = Field(default=True, description="Whether to generate training configs")
    auto_clean: bool = Field(default=False, description="Whether to auto-clean temporary files")
    enable_preview: bool = Field(default=True, description="Whether to generate image previews")
    preview_count: int = Field(default=0, ge=0, le=20, description="Number of preview images to generate")

    @validator('source_path')
    def validate_source_path(cls, v, values):
        """Validate source path for single mode."""
        if values.get('mode') == PipelineMode.SINGLE and not v:
            raise ValueError("source_path is required for single mode")
        return v

    @validator('datasets')
    def validate_datasets(cls, v, values):
        """Validate datasets for batch mode."""
        if values.get('mode') == PipelineMode.BATCH and not v:
            raise ValueError("datasets is required for batch mode")
        return v

    @validator('variations')
    def validate_variations(cls, v, values):
        """Validate variations for variations mode."""
        if values.get('mode') == PipelineMode.VARIATIONS and not v:
            raise ValueError("variations is required for variations mode")
        return v


class JobUpdate(BaseModel):
    """Model for updating an existing job."""
    name: Optional[str] = Field(None, description="Job name")
    description: Optional[str] = Field(None, description="Job description")
    status: Optional[JobStatus] = Field(None, description="Job status")


class JobResponse(BaseModel):
    """Response model for job information."""
    id: str = Field(..., description="Unique job ID")
    name: Optional[str] = Field(None, description="Job name")
    description: Optional[str] = Field(None, description="Job description")
    mode: PipelineMode = Field(..., description="Pipeline execution mode")
    status: JobStatus = Field(..., description="Current job status")
    
    # Execution details
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    
    # Progress information
    total_steps: Optional[int] = Field(None, description="Total number of steps")
    completed_steps: Optional[int] = Field(None, description="Number of completed steps")
    current_step: Optional[str] = Field(None, description="Current step description")
    progress_percentage: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    
    # Results
    successful_datasets: Optional[int] = Field(None, description="Number of successful datasets")
    failed_datasets: Optional[int] = Field(None, description="Number of failed datasets")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Configuration
    config: Optional[Dict[str, Any]] = Field(None, description="Job configuration")
    results: Optional[Dict[str, Any]] = Field(None, description="Job results")

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(PaginatedResponse):
    """Response model for job listing."""
    items: List[JobResponse] = Field(..., description="List of jobs")


# =============================================================================
# Training Models
# =============================================================================

class TrainingRequest(BaseModel):
    """Base model for training requests."""
    job_id: Optional[str] = Field(None, description="Optional job ID to associate with")
    enable_monitoring: bool = Field(default=True, description="Enable progress monitoring")


class SingleTrainingRequest(TrainingRequest):
    """Request model for single dataset training."""
    source_path: str = Field(..., description="Path to source dataset")
    preset: str = Field(..., description="Training preset name")
    dataset_name: Optional[str] = Field(None, description="Custom dataset name")
    repeats: int = Field(default=30, ge=1, description="Number of repeats")
    class_name: str = Field(default="person", description="Class name for training")
    generate_configs: bool = Field(default=True, description="Generate training configs")
    auto_clean: bool = Field(default=False, description="Auto-clean temporary files")
    preview_count: int = Field(default=0, ge=0, le=20, description="Number of preview images to generate")


class BatchTrainingRequest(TrainingRequest):
    """Request model for batch training."""
    datasets: List[Dict[str, Any]] = Field(..., description="List of dataset configurations")
    strategy: TrainingStrategy = Field(default=TrainingStrategy.SEQUENTIAL, description="Execution strategy")
    parallel_workers: Optional[int] = Field(None, ge=1, le=10, description="Number of parallel workers")


class VariationsTrainingRequest(TrainingRequest):
    """Request model for variations training."""
    dataset_name: str = Field(..., description="Name of prepared dataset")
    base_preset: str = Field(..., description="Base preset for variations")
    variations: Dict[str, List[Any]] = Field(..., description="Parameter variations")
    
    @validator('variations')
    def validate_variations_dict(cls, v):
        """Validate variations dictionary structure."""
        if not v:
            raise ValueError("variations cannot be empty")
        for param, values in v.items():
            if not isinstance(values, list) or len(values) == 0:
                raise ValueError(f"variations[{param}] must be a non-empty list")
        return v


class TrainingResponse(BaseResponse):
    """Response model for training operations."""
    job_id: str = Field(..., description="Associated job ID")
    mode: PipelineMode = Field(..., description="Training mode")
    status: JobStatus = Field(..., description="Training status")
    results: Optional[Dict[str, Any]] = Field(None, description="Training results")


# =============================================================================
# Dataset Models
# =============================================================================

class DatasetInfo(BaseModel):
    """Model for dataset information."""
    name: str = Field(..., description="Dataset name")
    path: str = Field(..., description="Dataset path")
    total_images: int = Field(..., description="Number of images")
    total_texts: int = Field(..., description="Number of text files")
    has_sample_prompts: bool = Field(..., description="Whether sample prompts exist")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    size_mb: Optional[float] = Field(None, description="Dataset size in MB")


class DatasetListResponse(PaginatedResponse):
    """Response model for dataset listing."""
    items: List[DatasetInfo] = Field(..., description="List of datasets")


class DatasetPreparationRequest(BaseModel):
    """Request model for dataset preparation."""
    source_path: str = Field(..., description="Source dataset path")
    repeats: int = Field(default=30, ge=1, description="Number of repeats")
    class_name: str = Field(default="person", description="Class name")
    auto_clean: bool = Field(default=False, description="Auto-clean temporary files")


class DatasetPreparationResponse(BaseResponse):
    """Response model for dataset preparation."""
    dataset_name: str = Field(..., description="Prepared dataset name")
    output_path: str = Field(..., description="Output dataset path")
    stats: Dict[str, Any] = Field(..., description="Preparation statistics")


# =============================================================================
# Preset Models
# =============================================================================

class PresetInfo(BaseModel):
    """Model for preset information."""
    name: str = Field(..., description="Preset name")
    description: str = Field(..., description="Preset description")
    category: Optional[str] = Field(None, description="Preset category")
    architecture: Optional[str] = Field(None, description="Model architecture")
    config_files: List[str] = Field(default_factory=list, description="Configuration files")


class PresetListResponse(BaseResponse):
    """Response model for preset listing."""
    presets: List[PresetInfo] = Field(..., description="List of available presets")


class PresetConfigRequest(BaseModel):
    """Request model for preset configuration generation."""
    dataset_name: str = Field(..., description="Dataset name")
    preset_name: str = Field(..., description="Preset name")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Custom parameters")


class PresetConfigResponse(BaseResponse):
    """Response model for preset configuration."""
    config_path: str = Field(..., description="Generated configuration path")
    config_content: Dict[str, Any] = Field(..., description="Configuration content")


# =============================================================================
# Progress Models
# =============================================================================

class ProgressUpdate(BaseModel):
    """Model for progress updates."""
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current status")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: Optional[str] = Field(None, description="Current step description")
    completed_steps: int = Field(..., description="Number of completed steps")
    total_steps: int = Field(..., description="Total number of steps")
    message: Optional[str] = Field(None, description="Progress message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    
    # Training-specific progress
    epoch: Optional[int] = Field(None, description="Current epoch")
    loss: Optional[float] = Field(None, description="Current loss")
    learning_rate: Optional[float] = Field(None, description="Current learning rate")
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional progress metadata")


# =============================================================================
# System Models
# =============================================================================

class SystemStatus(BaseModel):
    """Model for system status information."""
    status: str = Field(..., description="Overall system status")
    version: str = Field(..., description="API version")
    uptime: Optional[float] = Field(None, description="System uptime in seconds")
    
    # Service statuses
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    
    # Resource information
    resources: Optional[Dict[str, Any]] = Field(None, description="System resource information")
    
    # Statistics
    stats: Optional[Dict[str, Any]] = Field(None, description="System statistics")


class PipelineStatus(BaseModel):
    """Model for pipeline status information."""
    pipeline_status: str = Field(..., description="Pipeline status")
    base_path: str = Field(..., description="Base path")
    available_modes: List[str] = Field(..., description="Available pipeline modes")
    
    # Configuration
    config: Dict[str, Any] = Field(..., description="Pipeline configuration")
    
    # Available resources
    datasets: Dict[str, Any] = Field(..., description="Dataset information")
    presets: Dict[str, Any] = Field(..., description="Preset information")
    configurations: Dict[str, Any] = Field(..., description="Configuration information")
    variations: Dict[str, Any] = Field(..., description="Variations information")
    directories: Dict[str, str] = Field(..., description="Important directories")
    
    # ComfyUI integration
    comfyui: Dict[str, Any] = Field(..., description="ComfyUI configuration")