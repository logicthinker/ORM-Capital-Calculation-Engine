"""
Performance Analyzer for Automated Testing Framework

Provides comprehensive performance testing, monitoring, and analysis capabilities
for the ORM Capital Calculator Engine.
"""

import time
import psutil
import asyncio
import threading
import statistics
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    test_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    peak_memory_mb: float
    peak_cpu_percent: float
    throughput_ops_per_sec: Optional[float] = None
    latency_p50: Optional[float] = None
    latency_p95: Optional[float] = None
    latency_p99: Optional[float] = None
    error_rate: Optional[float] = None
    concurrent_users: Optional[int] = None


@dataclass
class SLARequirements:
    """SLA requirements for performance testing"""
    max_response_time_seconds: float
    max_memory_mb: float
    min_throughput_ops_per_sec: float
    max_cpu_percent: float
    max_error_rate_percent: float
    concurrent_users_target: int


class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.start_time = None
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self, interval: float = 0.1):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        self.metrics = []
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,)
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> PerformanceMetrics:
        """Stop monitoring and return metrics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        
        return self._calculate_metrics()
    
    def _monitor_loop(self, interval: float):
        """Monitoring loop"""
        while self.monitoring:
            try:
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent()
                
                self.metrics.append({
                    'timestamp': time.time(),
                    'memory_mb': memory_info.used / (1024 * 1024),
                    'memory_percent': memory_info.percent,
                    'cpu_percent': cpu_percent
                })
                
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                break
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from collected data"""
        if not self.metrics:
            return {}
        
        memory_values = [m['memory_mb'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'execution_time': execution_time,
            'memory_usage_mb': statistics.mean(memory_values),
            'peak_memory_mb': max(memory_values),
            'cpu_usage_percent': statistics.mean(cpu_values),
            'peak_cpu_percent': max(cpu_values),
            'sample_count': len(self.metrics)
        }


class PerformanceAnalyzer:
    """Comprehensive performance analysis and testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = []
        
    def generate_load_config(self) -> Dict[str, Any]:
        """Generate load test configuration"""
        import random
        
        load_patterns = [
            'constant_load',
            'ramp_up_load',
            'spike_load',
            'step_load',
            'random_load'
        ]
        
        pattern = random.choice(load_patterns)
        
        if pattern == 'constant_load':
            return {
                'pattern': pattern,
                'concurrent_users': random.randint(10, 100),
                'duration_seconds': random.randint(60, 300),
                'requests_per_user': random.randint(10, 50)
            }
        elif pattern == 'ramp_up_load':
            return {
                'pattern': pattern,
                'start_users': random.randint(1, 10),
                'end_users': random.randint(50, 200),
                'ramp_duration_seconds': random.randint(60, 180),
                'hold_duration_seconds': random.randint(120, 300)
            }
        elif pattern == 'spike_load':
            return {
                'pattern': pattern,
                'baseline_users': random.randint(10, 30),
                'spike_users': random.randint(100, 500),
                'spike_duration_seconds': random.randint(30, 120),
                'total_duration_seconds': random.randint(300, 600)
            }
        else:
            return {
                'pattern': pattern,
                'min_users': random.randint(5, 20),
                'max_users': random.randint(50, 150),
                'duration_seconds': random.randint(180, 400)
            }
    
    def generate_stress_config(self) -> Dict[str, Any]:
        """Generate stress test configuration"""
        import random
        
        stress_types = [
            'cpu_intensive',
            'memory_intensive',
            'io_intensive',
            'concurrent_intensive',
            'data_volume_intensive'
        ]
        
        stress_type = random.choice(stress_types)
        
        if stress_type == 'cpu_intensive':
            return {
                'type': stress_type,
                'calculation_complexity': random.choice(['high', 'extreme']),
                'concurrent_calculations': random.randint(50, 200),
                'duration_seconds': random.randint(300, 1800)
            }
        elif stress_type == 'memory_intensive':
            return {
                'type': stress_type,
                'data_size_mb': random.randint(500, 2000),
                'concurrent_operations': random.randint(20, 100),
                'duration_seconds': random.randint(180, 900)
            }
        elif stress_type == 'data_volume_intensive':
            return {
                'type': stress_type,
                'entities_count': random.randint(1000, 10000),
                'years_of_data': random.randint(10, 20),
                'losses_per_entity_per_year': random.randint(50, 200)
            }
        else:
            return {
                'type': stress_type,
                'concurrent_users': random.randint(100, 1000),
                'operations_per_user': random.randint(100, 500),
                'duration_seconds': random.randint(600, 1800)
            }
    
    def generate_scale_config(self) -> Dict[str, Any]:
        """Generate scalability test configuration"""
        import random
        
        return {
            'user_ramp_steps': [10, 25, 50, 75, 100, 150, 200],
            'step_duration_seconds': random.randint(60, 180),
            'metrics_collection_interval': 5,
            'target_response_time_ms': random.randint(1000, 5000),
            'target_throughput_rps': random.randint(10, 100),
            'resource_limits': {
                'max_memory_mb': random.randint(1024, 4096),
                'max_cpu_percent': random.randint(70, 90)
            }
        }
    
    def generate_memory_config(self) -> Dict[str, Any]:
        """Generate memory test configuration"""
        import random
        
        return {
            'test_scenarios': [
                'memory_leak_detection',
                'large_dataset_processing',
                'concurrent_memory_usage',
                'garbage_collection_impact'
            ],
            'data_sizes': [100, 500, 1000, 2000, 5000],  # MB
            'concurrent_operations': random.randint(10, 50),
            'duration_seconds': random.randint(300, 1200),
            'memory_sampling_interval': 1.0,
            'gc_monitoring': True
        }
    
    async def run_load_test(self, config: Dict[str, Any], test_function: Callable) -> PerformanceMetrics:
        """Run load test with specified configuration"""
        self.logger.info(f"Starting load test with config: {config}")
        
        monitor = PerformanceMonitor()
        monitor.start_monitoring()
        
        start_time = time.time()
        results = []
        errors = 0
        
        try:
            if config['pattern'] == 'constant_load':
                results = await self._run_constant_load(config, test_function)
            elif config['pattern'] == 'ramp_up_load':
                results = await self._run_ramp_up_load(config, test_function)
            elif config['pattern'] == 'spike_load':
                results = await self._run_spike_load(config, test_function)
            else:
                results = await self._run_random_load(config, test_function)
            
            # Count errors
            errors = sum(1 for r in results if r.get('error'))
            
        except Exception as e:
            self.logger.error(f"Load test failed: {e}")
            errors = 1
        
        execution_time = time.time() - start_time
        perf_metrics = monitor.stop_monitoring()
        
        # Calculate latency percentiles
        response_times = [r.get('response_time', 0) for r in results if not r.get('error')]
        
        if response_times:
            latency_p50 = np.percentile(response_times, 50)
            latency_p95 = np.percentile(response_times, 95)
            latency_p99 = np.percentile(response_times, 99)
            throughput = len(response_times) / execution_time
        else:
            latency_p50 = latency_p95 = latency_p99 = throughput = 0
        
        return PerformanceMetrics(
            test_name=f"load_test_{config['pattern']}",
            execution_time=execution_time,
            memory_usage_mb=perf_metrics.get('memory_usage_mb', 0),
            cpu_usage_percent=perf_metrics.get('cpu_usage_percent', 0),
            peak_memory_mb=perf_metrics.get('peak_memory_mb', 0),
            peak_cpu_percent=perf_metrics.get('peak_cpu_percent', 0),
            throughput_ops_per_sec=throughput,
            latency_p50=latency_p50,
            latency_p95=latency_p95,
            latency_p99=latency_p99,
            error_rate=(errors / max(len(results), 1)) * 100,
            concurrent_users=config.get('concurrent_users', 0)
        )
    
    async def _run_constant_load(self, config: Dict[str, Any], test_function: Callable) -> List[Dict]:
        """Run constant load test"""
        concurrent_users = config['concurrent_users']
        duration = config['duration_seconds']
        requests_per_user = config['requests_per_user']
        
        async def user_simulation():
            results = []
            for _ in range(requests_per_user):
                start_time = time.time()
                try:
                    await test_function()
                    response_time = time.time() - start_time
                    results.append({'response_time': response_time, 'error': False})
                except Exception as e:
                    response_time = time.time() - start_time
                    results.append({'response_time': response_time, 'error': True, 'error_msg': str(e)})
                
                # Small delay between requests
                await asyncio.sleep(0.1)
            
            return results
        
        # Run concurrent users
        tasks = [user_simulation() for _ in range(concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_results = []
        for user_result in user_results:
            if isinstance(user_result, list):
                all_results.extend(user_result)
            else:
                all_results.append({'error': True, 'error_msg': str(user_result)})
        
        return all_results
    
    async def _run_ramp_up_load(self, config: Dict[str, Any], test_function: Callable) -> List[Dict]:
        """Run ramp-up load test"""
        start_users = config['start_users']
        end_users = config['end_users']
        ramp_duration = config['ramp_duration_seconds']
        hold_duration = config['hold_duration_seconds']
        
        results = []
        
        # Ramp up phase
        user_increment = (end_users - start_users) / (ramp_duration / 10)  # Add users every 10 seconds
        current_users = start_users
        
        for step in range(int(ramp_duration / 10)):
            step_results = await self._run_constant_load({
                'concurrent_users': int(current_users),
                'duration_seconds': 10,
                'requests_per_user': 5
            }, test_function)
            results.extend(step_results)
            
            current_users = min(current_users + user_increment, end_users)
            await asyncio.sleep(1)
        
        # Hold phase
        hold_results = await self._run_constant_load({
            'concurrent_users': end_users,
            'duration_seconds': hold_duration,
            'requests_per_user': 10
        }, test_function)
        results.extend(hold_results)
        
        return results
    
    async def _run_spike_load(self, config: Dict[str, Any], test_function: Callable) -> List[Dict]:
        """Run spike load test"""
        baseline_users = config['baseline_users']
        spike_users = config['spike_users']
        spike_duration = config['spike_duration_seconds']
        total_duration = config['total_duration_seconds']
        
        results = []
        
        # Baseline phase
        baseline_duration = (total_duration - spike_duration) // 2
        baseline_results = await self._run_constant_load({
            'concurrent_users': baseline_users,
            'duration_seconds': baseline_duration,
            'requests_per_user': 10
        }, test_function)
        results.extend(baseline_results)
        
        # Spike phase
        spike_results = await self._run_constant_load({
            'concurrent_users': spike_users,
            'duration_seconds': spike_duration,
            'requests_per_user': 5
        }, test_function)
        results.extend(spike_results)
        
        # Recovery phase
        recovery_results = await self._run_constant_load({
            'concurrent_users': baseline_users,
            'duration_seconds': baseline_duration,
            'requests_per_user': 10
        }, test_function)
        results.extend(recovery_results)
        
        return results
    
    async def _run_random_load(self, config: Dict[str, Any], test_function: Callable) -> List[Dict]:
        """Run random load test"""
        import random
        
        min_users = config['min_users']
        max_users = config['max_users']
        duration = config['duration_seconds']
        
        results = []
        elapsed = 0
        step_duration = 30  # 30-second steps
        
        while elapsed < duration:
            current_users = random.randint(min_users, max_users)
            remaining_time = min(step_duration, duration - elapsed)
            
            step_results = await self._run_constant_load({
                'concurrent_users': current_users,
                'duration_seconds': remaining_time,
                'requests_per_user': 5
            }, test_function)
            results.extend(step_results)
            
            elapsed += remaining_time
            await asyncio.sleep(1)
        
        return results
    
    def analyze_performance_results(self, metrics: PerformanceMetrics, sla: SLARequirements) -> Dict[str, Any]:
        """Analyze performance results against SLA requirements"""
        analysis = {
            'test_name': metrics.test_name,
            'sla_compliance': {},
            'performance_grade': 'A',  # Default grade
            'recommendations': [],
            'bottlenecks': [],
            'summary': {}
        }
        
        # Check SLA compliance
        sla_checks = {
            'response_time': metrics.execution_time <= sla.max_response_time_seconds,
            'memory_usage': metrics.peak_memory_mb <= sla.max_memory_mb,
            'cpu_usage': metrics.peak_cpu_percent <= sla.max_cpu_percent,
            'error_rate': (metrics.error_rate or 0) <= sla.max_error_rate_percent,
            'throughput': (metrics.throughput_ops_per_sec or 0) >= sla.min_throughput_ops_per_sec
        }
        
        analysis['sla_compliance'] = sla_checks
        
        # Calculate overall compliance
        compliance_rate = sum(sla_checks.values()) / len(sla_checks)
        
        # Assign performance grade
        if compliance_rate >= 0.9:
            analysis['performance_grade'] = 'A'
        elif compliance_rate >= 0.8:
            analysis['performance_grade'] = 'B'
        elif compliance_rate >= 0.7:
            analysis['performance_grade'] = 'C'
        elif compliance_rate >= 0.6:
            analysis['performance_grade'] = 'D'
        else:
            analysis['performance_grade'] = 'F'
        
        # Generate recommendations
        if not sla_checks['response_time']:
            analysis['recommendations'].append(
                f"Response time ({metrics.execution_time:.2f}s) exceeds SLA ({sla.max_response_time_seconds}s). "
                "Consider optimizing algorithms or adding caching."
            )
            analysis['bottlenecks'].append('response_time')
        
        if not sla_checks['memory_usage']:
            analysis['recommendations'].append(
                f"Memory usage ({metrics.peak_memory_mb:.1f}MB) exceeds SLA ({sla.max_memory_mb}MB). "
                "Consider optimizing data structures or implementing memory pooling."
            )
            analysis['bottlenecks'].append('memory')
        
        if not sla_checks['cpu_usage']:
            analysis['recommendations'].append(
                f"CPU usage ({metrics.peak_cpu_percent:.1f}%) exceeds SLA ({sla.max_cpu_percent}%). "
                "Consider optimizing computational complexity or implementing parallel processing."
            )
            analysis['bottlenecks'].append('cpu')
        
        if not sla_checks['throughput']:
            analysis['recommendations'].append(
                f"Throughput ({metrics.throughput_ops_per_sec:.1f} ops/sec) below SLA ({sla.min_throughput_ops_per_sec} ops/sec). "
                "Consider implementing connection pooling or optimizing database queries."
            )
            analysis['bottlenecks'].append('throughput')
        
        if not sla_checks['error_rate']:
            analysis['recommendations'].append(
                f"Error rate ({metrics.error_rate:.1f}%) exceeds SLA ({sla.max_error_rate_percent}%). "
                "Investigate error causes and implement better error handling."
            )
            analysis['bottlenecks'].append('reliability')
        
        # Performance summary
        analysis['summary'] = {
            'overall_grade': analysis['performance_grade'],
            'sla_compliance_rate': f"{compliance_rate * 100:.1f}%",
            'primary_bottlenecks': analysis['bottlenecks'][:3],  # Top 3 bottlenecks
            'performance_score': compliance_rate * 100
        }
        
        return analysis
    
    def generate_performance_report(self, test_results: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not test_results:
            return {'error': 'No test results provided'}
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_tests': len(test_results),
            'summary': {},
            'detailed_results': [],
            'trends': {},
            'recommendations': []
        }
        
        # Calculate summary statistics
        execution_times = [r.execution_time for r in test_results]
        memory_usage = [r.peak_memory_mb for r in test_results]
        cpu_usage = [r.peak_cpu_percent for r in test_results]
        throughput = [r.throughput_ops_per_sec for r in test_results if r.throughput_ops_per_sec]
        error_rates = [r.error_rate for r in test_results if r.error_rate is not None]
        
        report['summary'] = {
            'execution_time': {
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'min': min(execution_times),
                'max': max(execution_times),
                'std_dev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0
            },
            'memory_usage_mb': {
                'mean': statistics.mean(memory_usage),
                'median': statistics.median(memory_usage),
                'min': min(memory_usage),
                'max': max(memory_usage),
                'std_dev': statistics.stdev(memory_usage) if len(memory_usage) > 1 else 0
            },
            'cpu_usage_percent': {
                'mean': statistics.mean(cpu_usage),
                'median': statistics.median(cpu_usage),
                'min': min(cpu_usage),
                'max': max(cpu_usage),
                'std_dev': statistics.stdev(cpu_usage) if len(cpu_usage) > 1 else 0
            }
        }
        
        if throughput:
            report['summary']['throughput_ops_per_sec'] = {
                'mean': statistics.mean(throughput),
                'median': statistics.median(throughput),
                'min': min(throughput),
                'max': max(throughput),
                'std_dev': statistics.stdev(throughput) if len(throughput) > 1 else 0
            }
        
        if error_rates:
            report['summary']['error_rate_percent'] = {
                'mean': statistics.mean(error_rates),
                'median': statistics.median(error_rates),
                'min': min(error_rates),
                'max': max(error_rates),
                'std_dev': statistics.stdev(error_rates) if len(error_rates) > 1 else 0
            }
        
        # Add detailed results
        report['detailed_results'] = [asdict(result) for result in test_results]
        
        # Generate recommendations based on patterns
        self._generate_performance_recommendations(report)
        
        return report
    
    def _generate_performance_recommendations(self, report: Dict[str, Any]):
        """Generate performance recommendations based on test results"""
        summary = report['summary']
        recommendations = []
        
        # Memory recommendations
        if summary['memory_usage_mb']['max'] > 1000:  # > 1GB
            recommendations.append({
                'category': 'memory',
                'priority': 'high',
                'issue': f"Peak memory usage is {summary['memory_usage_mb']['max']:.1f}MB",
                'recommendation': 'Implement memory optimization strategies such as data streaming, pagination, or memory pooling'
            })
        
        # CPU recommendations
        if summary['cpu_usage_percent']['mean'] > 70:
            recommendations.append({
                'category': 'cpu',
                'priority': 'medium',
                'issue': f"Average CPU usage is {summary['cpu_usage_percent']['mean']:.1f}%",
                'recommendation': 'Consider implementing parallel processing or optimizing computational algorithms'
            })
        
        # Response time recommendations
        if summary['execution_time']['mean'] > 30:  # > 30 seconds
            recommendations.append({
                'category': 'response_time',
                'priority': 'high',
                'issue': f"Average response time is {summary['execution_time']['mean']:.1f} seconds",
                'recommendation': 'Implement caching, optimize database queries, or consider asynchronous processing'
            })
        
        # Throughput recommendations
        if 'throughput_ops_per_sec' in summary and summary['throughput_ops_per_sec']['mean'] < 10:
            recommendations.append({
                'category': 'throughput',
                'priority': 'medium',
                'issue': f"Average throughput is {summary['throughput_ops_per_sec']['mean']:.1f} ops/sec",
                'recommendation': 'Optimize database connections, implement connection pooling, or scale horizontally'
            })
        
        # Variability recommendations
        if summary['execution_time']['std_dev'] > summary['execution_time']['mean'] * 0.5:
            recommendations.append({
                'category': 'consistency',
                'priority': 'medium',
                'issue': 'High variability in response times detected',
                'recommendation': 'Investigate performance bottlenecks and implement consistent resource allocation'
            })
        
        report['recommendations'] = recommendations
    
    def benchmark_against_baseline(self, current_results: List[PerformanceMetrics], 
                                 baseline_results: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Benchmark current results against baseline"""
        if not baseline_results:
            return {'error': 'No baseline results provided'}
        
        def calculate_change(current: float, baseline: float) -> Dict[str, Any]:
            if baseline == 0:
                return {'change_percent': 0, 'change_absolute': current - baseline, 'status': 'no_baseline'}
            
            change_percent = ((current - baseline) / baseline) * 100
            change_absolute = current - baseline
            
            if abs(change_percent) < 5:
                status = 'stable'
            elif change_percent > 0:
                status = 'degraded'
            else:
                status = 'improved'
            
            return {
                'change_percent': change_percent,
                'change_absolute': change_absolute,
                'status': status
            }
        
        # Calculate averages
        current_avg = {
            'execution_time': statistics.mean([r.execution_time for r in current_results]),
            'memory_usage': statistics.mean([r.peak_memory_mb for r in current_results]),
            'cpu_usage': statistics.mean([r.peak_cpu_percent for r in current_results])
        }
        
        baseline_avg = {
            'execution_time': statistics.mean([r.execution_time for r in baseline_results]),
            'memory_usage': statistics.mean([r.peak_memory_mb for r in baseline_results]),
            'cpu_usage': statistics.mean([r.peak_cpu_percent for r in baseline_results])
        }
        
        benchmark = {
            'comparison_timestamp': datetime.now().isoformat(),
            'current_test_count': len(current_results),
            'baseline_test_count': len(baseline_results),
            'metrics_comparison': {
                'execution_time': calculate_change(current_avg['execution_time'], baseline_avg['execution_time']),
                'memory_usage': calculate_change(current_avg['memory_usage'], baseline_avg['memory_usage']),
                'cpu_usage': calculate_change(current_avg['cpu_usage'], baseline_avg['cpu_usage'])
            },
            'overall_status': 'stable'  # Will be updated based on individual metrics
        }
        
        # Determine overall status
        statuses = [comp['status'] for comp in benchmark['metrics_comparison'].values()]
        if 'degraded' in statuses:
            benchmark['overall_status'] = 'degraded'
        elif 'improved' in statuses:
            benchmark['overall_status'] = 'improved'
        
        return benchmark
    
    def detect_performance_regressions(self, historical_results: List[List[PerformanceMetrics]]) -> Dict[str, Any]:
        """Detect performance regressions across multiple test runs"""
        if len(historical_results) < 2:
            return {'error': 'Need at least 2 test runs for regression detection'}
        
        regressions = {
            'detection_timestamp': datetime.now().isoformat(),
            'test_runs_analyzed': len(historical_results),
            'regressions_detected': [],
            'trends': {},
            'alerts': []
        }
        
        # Calculate trends for each metric
        metrics_over_time = {
            'execution_time': [],
            'memory_usage': [],
            'cpu_usage': []
        }
        
        for test_run in historical_results:
            if test_run:
                metrics_over_time['execution_time'].append(
                    statistics.mean([r.execution_time for r in test_run])
                )
                metrics_over_time['memory_usage'].append(
                    statistics.mean([r.peak_memory_mb for r in test_run])
                )
                metrics_over_time['cpu_usage'].append(
                    statistics.mean([r.peak_cpu_percent for r in test_run])
                )
        
        # Detect regressions using linear regression
        for metric_name, values in metrics_over_time.items():
            if len(values) >= 3:
                # Simple linear regression to detect trends
                x = np.arange(len(values))
                slope, intercept = np.polyfit(x, values, 1)
                
                # Calculate R-squared
                y_pred = slope * x + intercept
                ss_res = np.sum((values - y_pred) ** 2)
                ss_tot = np.sum((values - np.mean(values)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                
                trend_info = {
                    'metric': metric_name,
                    'slope': slope,
                    'r_squared': r_squared,
                    'trend_direction': 'increasing' if slope > 0 else 'decreasing',
                    'confidence': 'high' if r_squared > 0.7 else 'medium' if r_squared > 0.4 else 'low'
                }
                
                regressions['trends'][metric_name] = trend_info
                
                # Check for significant regressions
                if slope > 0 and r_squared > 0.5:  # Increasing trend with good fit
                    latest_value = values[-1]
                    baseline_value = values[0]
                    change_percent = ((latest_value - baseline_value) / baseline_value) * 100
                    
                    if change_percent > 20:  # 20% degradation threshold
                        regressions['regressions_detected'].append({
                            'metric': metric_name,
                            'severity': 'high' if change_percent > 50 else 'medium',
                            'change_percent': change_percent,
                            'trend_confidence': trend_info['confidence'],
                            'description': f"{metric_name} has degraded by {change_percent:.1f}% over {len(values)} test runs"
                        })
                        
                        regressions['alerts'].append({
                            'type': 'performance_regression',
                            'metric': metric_name,
                            'severity': 'high' if change_percent > 50 else 'medium',
                            'message': f"Performance regression detected in {metric_name}: {change_percent:.1f}% degradation"
                        })
        
        return regressions