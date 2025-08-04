"""Optimized database queries for better performance."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, case, text, and_, or_
from sqlalchemy.orm import Session

from .models import Execution, Variation, JobSummaryCache
from .enums import ExecutionStatus

logger = logging.getLogger(__name__)


class OptimizedQueriesMixin:
    """Mixin providing optimized query implementations."""
    
    def get_statistics_optimized(self) -> Dict[str, Any]:
        """Get overall database statistics with optimized queries.
        
        Uses single aggregate queries instead of multiple COUNT queries.
        
        Returns:
            Dictionary with statistics
        """
        with self.get_session() as session:
            # Single query for all execution statistics
            exec_stats = session.query(
                func.count(Execution.job_id).label('total'),
                func.sum(case((Execution.success == True, 1), else_=0)).label('successful'),
                func.sum(case((Execution.success == False, 1), else_=0)).label('failed'),
                func.sum(case((Execution.status == ExecutionStatus.PENDING.value, 1), else_=0)).label('pending'),
                func.sum(case((Execution.status == ExecutionStatus.TRAINING.value, 1), else_=0)).label('training'),
                func.sum(case((Execution.status == ExecutionStatus.DONE.value, 1), else_=0)).label('done'),
                func.sum(case((Execution.status == ExecutionStatus.FAILED.value, 1), else_=0)).label('failed_status'),
                func.avg(Execution.duration_seconds).label('avg_duration')
            ).first()
            
            # Single query for all variation statistics
            var_stats = session.query(
                func.count(Variation.job_id).label('total'),
                func.sum(case((Variation.success == True, 1), else_=0)).label('successful'),
                func.sum(case((Variation.success == False, 1), else_=0)).label('failed'),
                func.sum(case((Variation.status == ExecutionStatus.PENDING.value, 1), else_=0)).label('pending'),
                func.sum(case((Variation.status == ExecutionStatus.TRAINING.value, 1), else_=0)).label('training'),
                func.sum(case((Variation.status == ExecutionStatus.DONE.value, 1), else_=0)).label('done'),
                func.sum(case((Variation.status == ExecutionStatus.FAILED.value, 1), else_=0)).label('failed_status'),
                func.avg(Variation.duration_seconds).label('avg_duration')
            ).first()
            
            # Build response
            total_executions = exec_stats.total or 0
            total_variations = var_stats.total or 0
            total_jobs = total_executions + total_variations
            
            total_successful = (exec_stats.successful or 0) + (var_stats.successful or 0)
            total_failed = (exec_stats.failed or 0) + (var_stats.failed or 0)
            total_completed = total_successful + total_failed
            
            success_rate = (total_successful / total_completed * 100) if total_completed > 0 else 0.0
            
            # Build status breakdown
            exec_by_status = {}
            var_by_status = {}
            
            for status in ExecutionStatus:
                exec_count = getattr(exec_stats, status.value.lower(), 0) or 0
                var_count = getattr(var_stats, status.value.lower(), 0) or 0
                
                if exec_count > 0:
                    exec_by_status[status.value] = exec_count
                if var_count > 0:
                    var_by_status[status.value] = var_count
            
            return {
                'total_executions': total_executions,
                'total_variations': total_variations,
                'total_jobs': total_jobs,
                'executions_by_status': exec_by_status,
                'variations_by_status': var_by_status,
                'success_rate': success_rate,
                'total_successful': total_successful,
                'total_failed': total_failed,
                'avg_execution_duration': exec_stats.avg_duration,
                'avg_variation_duration': var_stats.avg_duration,
            }
    
    def get_all_jobs_optimized(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all jobs with single UNION query for better performance.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of job dictionaries
        """
        with self.get_session() as session:
            if self.config.db_type == 'postgresql':
                query = text("""
                    SELECT * FROM (
                        SELECT 
                            job_id, status, dataset_name, preset, start_time, 
                            created_at, updated_at, 'execution' as job_type, 
                            pipeline_mode as mode,
                            NULL as experiment_name, NULL as variation_id,
                            success, duration_seconds, error_message, output_path,
                            total_steps, current_step
                        FROM executions
                        
                        UNION ALL
                        
                        SELECT 
                            job_id, status, dataset_name, preset, start_time,
                            created_at, updated_at, 'variation' as job_type, 
                            'variations' as mode,
                            experiment_name, variation_id,
                            success, duration_seconds, error_message, output_path,
                            NULL as total_steps, NULL as current_step
                        FROM variations
                    ) AS combined
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            else:  # SQLite
                query = text("""
                    SELECT * FROM (
                        SELECT 
                            job_id, status, dataset_name, preset, start_time, 
                            created_at, updated_at, 'execution' as job_type, 
                            pipeline_mode as mode,
                            NULL as experiment_name, NULL as variation_id,
                            success, duration_seconds, error_message, output_path,
                            total_steps, current_step
                        FROM executions
                        
                        UNION ALL
                        
                        SELECT 
                            job_id, status, dataset_name, preset, start_time,
                            created_at, updated_at, 'variation' as job_type, 
                            'variations' as mode,
                            experiment_name, variation_id,
                            success, duration_seconds, error_message, output_path,
                            NULL as total_steps, NULL as current_step
                        FROM variations
                    ) AS combined
                    ORDER BY created_at DESC
                    LIMIT :limit
                """)
            
            result = session.execute(query, {"limit": limit})
            
            jobs = []
            for row in result:
                job_dict = dict(row._mapping)
                # Convert datetime objects to ISO format
                for field in ['start_time', 'created_at', 'updated_at']:
                    if job_dict.get(field):
                        job_dict[field] = job_dict[field].isoformat()
                jobs.append(job_dict)
            
            return jobs
    
    def get_dataset_stats_optimized(self, dataset_name: str) -> Dict[str, Any]:
        """Get statistics for a specific dataset using optimized queries.
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Dictionary with dataset statistics
        """
        with self.get_session() as session:
            # Use cache table for better performance
            stats = session.query(
                func.count(JobSummaryCache.job_id).label('total'),
                func.sum(case((JobSummaryCache.success == True, 1), else_=0)).label('successful'),
                func.sum(case((JobSummaryCache.success == False, 1), else_=0)).label('failed'),
                func.avg(JobSummaryCache.duration_seconds).label('avg_duration'),
                func.min(JobSummaryCache.duration_seconds).label('min_duration'),
                func.max(JobSummaryCache.duration_seconds).label('max_duration'),
                func.min(JobSummaryCache.start_time).label('first_run'),
                func.max(JobSummaryCache.start_time).label('last_run')
            ).filter(
                JobSummaryCache.dataset_name == dataset_name
            ).first()
            
            # Get job type breakdown
            type_breakdown = session.query(
                JobSummaryCache.job_type,
                func.count(JobSummaryCache.job_id).label('count')
            ).filter(
                JobSummaryCache.dataset_name == dataset_name
            ).group_by(
                JobSummaryCache.job_type
            ).all()
            
            job_types = {row.job_type: row.count for row in type_breakdown}
            
            return {
                'dataset_name': dataset_name,
                'total_jobs': stats.total or 0,
                'successful_jobs': stats.successful or 0,
                'failed_jobs': stats.failed or 0,
                'average_duration': stats.avg_duration,
                'min_duration': stats.min_duration,
                'max_duration': stats.max_duration,
                'first_run': stats.first_run.isoformat() if stats.first_run else None,
                'last_run': stats.last_run.isoformat() if stats.last_run else None,
                'executions': job_types.get('execution', 0),
                'variations': job_types.get('variation', 0),
                'success_rate': (
                    (stats.successful / stats.total * 100) 
                    if stats.total and stats.total > 0 else 0.0
                )
            }
    
    def get_running_jobs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all currently running jobs efficiently.
        
        Returns:
            Dictionary with 'executions' and 'variations' lists
        """
        with self.get_session() as session:
            # Use indexed queries for running jobs
            running_execs = session.query(
                Execution.job_id,
                Execution.status,
                Execution.dataset_name,
                Execution.start_time,
                Execution.current_step,
                Execution.total_steps
            ).filter(
                Execution.status.in_([
                    ExecutionStatus.PENDING.value,
                    ExecutionStatus.TRAINING.value
                ])
            ).order_by(Execution.created_at.desc()).all()
            
            running_vars = session.query(
                Variation.job_id,
                Variation.status,
                Variation.dataset_name,
                Variation.start_time,
                Variation.experiment_name,
                Variation.variation_id
            ).filter(
                Variation.status.in_([
                    ExecutionStatus.PENDING.value,
                    ExecutionStatus.TRAINING.value
                ])
            ).order_by(Variation.created_at.desc()).all()
            
            return {
                'executions': [
                    {
                        'job_id': e.job_id,
                        'status': e.status,
                        'dataset_name': e.dataset_name,
                        'start_time': e.start_time.isoformat() if e.start_time else None,
                        'current_step': e.current_step,
                        'total_steps': e.total_steps,
                        'progress': (
                            (e.current_step / e.total_steps * 100) 
                            if e.current_step and e.total_steps else 0
                        )
                    }
                    for e in running_execs
                ],
                'variations': [
                    {
                        'job_id': v.job_id,
                        'status': v.status,
                        'dataset_name': v.dataset_name,
                        'start_time': v.start_time.isoformat() if v.start_time else None,
                        'experiment_name': v.experiment_name,
                        'variation_id': v.variation_id
                    }
                    for v in running_vars
                ]
            }
    
    def cleanup_old_jobs(self, days: int = 30, keep_failed: bool = True) -> Dict[str, int]:
        """Clean up old job records efficiently.
        
        Args:
            days: Delete jobs older than this many days
            keep_failed: If True, keep failed jobs for debugging
            
        Returns:
            Dictionary with counts of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with self.get_session() as session:
            # Build base filters
            exec_filter = Execution.created_at < cutoff_date
            var_filter = Variation.created_at < cutoff_date
            
            if keep_failed:
                exec_filter = and_(exec_filter, Execution.success == True)
                var_filter = and_(var_filter, Variation.success == True)
            
            # Delete old executions
            exec_count = session.query(Execution).filter(exec_filter).delete(
                synchronize_session=False
            )
            
            # Delete old variations
            var_count = session.query(Variation).filter(var_filter).delete(
                synchronize_session=False
            )
            
            # Clean up cache entries
            cache_count = session.query(JobSummaryCache).filter(
                JobSummaryCache.last_updated < cutoff_date
            ).delete(synchronize_session=False)
            
            session.commit()
            
            logger.info(
                f"Cleaned up {exec_count} executions, {var_count} variations, "
                f"and {cache_count} cache entries older than {days} days"
            )
            
            return {
                'executions_deleted': exec_count,
                'variations_deleted': var_count,
                'cache_entries_deleted': cache_count
            }