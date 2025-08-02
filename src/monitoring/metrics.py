"""
Advanced monitoring and metrics system for AutoTrainX
"""
import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import threading

@dataclass
class MetricSnapshot:
    """Snapshot of system metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    gpu_utilization: float = 0.0
    gpu_memory_percent: float = 0.0
    active_jobs: int = 0
    queue_size: int = 0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

class MetricsCollector:
    """Advanced metrics collection and monitoring"""
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.snapshots: deque = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.alerts: List[Dict] = []
        self.alert_handlers: List[Callable] = []
        self.running = False
        
        # Prometheus metrics
        self.setup_prometheus_metrics()
        
        # Alert thresholds
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'gpu_memory_percent': 95.0,
            'training_error_rate': 0.1,
            'queue_wait_time': 600  # 10 minutes
        }
        
    def setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        self.prom_metrics = {
            # Counters
            'training_jobs_total': Counter('autotrainx_training_jobs_total', 'Total training jobs', ['status']),
            'api_requests_total': Counter('autotrainx_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status']),
            'errors_total': Counter('autotrainx_errors_total', 'Total errors', ['category', 'severity']),
            
            # Histograms
            'training_duration': Histogram('autotrainx_training_duration_seconds', 'Training job duration'),
            'api_request_duration': Histogram('autotrainx_api_request_duration_seconds', 'API request duration'),
            'queue_wait_time': Histogram('autotrainx_queue_wait_time_seconds', 'Job queue wait time'),
            
            # Gauges
            'cpu_usage': Gauge('autotrainx_cpu_usage_percent', 'CPU usage percentage'),
            'memory_usage': Gauge('autotrainx_memory_usage_percent', 'Memory usage percentage'),
            'disk_usage': Gauge('autotrainx_disk_usage_percent', 'Disk usage percentage'),
            'gpu_utilization': Gauge('autotrainx_gpu_utilization_percent', 'GPU utilization percentage'),
            'gpu_memory_usage': Gauge('autotrainx_gpu_memory_usage_percent', 'GPU memory usage percentage'),
            'active_jobs': Gauge('autotrainx_active_jobs', 'Number of active training jobs'),
            'queue_size': Gauge('autotrainx_queue_size', 'Number of jobs in queue'),
            'database_connections': Gauge('autotrainx_database_connections', 'Active database connections'),
            
            # Info
            'app_info': Info('autotrainx_app', 'Application information')
        }
        
    def start_monitoring(self, prometheus_port: int = 8001):
        """Start metrics collection and Prometheus server"""
        self.running = True
        
        # Start Prometheus metrics server
        start_http_server(prometheus_port)
        
        # Start collection thread
        collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        collection_thread.start()
        
    def stop_monitoring(self):
        """Stop metrics collection"""
        self.running = False
        
    def _collection_loop(self):
        """Main metrics collection loop"""
        while self.running:
            try:
                snapshot = self._collect_system_metrics()
                self.snapshots.append(snapshot)
                self._update_prometheus_metrics(snapshot)
                self._check_alerts(snapshot)
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Error in metrics collection: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> MetricSnapshot:
        """Collect current system metrics"""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # GPU metrics (if available)
        gpu_util, gpu_memory = self._get_gpu_metrics()
        
        return MetricSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk_percent,
            gpu_utilization=gpu_util,
            gpu_memory_percent=gpu_memory
        )
    
    def _get_gpu_metrics(self) -> tuple:
        """Get GPU utilization and memory usage"""
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # GPU utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util = util.gpu
            
            # GPU memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_memory = (mem_info.used / mem_info.total) * 100
            
            return gpu_util, gpu_memory
        except:
            return 0.0, 0.0
    
    def _update_prometheus_metrics(self, snapshot: MetricSnapshot):
        """Update Prometheus metrics with current snapshot"""
        self.prom_metrics['cpu_usage'].set(snapshot.cpu_percent)
        self.prom_metrics['memory_usage'].set(snapshot.memory_percent)
        self.prom_metrics['disk_usage'].set(snapshot.disk_usage_percent)
        self.prom_metrics['gpu_utilization'].set(snapshot.gpu_utilization)
        self.prom_metrics['gpu_memory_usage'].set(snapshot.gpu_memory_percent)
        self.prom_metrics['active_jobs'].set(snapshot.active_jobs)
        self.prom_metrics['queue_size'].set(snapshot.queue_size)
    
    def _check_alerts(self, snapshot: MetricSnapshot):
        """Check for alert conditions"""
        alerts = []
        
        # CPU alert
        if snapshot.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f'High CPU usage: {snapshot.cpu_percent:.1f}%',
                'value': snapshot.cpu_percent,
                'threshold': self.thresholds['cpu_percent'],
                'timestamp': snapshot.timestamp
            })
        
        # Memory alert
        if snapshot.memory_percent > self.thresholds['memory_percent']:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f'High memory usage: {snapshot.memory_percent:.1f}%',
                'value': snapshot.memory_percent,
                'threshold': self.thresholds['memory_percent'],
                'timestamp': snapshot.timestamp
            })
        
        # Disk alert
        if snapshot.disk_usage_percent > self.thresholds['disk_usage_percent']:
            alerts.append({
                'type': 'high_disk',
                'severity': 'critical',
                'message': f'High disk usage: {snapshot.disk_usage_percent:.1f}%',
                'value': snapshot.disk_usage_percent,
                'threshold': self.thresholds['disk_usage_percent'],
                'timestamp': snapshot.timestamp
            })
        
        # Process alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _handle_alert(self, alert: Dict):
        """Handle alert by calling registered handlers"""
        self.alerts.append(alert)
        
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")
    
    def add_alert_handler(self, handler: Callable[[Dict], None]):
        """Add alert handler function"""
        self.alert_handlers.append(handler)
    
    def record_training_job(self, job_id: str, status: str, duration: float = None):
        """Record training job metrics"""
        self.prom_metrics['training_jobs_total'].labels(status=status).inc()
        
        if duration:
            self.prom_metrics['training_duration'].observe(duration)
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics"""
        status = 'success' if 200 <= status_code < 300 else 'error'
        self.prom_metrics['api_requests_total'].labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        self.prom_metrics['api_request_duration'].observe(duration)
    
    def record_error(self, category: str, severity: str):
        """Record error metrics"""
        self.prom_metrics['errors_total'].labels(
            category=category,
            severity=severity
        ).inc()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        if not self.snapshots:
            return {}
        
        latest = self.snapshots[-1]
        return {
            'timestamp': latest.timestamp.isoformat(),
            'cpu_percent': latest.cpu_percent,
            'memory_percent': latest.memory_percent,
            'disk_usage_percent': latest.disk_usage_percent,
            'gpu_utilization': latest.gpu_utilization,
            'gpu_memory_percent': latest.gpu_memory_percent,
            'active_jobs': latest.active_jobs,
            'queue_size': latest.queue_size
        }
    
    def get_historical_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical metrics for specified hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            {
                'timestamp': snapshot.timestamp.isoformat(),
                'cpu_percent': snapshot.cpu_percent,
                'memory_percent': snapshot.memory_percent,
                'disk_usage_percent': snapshot.disk_usage_percent,
                'gpu_utilization': snapshot.gpu_utilization,
                'gpu_memory_percent': snapshot.gpu_memory_percent,
                'active_jobs': snapshot.active_jobs,
                'queue_size': snapshot.queue_size
            }
            for snapshot in self.snapshots
            if snapshot.timestamp > cutoff
        ]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alerts
            if alert['timestamp'] > cutoff
        ]

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.checks = []
        
    def add_check(self, name: str, check_func: Callable[[], bool], critical: bool = False):
        """Add health check"""
        self.checks.append({
            'name': name,
            'func': check_func,
            'critical': critical
        })
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = 'healthy'
        
        for check in self.checks:
            try:
                result = check['func']()
                results[check['name']] = {
                    'status': 'pass' if result else 'fail',
                    'critical': check['critical']
                }
                
                if not result and check['critical']:
                    overall_status = 'unhealthy'
                elif not result:
                    overall_status = 'degraded'
                    
            except Exception as e:
                results[check['name']] = {
                    'status': 'error',
                    'error': str(e),
                    'critical': check['critical']
                }
                
                if check['critical']:
                    overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': results
        }

# Global metrics collector instance
metrics_collector: Optional[MetricsCollector] = None
health_checker = HealthChecker()

def setup_monitoring(collection_interval: int = 30, prometheus_port: int = 8001):
    """Setup global monitoring"""
    global metrics_collector
    metrics_collector = MetricsCollector(collection_interval)
    metrics_collector.start_monitoring(prometheus_port)
    
    # Add default health checks
    health_checker.add_check('disk_space', lambda: psutil.disk_usage('/').percent < 90, critical=True)
    health_checker.add_check('memory_usage', lambda: psutil.virtual_memory().percent < 90, critical=True)
    
    return metrics_collector

def get_metrics() -> MetricsCollector:
    """Get global metrics collector"""
    return metrics_collector