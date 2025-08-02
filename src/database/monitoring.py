"""Database monitoring and health check utilities."""

import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DatabaseHealthMonitor:
    """Monitor database health and performance."""
    
    def __init__(self, db_manager):
        """Initialize health monitor.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.health_history = []
        self.max_history = 100
    
    def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Check connection pool
        pool_status = self._check_connection_pool()
        health_status['checks']['connection_pool'] = pool_status
        
        # Check query performance
        query_perf = self._check_query_performance()
        health_status['checks']['query_performance'] = query_perf
        
        # Check database size
        db_size = self._check_database_size()
        health_status['checks']['database_size'] = db_size
        
        # Check table statistics
        table_stats = self._check_table_statistics()
        health_status['checks']['table_statistics'] = table_stats
        
        # Check for long-running queries
        long_queries = self._check_long_running_queries()
        health_status['checks']['long_running_queries'] = long_queries
        
        # Determine overall status
        if health_status['errors']:
            health_status['status'] = 'critical'
        elif health_status['warnings']:
            health_status['status'] = 'warning'
        
        # Store in history
        self.health_history.append(health_status)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
        
        return health_status
    
    def _check_connection_pool(self) -> Dict[str, Any]:
        """Check connection pool health."""
        try:
            pool_status = self.db_manager.pool_manager.get_pool_status()
            
            # Calculate utilization
            total_connections = pool_status['size'] + pool_status['overflow']
            utilization = (pool_status['checked_out'] / total_connections * 100) if total_connections > 0 else 0
            
            result = {
                'status': 'ok',
                'utilization': f"{utilization:.1f}%",
                'active_connections': pool_status['checked_out'],
                'total_connections': total_connections,
                'connection_errors': pool_status['stats']['connection_errors']
            }
            
            # Check for issues
            if utilization > 80:
                self.health_history[-1]['warnings'].append(
                    f"High connection pool utilization: {utilization:.1f}%"
                )
            
            if pool_status['stats']['connection_errors'] > 10:
                self.health_history[-1]['warnings'].append(
                    f"High connection error count: {pool_status['stats']['connection_errors']}"
                )
            
            return result
            
        except Exception as e:
            self.health_history[-1]['errors'].append(f"Connection pool check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _check_query_performance(self) -> Dict[str, Any]:
        """Check query performance metrics."""
        try:
            metrics = self.db_manager.transaction_metrics.get_metrics()
            
            result = {
                'status': 'ok',
                'average_duration': f"{metrics['average_duration']:.3f}s",
                'success_rate': f"{metrics['success_rate'] * 100:.1f}%",
                'lock_timeouts': metrics['lock_timeouts'],
                'total_transactions': metrics['total_transactions']
            }
            
            # Check for issues
            if metrics['average_duration'] > 1.0:
                self.health_history[-1]['warnings'].append(
                    f"High average query duration: {metrics['average_duration']:.2f}s"
                )
            
            if metrics['success_rate'] < 0.95:
                self.health_history[-1]['warnings'].append(
                    f"Low transaction success rate: {metrics['success_rate'] * 100:.1f}%"
                )
            
            if metrics['lock_timeouts'] > 5:
                self.health_history[-1]['warnings'].append(
                    f"Multiple lock timeouts detected: {metrics['lock_timeouts']}"
                )
            
            return result
            
        except Exception as e:
            self.health_history[-1]['errors'].append(f"Query performance check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _check_database_size(self) -> Dict[str, Any]:
        """Check database file size and growth."""
        try:
            db_path = Path(self.db_manager.db_path)
            db_size = db_path.stat().st_size if db_path.exists() else 0
            
            # Check WAL file size
            wal_path = db_path.with_suffix('.db-wal')
            wal_size = wal_path.stat().st_size if wal_path.exists() else 0
            
            total_size = db_size + wal_size
            
            result = {
                'status': 'ok',
                'database_size': f"{db_size / 1024 / 1024:.2f} MB",
                'wal_size': f"{wal_size / 1024 / 1024:.2f} MB",
                'total_size': f"{total_size / 1024 / 1024:.2f} MB"
            }
            
            # Check for issues
            if total_size > 1024 * 1024 * 1024:  # 1GB
                self.health_history[-1]['warnings'].append(
                    f"Large database size: {total_size / 1024 / 1024 / 1024:.2f} GB"
                )
            
            if wal_size > db_size * 0.5:  # WAL is more than 50% of DB size
                self.health_history[-1]['warnings'].append(
                    "WAL file is large relative to database size"
                )
            
            return result
            
        except Exception as e:
            self.health_history[-1]['errors'].append(f"Database size check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _check_table_statistics(self) -> Dict[str, Any]:
        """Check table row counts and growth."""
        try:
            with self.db_manager.get_session() as session:
                # Get row counts
                exec_count = session.execute(
                    text("SELECT COUNT(*) FROM executions")
                ).scalar()
                
                var_count = session.execute(
                    text("SELECT COUNT(*) FROM variations")
                ).scalar()
                
                # Get recent growth
                recent_date = datetime.utcnow() - timedelta(days=1)
                recent_exec = session.execute(
                    text("SELECT COUNT(*) FROM executions WHERE created_at > :date"),
                    {"date": recent_date}
                ).scalar()
                
                recent_var = session.execute(
                    text("SELECT COUNT(*) FROM variations WHERE created_at > :date"),
                    {"date": recent_date}
                ).scalar()
                
                result = {
                    'status': 'ok',
                    'total_executions': exec_count,
                    'total_variations': var_count,
                    'recent_executions_24h': recent_exec,
                    'recent_variations_24h': recent_var
                }
                
                # Check for issues
                total_rows = exec_count + var_count
                if total_rows > 1000000:
                    self.health_history[-1]['warnings'].append(
                        f"Large number of records: {total_rows:,}"
                    )
                
                return result
                
        except Exception as e:
            self.health_history[-1]['errors'].append(f"Table statistics check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _check_long_running_queries(self) -> Dict[str, Any]:
        """Check for long-running or stuck queries."""
        try:
            with self.db_manager.get_session() as session:
                # Check for old pending jobs
                old_date = datetime.utcnow() - timedelta(hours=24)
                
                old_pending = session.execute(
                    text("""
                        SELECT COUNT(*) FROM (
                            SELECT job_id FROM executions 
                            WHERE status = 'training' AND start_time < :date
                            UNION ALL
                            SELECT job_id FROM variations 
                            WHERE status = 'training' AND start_time < :date
                        )
                    """),
                    {"date": old_date}
                ).scalar()
                
                result = {
                    'status': 'ok',
                    'stuck_jobs': old_pending
                }
                
                if old_pending > 0:
                    self.health_history[-1]['warnings'].append(
                        f"Found {old_pending} jobs stuck in 'training' status for >24 hours"
                    )
                
                return result
                
        except Exception as e:
            self.health_history[-1]['errors'].append(f"Long-running query check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of recent health checks."""
        if not self.health_history:
            return {'status': 'no_data', 'message': 'No health checks performed yet'}
        
        # Analyze recent history
        recent_checks = self.health_history[-10:]  # Last 10 checks
        
        critical_count = sum(1 for h in recent_checks if h['status'] == 'critical')
        warning_count = sum(1 for h in recent_checks if h['status'] == 'warning')
        
        # Aggregate common issues
        all_warnings = []
        all_errors = []
        
        for check in recent_checks:
            all_warnings.extend(check.get('warnings', []))
            all_errors.extend(check.get('errors', []))
        
        # Count occurrences
        from collections import Counter
        warning_counts = Counter(all_warnings)
        error_counts = Counter(all_errors)
        
        return {
            'current_status': self.health_history[-1]['status'],
            'recent_critical': critical_count,
            'recent_warnings': warning_count,
            'common_warnings': dict(warning_counts.most_common(5)),
            'common_errors': dict(error_counts.most_common(5)),
            'last_check': self.health_history[-1]['timestamp']
        }
    
    def export_health_report(self, output_path: Path):
        """Export health report to JSON file."""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'summary': self.get_health_summary(),
            'latest_check': self.health_history[-1] if self.health_history else None,
            'history': self.health_history[-20:]  # Last 20 checks
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Health report exported to {output_path}")