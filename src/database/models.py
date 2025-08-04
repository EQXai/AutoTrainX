"""SQLAlchemy models with multi-database support."""

from datetime import datetime
from typing import Optional, Dict, Any
import json

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, Index, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import relationship

from .enums import ExecutionStatus, PipelineMode
from .dialects.sqlite import SQLiteJSONType

Base = declarative_base()


# Helper function for conditional types
def get_json_column():
    """Get JSON column that works with both SQLite and PostgreSQL."""
    return Column(
        postgresql.JSONB().with_variant(
            SQLiteJSONType(), 'sqlite'
        )
    )


def get_datetime_column(**kwargs):
    """Get DateTime column that works with both databases."""
    return Column(
        postgresql.TIMESTAMP(timezone=True).with_variant(
            DateTime(), 'sqlite'
        ),
        **kwargs
    )


class Execution(Base):
    """Model for tracking single and batch pipeline executions."""
    __tablename__ = 'executions'
    
    job_id = Column(String(8), primary_key=True)  # Short ID format
    status = Column(String(50), nullable=False, default=ExecutionStatus.PENDING.value)
    pipeline_mode = Column(String(20), nullable=False)
    dataset_name = Column(String(255), nullable=False)
    preset = Column(String(100), nullable=False)
    total_steps = Column(Integer)
    start_time = get_datetime_column()
    end_time = get_datetime_column()
    duration_seconds = Column(Float)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    output_path = Column(Text)
    created_at = get_datetime_column(default=datetime.utcnow)
    updated_at = get_datetime_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes
    __table_args__ = (
        Index('idx_executions_status', 'status'),
        Index('idx_executions_dataset', 'dataset_name'),
        Index('idx_executions_created', 'created_at'),
        # Composite indexes for performance
        Index('idx_exec_status_created', 'status', 'created_at'),
        Index('idx_exec_dataset_status', 'dataset_name', 'status'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        def format_timestamp(dt):
            """Format datetime to string with 3 decimal places for microseconds."""
            if dt:
                return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            return None
        
        def format_duration(seconds):
            """Format duration in seconds to human readable format."""
            if not seconds:
                return None
            
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m {secs}s"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
        
        return {
            'job_id': self.job_id,
            'status': self.status,
            'pipeline_mode': self.pipeline_mode,
            'dataset_name': self.dataset_name,
            'preset': self.preset,
            'total_steps': self.total_steps,
            'start_time': format_timestamp(self.start_time),
            'end_time': format_timestamp(self.end_time),
            'duration_seconds': format_duration(self.duration_seconds),
            'success': self.success,
            'error_message': self.error_message,
            'output_path': self.output_path,
            'created_at': format_timestamp(self.created_at),
            'updated_at': format_timestamp(self.updated_at),
        }


class Variation(Base):
    """Model for tracking variations pipeline executions."""
    __tablename__ = 'variations'
    
    job_id = Column(String(8), primary_key=True)  # Short ID format
    status = Column(String(50), nullable=False, default=ExecutionStatus.PENDING.value)
    variation_id = Column(String(100), nullable=False)
    experiment_name = Column(String(255), nullable=False)
    dataset_name = Column(String(255), nullable=False)
    preset = Column(String(100), nullable=False)
    total_steps = Column(Integer)
    total_combinations = Column(Integer, nullable=False)
    varied_parameters = get_json_column()  # Native JSON support
    parameter_values = get_json_column()   # Native JSON support
    start_time = get_datetime_column()
    end_time = get_datetime_column()
    duration_seconds = Column(Float)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    output_path = Column(Text)
    parent_experiment_id = Column(String(100))
    created_at = get_datetime_column(default=datetime.utcnow)
    updated_at = get_datetime_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes
    __table_args__ = (
        Index('idx_variations_status', 'status'),
        Index('idx_variations_experiment', 'experiment_name'),
        Index('idx_variations_parent', 'parent_experiment_id'),
        # Composite indexes
        Index('idx_var_status_created', 'status', 'created_at'),
        Index('idx_var_experiment_status', 'experiment_name', 'status', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        def format_timestamp(dt):
            """Format datetime to string with 3 decimal places for microseconds."""
            if dt:
                return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            return None
        
        def format_duration(seconds):
            """Format duration in seconds to human readable format."""
            if not seconds:
                return None
            
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m {secs}s"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
        
        return {
            'job_id': self.job_id,
            'status': self.status,
            'variation_id': self.variation_id,
            'experiment_name': self.experiment_name,
            'dataset_name': self.dataset_name,
            'preset': self.preset,
            'total_steps': self.total_steps,
            'total_combinations': self.total_combinations,
            'varied_parameters': self.varied_parameters or {},
            'parameter_values': self.parameter_values or {},
            'start_time': format_timestamp(self.start_time),
            'end_time': format_timestamp(self.end_time),
            'duration_seconds': format_duration(self.duration_seconds),
            'success': self.success,
            'error_message': self.error_message,
            'output_path': self.output_path,
            'parent_experiment_id': self.parent_experiment_id,
            'created_at': format_timestamp(self.created_at),
            'updated_at': format_timestamp(self.updated_at),
        }
    
    # Simplified accessors - JSON handled natively
    def get_varied_parameters(self) -> dict:
        """Get varied parameters as dictionary."""
        return self.varied_parameters or {}
    
    def set_varied_parameters(self, params: dict):
        """Set varied parameters from dictionary."""
        self.varied_parameters = params
    
    def get_parameter_values(self) -> dict:
        """Get parameter values as dictionary."""
        return self.parameter_values or {}
    
    def set_parameter_values(self, values: dict):
        """Set parameter values from dictionary."""
        self.parameter_values = values


class JobSummaryCache(Base):
    """Materialized view for job summaries."""
    __tablename__ = 'job_summary_cache'
    
    job_id = Column(String, primary_key=True)
    job_type = Column(String, nullable=False)  # 'execution' or 'variation'
    status = Column(String, nullable=False)
    dataset_name = Column(String, nullable=False)
    preset = Column(String, nullable=False)
    start_time = get_datetime_column()
    duration_seconds = Column(Float)
    success = Column(Boolean)
    last_updated = get_datetime_column(default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_summary_status_updated', 'status', 'last_updated'),
    )


class ModelPath(Base):
    """Model directory tracking."""
    __tablename__ = 'model_paths'
    
    id = Column(String, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    added_at = get_datetime_column(default=datetime.utcnow)
    last_scan = get_datetime_column()
    model_count = Column(Integer, default=0)
    
    # Relationship
    models = relationship("Model", back_populates="model_path", cascade="all, delete-orphan")


class Model(Base):
    """Trained model tracking."""
    __tablename__ = 'models'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # .safetensors, .ckpt, etc.
    size = Column(Integer, nullable=False)  # in bytes
    created_at = get_datetime_column()
    modified_at = get_datetime_column()
    has_preview = Column(Boolean, default=False)
    preview_images = get_json_column()  # Array of image paths
    model_metadata = get_json_column()  # Model metadata (renamed from metadata)
    
    # Foreign key
    path_id = Column(String, ForeignKey('model_paths.id'))
    model_path = relationship("ModelPath", back_populates="models")