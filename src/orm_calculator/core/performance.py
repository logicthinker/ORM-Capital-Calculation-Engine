"""
Performance monitoring and profiling for ORM Capital Calculator Engine

Provides comprehensive performance monitoring including response times,
memory usage, throughput metrics, and profiling capabilities.
"""

import time
import psutil
import asyncio
import functools
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from enum import Enum

from pydantic import BaseModel
from fastapi import Request, Response


class MetricType(str, Enum):
    """Types of performance metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection"""
    response_times: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    cpu_usage: List[float] = field(default_factory=list)
    request_count: int = 0
    error_count: int = 0
    active_connections: int = 0
    throughput: float = 0.0
    
    def add_response_time(self, duration: float) -> None:
        """Add response time measurement"""
        self.response_times.append(duration)
        # Keep only last 1000 measurements
        if len(self.response_times) > 1000:
            self.response_times.pop(0)
    
    def get_avg_response_time(self) -> float:
        """Get average response time"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
    
    def get_p95_response_time(self) -> float:
        """Get 95th percentile response time"""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(0.95 * len(sorted_times))
        return sorted_times[index] if index < len(sorted_times) else sorted_times[-1]


class MetricsCollector:
    """Collects and stores performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._start_time = datetime.utcnow()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        key = self._build_key(name, labels)
        self._counters[key] += value
        self._add_metric(name, MetricValue(self._counters[key], datetime.utcnow(), labels or {}))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric"""
        key = self._build_key(name, labels)
        self._gauges[key] = value
        self._add_metric(name, MetricValue(value, datetime.utcnow(), labels or {}))
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value"""
        self._add_metric(name, MetricValue(value, datetime.utcnow(), labels or {}))
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a timer duration"""
        self.record_histogram(f"{name}_duration", duration, labels)
    
    def get_metrics(self, name: str) -> List[MetricValue]:
        """Get all metrics for a given name"""
        return list(self._metrics[name])
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value"""
        key = self._build_key(name, labels)
        return self._counters[key]
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current gauge value"""
        key = self._build_key(name, labels)
        return self._gauges[key]
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics"""
        values = [m.value for m in self._metrics[name]]
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "sum": sum(values),
            "avg": sum(values) / count,
            "min": min(values),
            "max": max(values),
            "p50": sorted_values[int(0.5 * count)],
            "p95": sorted_values[int(0.95 * count)],
            "p99": sorted_values[int(0.99 * count)]
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics"""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {name: self.get_histogram_stats(name) for name in self._metrics.keys()},
            "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds()
        }
    
    def _build_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Build metric key with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _add_metric(self, name: str, metric: MetricValue) -> None:
        """Add metric to collection"""
        self._metrics[name].append(metric)


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self):
        self.process = psutil.Process()
        self._last_cpu_times = None
        self._last_check = None
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": self.process.memory_percent(),
            "system_total_mb": system_memory.total / 1024 / 1024,
            "system_available_mb": system_memory.available / 1024 / 1024,
            "system_percent": system_memory.percent
        }
    
    def get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage statistics"""
        cpu_percent = self.process.cpu_percent()
        system_cpu = psutil.cpu_percent(interval=None)
        
        return {
            "process_percent": cpu_percent,
            "system_percent": system_cpu,
            "cpu_count": psutil.cpu_count(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage statistics"""
        disk_usage = psutil.disk_usage('/')
        
        return {
            "total_gb": disk_usage.total / 1024 / 1024 / 1024,
            "used_gb": disk_usage.used / 1024 / 1024 / 1024,
            "free_gb": disk_usage.free / 1024 / 1024 / 1024,
            "percent": (disk_usage.used / disk_usage.total) * 100
        }
    
    def get_network_stats(self) -> Dict[str, int]:
        """Get network statistics"""
        net_io = psutil.net_io_counters()
        
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }


class PerformanceProfiler:
    """Performance profiler for detailed analysis"""
    
    def __init__(self):
        self._profiles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._active_profiles: Dict[str, datetime] = {}
    
    @asynccontextmanager
    async def profile(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for profiling code blocks"""
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            profile_data = {
                "name": name,
                "duration": duration,
                "memory_delta": memory_delta,
                "start_time": datetime.utcnow().isoformat(),
                "labels": labels or {}
            }
            
            self._profiles[name].append(profile_data)
            
            # Keep only last 100 profiles per name
            if len(self._profiles[name]) > 100:
                self._profiles[name].pop(0)
    
    def get_profile_stats(self, name: str) -> Dict[str, Any]:
        """Get profiling statistics for a named operation"""
        profiles = self._profiles[name]
        if not profiles:
            return {"count": 0}
        
        durations = [p["duration"] for p in profiles]
        memory_deltas = [p["memory_delta"] for p in profiles]
        
        return {
            "count": len(profiles),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": sorted(durations)[int(0.95 * len(durations))],
            "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
            "total_memory_delta": sum(memory_deltas)
        }
    
    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all profiling statistics"""
        return {name: self.get_profile_stats(name) for name in self._profiles.keys()}


class PerformanceMonitor:
    """Main performance monitoring service"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.system_monitor = SystemMonitor()
        self.profiler = PerformanceProfiler()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 30  # seconds
    
    async def start_monitoring(self) -> None:
        """Start background monitoring task"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitor_system())
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring task"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_system(self) -> None:
        """Background system monitoring loop"""
        while True:
            try:
                # Collect system metrics
                memory_stats = self.system_monitor.get_memory_usage()
                cpu_stats = self.system_monitor.get_cpu_usage()
                disk_stats = self.system_monitor.get_disk_usage()
                
                # Record metrics
                self.metrics.set_gauge("memory_usage_mb", memory_stats["rss_mb"])
                self.metrics.set_gauge("memory_percent", memory_stats["percent"])
                self.metrics.set_gauge("cpu_usage_percent", cpu_stats["process_percent"])
                self.metrics.set_gauge("system_cpu_percent", cpu_stats["system_percent"])
                self.metrics.set_gauge("disk_usage_percent", disk_stats["percent"])
                
                await asyncio.sleep(self._monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in system monitoring: {e}")
                await asyncio.sleep(self._monitoring_interval)
    
    def record_request(self, method: str, path: str, status_code: int, duration: float) -> None:
        """Record HTTP request metrics"""
        labels = {"method": method, "path": path, "status": str(status_code)}
        
        self.metrics.increment_counter("http_requests_total", labels=labels)
        self.metrics.record_timer("http_request_duration", duration, labels=labels)
        
        if status_code >= 400:
            self.metrics.increment_counter("http_errors_total", labels=labels)
    
    def record_calculation(self, model_name: str, entity_id: str, duration: float, success: bool) -> None:
        """Record calculation metrics"""
        labels = {"model": model_name, "entity": entity_id, "success": str(success)}
        
        self.metrics.increment_counter("calculations_total", labels=labels)
        self.metrics.record_timer("calculation_duration", duration, labels=labels)
        
        if not success:
            self.metrics.increment_counter("calculation_errors_total", labels=labels)
    
    def record_database_query(self, operation: str, table: str, duration: float, success: bool) -> None:
        """Record database query metrics"""
        labels = {"operation": operation, "table": table, "success": str(success)}
        
        self.metrics.increment_counter("db_queries_total", labels=labels)
        self.metrics.record_timer("db_query_duration", duration, labels=labels)
        
        if not success:
            self.metrics.increment_counter("db_errors_total", labels=labels)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            "system": {
                "memory": self.system_monitor.get_memory_usage(),
                "cpu": self.system_monitor.get_cpu_usage(),
                "disk": self.system_monitor.get_disk_usage(),
                "network": self.system_monitor.get_network_stats()
            },
            "metrics": self.metrics.get_all_metrics(),
            "profiles": self.profiler.get_all_profiles()
        }


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def performance_timer(name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator for timing function execution"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                async with monitor.profiler.profile(name, labels):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration = time.perf_counter() - start_time
                    monitor.metrics.record_timer(name, duration, labels)
                    return result
                except Exception as e:
                    duration = time.perf_counter() - start_time
                    error_labels = {**(labels or {}), "error": type(e).__name__}
                    monitor.metrics.record_timer(f"{name}_error", duration, error_labels)
                    raise
            return sync_wrapper
    return decorator


class PerformanceMiddleware:
    """FastAPI middleware for performance monitoring"""
    
    def __init__(self, app):
        self.app = app
        self.monitor = get_performance_monitor()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.perf_counter()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                duration = time.perf_counter() - start_time
                
                # Extract request info
                method = scope["method"]
                path = scope["path"]
                status_code = message["status"]
                
                # Record metrics
                self.monitor.record_request(method, path, status_code, duration)
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)