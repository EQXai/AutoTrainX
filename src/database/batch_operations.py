"""Batch operations for improved database performance."""

import logging
from typing import List, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, case, func
from sqlalchemy.dialects.postgresql import insert

from .models import Execution, Variation, JobSummaryCache
from .enums import ExecutionStatus

logger = logging.getLogger(__name__)


class BatchOperationsMixin:
    """Mixin class providing batch operation methods for database manager."""
    
    def batch_update_execution_status(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update multiple execution statuses.
        
        Args:
            updates: List of dictionaries with 'job_id', 'status', and optional 'error_message'
            
        Returns:
            Number of records updated
        """
        def _batch_update():
            with self.transaction_metrics.track_transaction("batch_update_executions"):
                with self.get_session() as session:
                    updated_count = 0
                    now = datetime.utcnow()
                    
                    # Group updates by status for efficiency
                    status_groups = {}
                    for update in updates:
                        status = update['status']
                        if status not in status_groups:
                            status_groups[status] = []
                        status_groups[status].append(update)
                    
                    # Execute batch updates per status
                    for status, items in status_groups.items():
                        job_ids = [item['job_id'] for item in items]
                        
                        update_values = {
                            'status': status.value,
                            'updated_at': now,
                        }
                        
                        if status == ExecutionStatus.DONE:
                            update_values.update({
                                'end_time': now,
                                'success': True
                            })
                        elif status == ExecutionStatus.FAILED:
                            update_values.update({
                                'end_time': now,
                                'success': False
                            })
                        
                        count = session.query(Execution).filter(
                            Execution.job_id.in_(job_ids)
                        ).update(update_values, synchronize_session=False)
                        
                        updated_count += count
                        
                        # Handle error messages for failed jobs
                        if status == ExecutionStatus.FAILED:
                            for item in items:
                                if 'error_message' in item:
                                    session.query(Execution).filter_by(
                                        job_id=item['job_id']
                                    ).update({
                                        'error_message': item['error_message']
                                    })
                    
                    session.commit()
                    
                    # Batch update cache
                    self._batch_update_cache_for_jobs(session, job_ids, 'execution')
                    
                    return updated_count
        
        return self._retry_on_lock(_batch_update)
    
    def batch_update_variation_status(self, updates: List[Dict[str, Any]]) -> int:
        """Batch update multiple variation statuses.
        
        Args:
            updates: List of dictionaries with 'job_id', 'status', and optional 'error_message'
            
        Returns:
            Number of records updated
        """
        def _batch_update():
            with self.transaction_metrics.track_transaction("batch_update_variations"):
                with self.get_session() as session:
                    updated_count = 0
                    now = datetime.utcnow()
                    
                    # Similar logic to batch_update_execution_status
                    status_groups = {}
                    for update in updates:
                        status = update['status']
                        if status not in status_groups:
                            status_groups[status] = []
                        status_groups[status].append(update)
                    
                    for status, items in status_groups.items():
                        job_ids = [item['job_id'] for item in items]
                        
                        update_values = {
                            'status': status.value,
                            'updated_at': now,
                        }
                        
                        if status == ExecutionStatus.DONE:
                            update_values.update({
                                'end_time': now,
                                'success': True
                            })
                        elif status == ExecutionStatus.FAILED:
                            update_values.update({
                                'end_time': now,
                                'success': False
                            })
                        elif status == ExecutionStatus.TRAINING:
                            update_values['start_time'] = now
                        
                        count = session.query(Variation).filter(
                            Variation.job_id.in_(job_ids)
                        ).update(update_values, synchronize_session=False)
                        
                        updated_count += count
                    
                    session.commit()
                    
                    # Batch update cache
                    self._batch_update_cache_for_jobs(session, job_ids, 'variation')
                    
                    return updated_count
        
        return self._retry_on_lock(_batch_update)
    
    def _batch_update_cache_for_jobs(self, session: Session, job_ids: List[str], job_type: str):
        """Batch update job cache for multiple jobs.
        
        Args:
            session: Database session
            job_ids: List of job IDs to update
            job_type: Type of job ('execution' or 'variation')
        """
        if not job_ids:
            return
        
        if job_type == 'execution':
            model = Execution
        else:
            model = Variation
        
        # Fetch all jobs
        jobs = session.query(model).filter(model.job_id.in_(job_ids)).all()
        
        if self.config.db_type == 'postgresql':
            # Use PostgreSQL UPSERT
            values = []
            for job in jobs:
                values.append({
                    'job_id': job.job_id,
                    'job_type': job_type,
                    'status': job.status,
                    'dataset_name': job.dataset_name,
                    'preset': job.preset,
                    'start_time': job.start_time,
                    'duration_seconds': getattr(job, 'duration_seconds', None),
                    'success': getattr(job, 'success', None),
                    'last_updated': datetime.utcnow()
                })
            
            if values:
                stmt = insert(JobSummaryCache).values(values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['job_id'],
                    set_={
                        'status': stmt.excluded.status,
                        'dataset_name': stmt.excluded.dataset_name,
                        'preset': stmt.excluded.preset,
                        'start_time': stmt.excluded.start_time,
                        'duration_seconds': stmt.excluded.duration_seconds,
                        'success': stmt.excluded.success,
                        'last_updated': stmt.excluded.last_updated
                    }
                )
                session.execute(stmt)
        else:
            # SQLite fallback
            for job in jobs:
                cache_entry = session.query(JobSummaryCache).filter_by(
                    job_id=job.job_id
                ).first()
                
                if cache_entry:
                    # Update existing
                    cache_entry.status = job.status
                    cache_entry.dataset_name = job.dataset_name
                    cache_entry.preset = job.preset
                    cache_entry.start_time = job.start_time
                    cache_entry.duration_seconds = getattr(job, 'duration_seconds', None)
                    cache_entry.success = getattr(job, 'success', None)
                    cache_entry.last_updated = datetime.utcnow()
                else:
                    # Insert new
                    cache_entry = JobSummaryCache(
                        job_id=job.job_id,
                        job_type=job_type,
                        status=job.status,
                        dataset_name=job.dataset_name,
                        preset=job.preset,
                        start_time=job.start_time,
                        duration_seconds=getattr(job, 'duration_seconds', None),
                        success=getattr(job, 'success', None),
                        last_updated=datetime.utcnow()
                    )
                    session.add(cache_entry)
    
    def refresh_job_cache_optimized(self):
        """Optimized cache refresh using bulk operations."""
        with self.bulk_session() as session:
            if self.config.db_type == 'postgresql':
                # PostgreSQL optimized refresh
                session.execute(text("""
                    TRUNCATE job_summary_cache;
                    
                    INSERT INTO job_summary_cache 
                    (job_id, job_type, status, dataset_name, preset, start_time, 
                     duration_seconds, success, last_updated)
                    SELECT 
                        job_id, 'execution', status, dataset_name, preset, 
                        start_time, duration_seconds, success, CURRENT_TIMESTAMP
                    FROM executions
                    UNION ALL
                    SELECT 
                        job_id, 'variation', status, dataset_name, preset, 
                        start_time, duration_seconds, success, CURRENT_TIMESTAMP
                    FROM variations;
                """))
            else:
                # SQLite optimized refresh
                session.execute(text("DELETE FROM job_summary_cache"))
                session.execute(text("""
                    INSERT INTO job_summary_cache 
                    (job_id, job_type, status, dataset_name, preset, start_time, 
                     duration_seconds, success, last_updated)
                    SELECT 
                        job_id, 'execution', status, dataset_name, preset, 
                        start_time, duration_seconds, success, CURRENT_TIMESTAMP
                    FROM executions
                    UNION ALL
                    SELECT 
                        job_id, 'variation', status, dataset_name, preset, 
                        start_time, duration_seconds, success, CURRENT_TIMESTAMP
                    FROM variations
                """))
            
            session.commit()
            logger.info("Job summary cache refreshed with optimized bulk operation")
    
    def batch_create_executions(self, executions: List[Dict[str, Any]]) -> List[str]:
        """Create multiple executions in a single transaction.
        
        Args:
            executions: List of execution data dictionaries
            
        Returns:
            List of created job IDs
        """
        def _batch_create():
            with self.transaction_metrics.track_transaction("batch_create_executions"):
                with self.get_session() as session:
                    created_jobs = []
                    
                    for exec_data in executions:
                        execution = Execution(
                            job_id=exec_data['job_id'],
                            pipeline_mode=exec_data['pipeline_mode'],
                            dataset_name=exec_data['dataset_name'],
                            preset=exec_data['preset'],
                            total_steps=exec_data.get('total_steps'),
                            status=ExecutionStatus.PENDING.value,
                            start_time=datetime.utcnow()
                        )
                        session.add(execution)
                        created_jobs.append(execution.job_id)
                    
                    session.commit()
                    
                    # Batch update cache
                    self._batch_update_cache_for_jobs(session, created_jobs, 'execution')
                    
                    return created_jobs
        
        return self._retry_on_lock(_batch_create)