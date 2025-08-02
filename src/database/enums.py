"""Database enums for AutoTrainX execution tracking."""

from enum import Enum


class ExecutionStatus(Enum):
    """Status values for execution tracking."""
    PENDING = "pending"
    IN_QUEUE = "in_queue"
    PREPARING_DATASET = "preparing_dataset"
    CONFIGURING_PRESET = "configuring_preset"
    READY_FOR_TRAINING = "ready_for_training"  # Ready and waiting in queue
    TRAINING = "training"
    GENERATING_PREVIEW = "generating_preview"
    DONE = "done"
    COMPLETED = "done"  # Alias for DONE
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineMode(Enum):
    """Pipeline execution modes."""
    SINGLE = "single"
    BATCH = "batch"
    VARIATIONS = "variations"