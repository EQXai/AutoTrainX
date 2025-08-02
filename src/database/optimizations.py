"""Database optimization utilities for AutoTrainX."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import Query
from sqlalchemy.sql import text

from .models import Execution, Variation
from .enums import ExecutionStatus


class QueryOptimizer:
    """Optimized query patterns for common database operations."""
    
    @staticmethod
    def get_active_jobs_optimized(session, limit: int = 100) -> List[Dict[str, Any]]:
        """Get active jobs using a single optimized query with UNION.
        
        This replaces the current approach of two separate queries + Python sorting.
        """
        query = text("""
            SELECT * FROM (
                SELECT 
                    job_id, status, dataset_name, preset, start_time, 
                    created_at, 'execution' as type, pipeline_mode as mode,
                    NULL as experiment_name, NULL as variation_id
                FROM executions
                WHERE status IN ('pending', 'in_queue', 'training', 'preparing_dataset')
                
                UNION ALL
                
                SELECT 
                    job_id, status, dataset_name, preset, start_time,
                    created_at, 'variation' as type, 'variations' as mode,
                    experiment_name, variation_id
                FROM variations
                WHERE status IN ('pending', 'in_queue', 'training', 'preparing_dataset')
            ) AS combined
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        result = session.execute(query, {"limit": limit})
        return [dict(row) for row in result]
    
    @staticmethod
    def get_statistics_optimized(session) -> Dict[str, Any]:
        """Get statistics using optimized aggregate queries.
        
        This replaces multiple count() queries with a single aggregate query.
        """
        # Single query for all execution statistics
        exec_stats = session.query(
            func.count(Execution.job_id).label('total'),
            func.sum(case((Execution.success == True, 1), else_=0)).label('successful'),
            func.sum(case((Execution.success == False, 1), else_=0)).label('failed'),
            func.avg(Execution.duration_seconds).label('avg_duration'),
            func.sum(case((Execution.status == ExecutionStatus.PENDING.value, 1), else_=0)).label('pending'),
            func.sum(case((Execution.status == ExecutionStatus.TRAINING.value, 1), else_=0)).label('training'),
            func.sum(case((Execution.status == ExecutionStatus.DONE.value, 1), else_=0)).label('done'),
            func.sum(case((Execution.status == ExecutionStatus.FAILED.value, 1), else_=0)).label('failed_status')
        ).filter(
            Execution.duration_seconds.isnot(None)
        ).first()
        
        # Single query for all variation statistics
        var_stats = session.query(
            func.count(Variation.job_id).label('total'),
            func.sum(case((Variation.success == True, 1), else_=0)).label('successful'),
            func.sum(case((Variation.success == False, 1), else_=0)).label('failed'),
            func.avg(Variation.duration_seconds).label('avg_duration'),
            func.sum(case((Variation.status == ExecutionStatus.PENDING.value, 1), else_=0)).label('pending'),
            func.sum(case((Variation.status == ExecutionStatus.TRAINING.value, 1), else_=0)).label('training'),
            func.sum(case((Variation.status == ExecutionStatus.DONE.value, 1), else_=0)).label('done'),
            func.sum(case((Variation.status == ExecutionStatus.FAILED.value, 1), else_=0)).label('failed_status')
        ).filter(
            Variation.duration_seconds.isnot(None)
        ).first()
        
        return {
            'total_executions': exec_stats.total or 0,
            'total_variations': var_stats.total or 0,
            'executions_by_status': {
                'pending': exec_stats.pending or 0,
                'training': exec_stats.training or 0,
                'done': exec_stats.done or 0,
                'failed': exec_stats.failed_status or 0
            },
            'variations_by_status': {
                'pending': var_stats.pending or 0,
                'training': var_stats.training or 0,
                'done': var_stats.done or 0,
                'failed': var_stats.failed_status or 0
            },
            'success_rate': calculate_success_rate(
                (exec_stats.successful or 0) + (var_stats.successful or 0),
                (exec_stats.failed or 0) + (var_stats.failed or 0)
            ),
            'average_duration': calculate_average(
                [exec_stats.avg_duration, var_stats.avg_duration]
            )
        }
    
    @staticmethod
    def batch_update_status(session, job_ids: List[str], status: ExecutionStatus, 
                           error_message: Optional[str] = None) -> int:
        """Batch update status for multiple jobs.
        
        Useful for batch operations to reduce database round trips.
        """
        updated_count = 0
        now = datetime.utcnow()
        
        # Update executions
        exec_count = session.query(Execution).filter(
            Execution.job_id.in_(job_ids)
        ).update({
            'status': status.value,
            'updated_at': now,
            'error_message': error_message,
            'end_time': now if status in [ExecutionStatus.DONE, ExecutionStatus.FAILED] else None,
            'success': True if status == ExecutionStatus.DONE else False
        }, synchronize_session=False)
        
        # Update variations
        var_count = session.query(Variation).filter(
            Variation.job_id.in_(job_ids)
        ).update({
            'status': status.value,
            'updated_at': now,
            'error_message': error_message,
            'end_time': now if status in [ExecutionStatus.DONE, ExecutionStatus.FAILED] else None,
            'success': True if status == ExecutionStatus.DONE else False
        }, synchronize_session=False)
        
        session.commit()
        return exec_count + var_count


def calculate_success_rate(successful: int, failed: int) -> float:
    """Calculate success rate."""
    total = successful + failed
    return successful / total if total > 0 else 0.0


def calculate_average(values: List[Optional[float]]) -> float:
    """Calculate average of non-None values."""
    valid_values = [v for v in values if v is not None]
    return sum(valid_values) / len(valid_values) if valid_values else 0.0