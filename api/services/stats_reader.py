"""
Statistics Reader Service - Read-only access to PostgreSQL statistics.

This service provides read-only access to training statistics and job information
stored in the PostgreSQL database by the main AutoTrainX application.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

logger = logging.getLogger(__name__)


class StatsReader:
    """Read-only access to training statistics from PostgreSQL."""
    
    def __init__(self):
        """Initialize database connection parameters."""
        self.db_config = {
            'host': os.getenv('DATABASE_HOST') or os.getenv('AUTOTRAINX_DB_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT') or os.getenv('AUTOTRAINX_DB_PORT', 5432)),
            'database': os.getenv('DATABASE_NAME') or os.getenv('AUTOTRAINX_DB_NAME', 'autotrainx'),
            'user': os.getenv('DATABASE_USER') or os.getenv('AUTOTRAINX_DB_USER', 'autotrainx'),
            'password': os.getenv('DATABASE_PASSWORD') or os.getenv('AUTOTRAINX_DB_PASSWORD', '1234')
        }
    
    def _get_connection(self):
        """Get database connection with dict cursor."""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    async def get_job_by_id(self, job_id: str) -> Optional[Dict]:
        """
        Get job information by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job information or None if not found
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            job_id,
                            dataset_name,
                            pipeline_mode,
                            preset,
                            status,
                            created_at,
                            start_time,
                            end_time,
                            output_path,
                            error_message,
                            total_steps,
                            current_step,
                            success
                        FROM executions
                        WHERE job_id = %s
                    """, (job_id,))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    async def get_jobs_list(self, 
                           limit: int = 20,
                           offset: int = 0,
                           status: Optional[str] = None,
                           mode: Optional[str] = None) -> Tuple[List[Dict], int]:
        """
        Get list of jobs with pagination and filtering.
        
        Args:
            limit: Number of jobs to return
            offset: Offset for pagination
            status: Filter by status
            mode: Filter by pipeline mode
            
        Returns:
            Tuple of (jobs list, total count)
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Build query conditions
                    conditions = []
                    params = []
                    
                    if status:
                        conditions.append("status = %s")
                        params.append(status)
                        
                    if mode:
                        conditions.append("pipeline_mode = %s")
                        params.append(mode)
                    
                    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                    
                    # Get total count
                    count_query = f"SELECT COUNT(*) as total FROM executions {where_clause}"
                    cursor.execute(count_query, params)
                    total = cursor.fetchone()['total']
                    
                    # Get jobs
                    query = f"""
                        SELECT 
                            job_id,
                            dataset_name,
                            pipeline_mode,
                            preset,
                            status,
                            created_at,
                            start_time,
                            end_time,
                            success,
                            error_message
                        FROM executions
                        {where_clause}
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """
                    
                    cursor.execute(query, params + [limit, offset])
                    jobs = [dict(row) for row in cursor.fetchall()]
                    
                    return jobs, total
                    
        except Exception as e:
            logger.error(f"Failed to get jobs list: {e}")
            return [], 0
    
    async def get_job_statistics(self) -> Dict:
        """
        Get overall job statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get status counts
                    cursor.execute("""
                        SELECT 
                            status,
                            COUNT(*) as count
                        FROM executions
                        GROUP BY status
                    """)
                    status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
                    
                    # Get mode counts
                    cursor.execute("""
                        SELECT 
                            pipeline_mode,
                            COUNT(*) as count
                        FROM executions
                        GROUP BY pipeline_mode
                    """)
                    mode_counts = {row['pipeline_mode']: row['count'] for row in cursor.fetchall()}
                    
                    # Get success rate
                    cursor.execute("""
                        SELECT 
                            COUNT(CASE WHEN success = true THEN 1 END) as successful,
                            COUNT(*) as total
                        FROM executions
                        WHERE status IN ('done', 'failed')
                    """)
                    result = cursor.fetchone()
                    success_rate = (result['successful'] / result['total'] * 100) if result['total'] > 0 else 0
                    
                    # Get recent activity
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as jobs_24h
                        FROM executions
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                    """)
                    jobs_24h = cursor.fetchone()['jobs_24h']
                    
                    return {
                        'status_breakdown': status_counts,
                        'mode_breakdown': mode_counts,
                        'success_rate': round(success_rate, 2),
                        'total_jobs': sum(status_counts.values()),
                        'jobs_last_24h': jobs_24h
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'status_breakdown': {},
                'mode_breakdown': {},
                'success_rate': 0,
                'total_jobs': 0,
                'jobs_last_24h': 0
            }
    
    async def get_running_jobs(self) -> List[Dict]:
        """
        Get currently running jobs.
        
        Returns:
            List of running jobs
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            job_id,
                            dataset_name,
                            pipeline_mode,
                            preset,
                            status,
                            start_time,
                            current_step,
                            total_steps,
                            EXTRACT(EPOCH FROM (NOW() - start_time)) as elapsed_seconds
                        FROM executions
                        WHERE status IN ('training', 'preparing_dataset', 'configuring_preset', 'generating_preview')
                        ORDER BY start_time DESC
                    """)
                    
                    jobs = []
                    for row in cursor.fetchall():
                        job = dict(row)
                        # Calculate progress
                        if job['total_steps'] and job['current_step']:
                            job['progress_percentage'] = (job['current_step'] / job['total_steps']) * 100
                        else:
                            job['progress_percentage'] = 0
                        jobs.append(job)
                    
                    return jobs
                    
        except Exception as e:
            logger.error(f"Failed to get running jobs: {e}")
            return []
    
    async def get_recent_completions(self, limit: int = 10) -> List[Dict]:
        """
        Get recently completed jobs.
        
        Args:
            limit: Number of jobs to return
            
        Returns:
            List of completed jobs
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            job_id,
                            dataset_name,
                            pipeline_mode,
                            preset,
                            status,
                            created_at,
                            end_time,
                            success,
                            EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds
                        FROM executions
                        WHERE status IN ('done', 'failed', 'cancelled')
                        AND end_time IS NOT NULL
                        ORDER BY end_time DESC
                        LIMIT %s
                    """, (limit,))
                    
                    return [dict(row) for row in cursor.fetchall()]
                    
        except Exception as e:
            logger.error(f"Failed to get recent completions: {e}")
            return []
    
    async def get_preset_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics grouped by preset.
        
        Returns:
            Dictionary with preset statistics
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            preset,
                            COUNT(*) as total_jobs,
                            COUNT(CASE WHEN success = true THEN 1 END) as successful_jobs,
                            AVG(CASE WHEN success = true AND end_time IS NOT NULL 
                                THEN EXTRACT(EPOCH FROM (end_time - start_time)) 
                                END) as avg_duration_seconds
                        FROM executions
                        WHERE status IN ('done', 'failed')
                        GROUP BY preset
                        ORDER BY total_jobs DESC
                    """)
                    
                    stats = {}
                    for row in cursor.fetchall():
                        stats[row['preset']] = {
                            'total_jobs': row['total_jobs'],
                            'successful_jobs': row['successful_jobs'],
                            'success_rate': (row['successful_jobs'] / row['total_jobs'] * 100) if row['total_jobs'] > 0 else 0,
                            'avg_duration_minutes': round(row['avg_duration_seconds'] / 60, 2) if row['avg_duration_seconds'] else None
                        }
                    
                    return stats
                    
        except Exception as e:
            logger.error(f"Failed to get preset statistics: {e}")
            return {}