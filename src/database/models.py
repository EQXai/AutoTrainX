"""SQLAlchemy models for AutoTrainX execution tracking."""

from datetime import datetime
from typing import Optional
import json

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, 
    DateTime, Index, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .enums import ExecutionStatus, PipelineMode


Base = declarative_base()


class Execution(Base):
    """Model for tracking single and batch pipeline executions."""
    __tablename__ = 'executions'
    
    job_id = Column(String(8), primary_key=True)  # Short ID format
    status = Column(String(50), nullable=False, default=ExecutionStatus.PENDING.value)
    pipeline_mode = Column(String(20), nullable=False)
    dataset_name = Column(String(255), nullable=False)
    preset = Column(String(100), nullable=False)
    total_steps = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    output_path = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes
    __table_args__ = (
        Index('idx_executions_status', 'status'),
        Index('idx_executions_dataset', 'dataset_name'),
        Index('idx_executions_created', 'created_at'),
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
    varied_parameters = Column(Text, nullable=False)  # JSON string
    parameter_values = Column(Text, nullable=False)   # JSON string
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    output_path = Column(Text)
    parent_experiment_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes
    __table_args__ = (
        Index('idx_variations_status', 'status'),
        Index('idx_variations_experiment', 'experiment_name'),
        Index('idx_variations_parent', 'parent_experiment_id'),
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
            'varied_parameters': json.loads(self.varied_parameters) if self.varied_parameters else {},
            'parameter_values': json.loads(self.parameter_values) if self.parameter_values else {},
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
    
    def get_varied_parameters(self) -> dict:
        """Get varied parameters as dictionary."""
        if self.varied_parameters:
            return json.loads(self.varied_parameters)
        return {}
    
    def set_varied_parameters(self, params: dict):
        """Set varied parameters from dictionary."""
        self.varied_parameters = json.dumps(params)
    
    def get_parameter_values(self) -> dict:
        """Get parameter values as dictionary."""
        if self.parameter_values:
            return json.loads(self.parameter_values)
        return {}
    
    def set_parameter_values(self, values: dict):
        """Set parameter values from dictionary."""
        self.parameter_values = json.dumps(values)