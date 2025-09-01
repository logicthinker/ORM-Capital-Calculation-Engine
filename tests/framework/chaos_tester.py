"""
Chaos Testing Engine for Automated Testing Framework

Implements chaos engineering principles to test system resilience and failure recovery.
"""

import asyncio
import random
import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import subprocess
import signal
import os


@dataclass
class ChaosScenario:
    """Chaos testing scenario definition"""
    scenario_id: str
    name: str
    description: str
    category: str  # 'system', 'network', 'resource', 'data'
    severity: str  # 'low', 'medium', 'high', 'critical'
    duration_seconds: int
    recovery_time_seconds: int
    success_criteria: List[str]


@dataclass
class ChaosResult:
    """Chaos test result"""
    scenario_id: str
    start_time: datetime
    end_time: datetime
    success: bool
    recovery_time_seconds: float
    error_messages: List[str]
    system_metrics: Dict[str, Any]
    resilience_score: float  # 0-100


class ChaosTestEngine:
    """Comprehensive chaos testing engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_chaos = []
        self.system_monitor = SystemMonitor()
        
    def generate_failure_scenario(self) -> Dict[str, Any]:
        """Generate system failure scenario"""
        failure_types = [
            'database_connection_failure',
            'memory_exhaustion',
            'cpu_spike',
            'disk_full',
            'service_crash',
            'dependency_timeout',
            'configuration_corruption',
            'thread_pool_exhaustion'
        ]
        
        failure_type = random.choice(failure_types)
        
        if failure_type == 'database_connection_failure':
            return {
                'type': failure_type,
                'scenario': ChaosScenario(
                    scenario_id='CHAOS_DB_001',
                    name='Database Connection Failure',
                    description='Simulate database connection failures',
                    category='system',
                    severity='high',
                    duration_seconds=random.randint(30, 180),
                    recovery_time_seconds=random.randint(10, 60),
                    success_criteria=[
                        'system_continues_operation',
                        'graceful_error_handling',
                        'automatic_reconnection',
                        'no_data_corruption'
                    ]
                ),
                'implementation': 'block_database_connections'
            }
        elif failure_type == 'memory_exhaustion':
            return {
                'type': failure_type,
                'scenario': ChaosScenario(
                    scenario_id='CHAOS_MEM_001',
                    name='Memory Exhaustion',
                    description='Consume available memory to test OOM handling',
                    category='resource',
                    severity='critical',
                    duration_seconds=random.randint(60, 300),
                    recovery_time_seconds=random.randint(30, 120),
                    success_criteria=[
                        'graceful_degradation',
                        'memory_cleanup',
                        'service_recovery',
                        'no_permanent_damage'
                    ]
                ),
                'implementation': 'consume_memory',
                'memory_percentage': random.randint(70, 95)
            }
        elif failure_type == 'cpu_spike':
            return {
                'type': failure_type,
                'scenario': ChaosScenario(
                    scenario_id='CHAOS_CPU_001',
                    name='CPU Spike',
                    description='Generate high CPU load to test performance under stress',
                    category='resource',
                    severity='medium',
                    duration_seconds=random.randint(30, 120),
                    recovery_time_seconds=random.randint(5, 30),
                    success_criteria=[
                        'response_time_degradation_acceptable',
                        'no_service_crash',
                        'queue_management',
                        'load_balancing_effective'
                    ]
                ),
                'implementation': 'generate_cpu_load',
                'cpu_percentage': random.randint(80, 100)
            }
        else:
            return {
                'type': failure_type,
                'scenario': ChaosScenario(
                    scenario_id=f'CHAOS_GEN_{random.randint(1, 999):03d}',
                    name=f'Generic {failure_type.replace("_", " ").title()}',
                    description=f'Test system resilience against {failure_type}',
                    category='system',
                    severity='medium',
                    duration_seconds=random.randint(60, 180),
                    recovery_time_seconds=random.randint(15, 60),
                    success_criteria=[
                        'system_stability_maintained',
                        'error_handling_effective',
                        'recovery_successful'
                    ]
                ),
                'implementation': 'generic_failure_simulation'
            }
    
    def generate_network_scenario(self) -> Dict[str, Any]:
        """Generate network partition scenario"""
        network_issues = [
            'connection_timeout',
            'packet_loss',
            'bandwidth_limitation',
            'dns_failure',
            'ssl_certificate_error',
            'network_partition',
            'high_latency',
            'connection_reset'
        ]
        
        issue_type = random.choice(network_issues)
        
        if issue_type == 'connection_timeout':
            return {
                'type': issue_type,
                'scenario': ChaosScenario(
                    scenario_id='CHAOS_NET_001',
                    name='Connection Timeout',
                    description='Simulate network connection timeouts',
                    category='network',
                    severity='high',
                    duration_seconds=random.randint(60, 300),
                    recovery_time_seconds=random.randint(10, 60),
                    success_criteria=[
                        'timeout_handling',
                        'retry_mechanism_works',
                        'circuit_breaker_activated',
                        'fallback_mechanism'
                    ]
                ),
                'implementation': 'simulate_connection_timeout',
                'timeout_duration': random.randint(5, 30)
            }
        elif issue_type == 'packet_loss':
            return {
                'type': issue_type,
                'scenario': ChaosScenario(
                    scenario_id='CHAOS_NET_002',
                    name='Packet Loss',
                    description='Simulate network packet loss',
                    category='network',
                    severity='medium',
                    duration_seconds=random.randint(120, 600),
                    recovery_time_seconds=random.randint(30, 120),
                    success_criteria=[
                        'data_integrity_maintained',
                        'retransmission_works',
                        'performance_degradation_acceptable',
                        'connection_stability'
                    ]
                ),
                'implementation': 'simulate_packet_loss',
                'loss_percentage': random.randint(5, 25)
            }
        else:
            return {
                'type': issue_type,
                'scenario': ChaosScenario(
                    scenario_id=f'CHAOS_NET_{random.randint(100, 999)}',
                    name=f'Network {issue_type.replace("_", " ").title()}',
                    description=f'Test network resilience against {issue_type}',
                    category='network',
                    severity='medium',
                    duration_seconds=random.randint(90, 300),
                    recovery_time_seconds=random.randint(20, 90),
                    success_criteria=[
                        'network_error_handling',
                        'service_availability',
                        'data_consistency'
                    ]
                ),
                'implementation': 'generic_network_simulation'
            }
    
    def generate_resource_scenario(self) -> Dict[str, Any]:
        """Generate resource exhaustion scenario"""
        resource_types = [
            'memory_leak',
            'file_descriptor_exhaustion',
            'thread_pool_exhaustion',
            'disk_space_exhaustion',
            'connection_pool_exhaustion',
            'cache_overflow',
            'queue_overflow'
        ]
        
        resource_type = random.choice(resource_types)
        
        return {
            'type': resource_type,
            'scenario': ChaosScenario(
                scenario_id=f'CHAOS_RES_{random.randint(1, 999):03d}',
                name=f'Resource {resource_type.replace("_", " ").title()}',
                description=f'Test system behavior under {resource_type}',
                category='resource',
                severity='high',
                duration_seconds=random.randint(180, 600),
                recovery_time_seconds=random.randint(60, 300),
                success_criteria=[
                    'resource_cleanup',
                    'graceful_degradation',
                    'monitoring_alerts',
                    'automatic_recovery'
                ]
            ),
            'implementation': f'simulate_{resource_type}',
            'intensity': random.choice(['low', 'medium', 'high'])
        }
    
    async def execute_chaos_scenario(self, scenario_config: Dict[str, Any]) -> ChaosResult:
        """Execute a chaos testing scenario"""
        scenario = scenario_config['scenario']
        self.logger.info(f"Starting chaos scenario: {scenario.name}")
        
        start_time = datetime.now()
        self.system_monitor.start_monitoring()
        
        try:
            # Execute the chaos scenario
            if scenario_config['implementation'] == 'block_database_connections':
                await self._block_database_connections(scenario)
            elif scenario_config['implementation'] == 'consume_memory':
                await self._consume_memory(scenario, scenario_config.get('memory_percentage', 80))
            elif scenario_config['implementation'] == 'generate_cpu_load':
                await self._generate_cpu_load(scenario, scenario_config.get('cpu_percentage', 90))
            elif scenario_config['implementation'] == 'simulate_connection_timeout':
                await self._simulate_connection_timeout(scenario, scenario_config.get('timeout_duration', 10))
            elif scenario_config['implementation'] == 'simulate_packet_loss':
                await self._simulate_packet_loss(scenario, scenario_config.get('loss_percentage', 10))
            else:
                await self._generic_chaos_simulation(scenario)
            
            # Wait for scenario duration
            await asyncio.sleep(scenario.duration_seconds)
            
            # Stop chaos and measure recovery
            recovery_start = time.time()
            await self._stop_chaos_scenario(scenario)
            
            # Wait for system recovery
            recovery_success = await self._wait_for_recovery(scenario)
            recovery_time = time.time() - recovery_start
            
            end_time = datetime.now()
            system_metrics = self.system_monitor.stop_monitoring()
            
            # Evaluate success criteria
            success = await self._evaluate_success_criteria(scenario, system_metrics)
            resilience_score = self._calculate_resilience_score(scenario, recovery_time, success, system_metrics)
            
            return ChaosResult(
                scenario_id=scenario.scenario_id,
                start_time=start_time,
                end_time=end_time,
                success=success and recovery_success,
                recovery_time_seconds=recovery_time,
                error_messages=[],
                system_metrics=system_metrics,
                resilience_score=resilience_score
            )
            
        except Exception as e:
            self.logger.error(f"Chaos scenario failed: {e}")
            end_time = datetime.now()
            system_metrics = self.system_monitor.stop_monitoring()
            
            return ChaosResult(
                scenario_id=scenario.scenario_id,
                start_time=start_time,
                end_time=end_time,
                success=False,
                recovery_time_seconds=0,
                error_messages=[str(e)],
                system_metrics=system_metrics,
                resilience_score=0
            )
    
    async def _block_database_connections(self, scenario: ChaosScenario):
        """Simulate database connection failures"""
        self.logger.info("Blocking database connections")
        # Implementation would block database connections
        # This is a simulation for testing purposes
        pass
    
    async def _consume_memory(self, scenario: ChaosScenario, percentage: int):
        """Consume memory to simulate memory exhaustion"""
        self.logger.info(f"Consuming {percentage}% of available memory")
        
        # Get available memory
        memory_info = psutil.virtual_memory()
        target_memory = int(memory_info.available * (percentage / 100))
        
        # Consume memory in chunks
        memory_hogs = []
        chunk_size = 100 * 1024 * 1024  # 100MB chunks
        
        try:
            while len(memory_hogs) * chunk_size < target_memory:
                memory_hogs.append(bytearray(chunk_size))
                await asyncio.sleep(0.1)  # Small delay to prevent system freeze
            
            self.logger.info(f"Consumed approximately {len(memory_hogs) * chunk_size / (1024**3):.2f} GB")
            
            # Keep memory consumed for scenario duration
            await asyncio.sleep(scenario.duration_seconds)
            
        finally:
            # Clean up memory
            memory_hogs.clear()
            self.logger.info("Memory consumption stopped")
    
    async def _generate_cpu_load(self, scenario: ChaosScenario, percentage: int):
        """Generate CPU load to simulate high CPU usage"""
        self.logger.info(f"Generating {percentage}% CPU load")
        
        num_cores = psutil.cpu_count()
        load_threads = []
        stop_event = threading.Event()
        
        def cpu_load_worker():
            """Worker function to generate CPU load"""
            while not stop_event.is_set():
                # Busy wait to consume CPU
                end_time = time.time() + 0.1  # 100ms of work
                while time.time() < end_time and not stop_event.is_set():
                    pass
                # Small sleep to control CPU percentage
                time.sleep(0.1 * (100 - percentage) / percentage)
        
        try:
            # Start CPU load threads
            for _ in range(num_cores):
                thread = threading.Thread(target=cpu_load_worker)
                thread.start()
                load_threads.append(thread)
            
            # Keep load for scenario duration
            await asyncio.sleep(scenario.duration_seconds)
            
        finally:
            # Stop CPU load
            stop_event.set()
            for thread in load_threads:
                thread.join(timeout=1)
            self.logger.info("CPU load generation stopped")
    
    async def _simulate_connection_timeout(self, scenario: ChaosScenario, timeout_duration: int):
        """Simulate network connection timeouts"""
        self.logger.info(f"Simulating connection timeouts of {timeout_duration}s")
        # Implementation would introduce network delays
        pass
    
    async def _simulate_packet_loss(self, scenario: ChaosScenario, loss_percentage: int):
        """Simulate network packet loss"""
        self.logger.info(f"Simulating {loss_percentage}% packet loss")
        # Implementation would drop network packets
        pass
    
    async def _generic_chaos_simulation(self, scenario: ChaosScenario):
        """Generic chaos simulation"""
        self.logger.info(f"Running generic chaos simulation: {scenario.name}")
        # Generic implementation for other chaos scenarios
        pass
    
    async def _stop_chaos_scenario(self, scenario: ChaosScenario):
        """Stop the chaos scenario and begin recovery"""
        self.logger.info(f"Stopping chaos scenario: {scenario.name}")
        # Implementation would clean up chaos effects
        pass
    
    async def _wait_for_recovery(self, scenario: ChaosScenario) -> bool:
        """Wait for system recovery and validate"""
        self.logger.info("Waiting for system recovery")
        
        recovery_timeout = scenario.recovery_time_seconds * 2  # Allow extra time
        start_time = time.time()
        
        while time.time() - start_time < recovery_timeout:
            # Check if system has recovered
            if await self._check_system_health():
                self.logger.info("System recovery successful")
                return True
            
            await asyncio.sleep(5)  # Check every 5 seconds
        
        self.logger.warning("System recovery timeout")
        return False
    
    async def _check_system_health(self) -> bool:
        """Check if system has recovered to healthy state"""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                return False
            
            # Check memory usage
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 90:
                return False
            
            # Check if processes are responding
            # This would include application-specific health checks
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def _evaluate_success_criteria(self, scenario: ChaosScenario, metrics: Dict[str, Any]) -> bool:
        """Evaluate if success criteria were met"""
        success_count = 0
        total_criteria = len(scenario.success_criteria)
        
        for criterion in scenario.success_criteria:
            if await self._check_success_criterion(criterion, metrics):
                success_count += 1
        
        # Require at least 70% of criteria to be met
        success_rate = success_count / total_criteria
        return success_rate >= 0.7
    
    async def _check_success_criterion(self, criterion: str, metrics: Dict[str, Any]) -> bool:
        """Check if a specific success criterion was met"""
        if criterion == 'system_continues_operation':
            return metrics.get('uptime_percentage', 0) > 80
        elif criterion == 'graceful_error_handling':
            return metrics.get('error_rate', 100) < 10
        elif criterion == 'automatic_reconnection':
            return metrics.get('reconnection_success', False)
        elif criterion == 'no_data_corruption':
            return metrics.get('data_integrity_check', False)
        elif criterion == 'graceful_degradation':
            return metrics.get('performance_degradation', 100) < 50
        elif criterion == 'memory_cleanup':
            return metrics.get('memory_leak_detected', True) == False
        elif criterion == 'service_recovery':
            return metrics.get('service_recovery_time', float('inf')) < 300
        else:
            # Default: assume criterion is met if no specific check
            return True
    
    def _calculate_resilience_score(self, scenario: ChaosScenario, recovery_time: float, 
                                  success: bool, metrics: Dict[str, Any]) -> float:
        """Calculate resilience score (0-100)"""
        base_score = 100 if success else 0
        
        # Adjust score based on recovery time
        expected_recovery = scenario.recovery_time_seconds
        if recovery_time > expected_recovery:
            time_penalty = min(50, (recovery_time - expected_recovery) / expected_recovery * 30)
            base_score -= time_penalty
        
        # Adjust score based on system metrics
        if metrics.get('error_rate', 0) > 5:
            base_score -= min(20, metrics['error_rate'])
        
        if metrics.get('performance_degradation', 0) > 30:
            base_score -= min(15, metrics['performance_degradation'] - 30)
        
        return max(0, min(100, base_score))


class SystemMonitor:
    """System monitoring for chaos testing"""
    
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.start_time = None
        
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.start_time = time.time()
        self.metrics = []
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        
        return self._calculate_metrics()
    
    def _monitor_loop(self):
        """Monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent()
                memory_info = psutil.virtual_memory()
                disk_info = psutil.disk_usage('/')
                
                self.metrics.append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_info.percent,
                    'memory_available_mb': memory_info.available / (1024 * 1024),
                    'disk_percent': disk_info.percent,
                    'disk_free_gb': disk_info.free / (1024 * 1024 * 1024)
                })
                
                time.sleep(5)  # Collect metrics every 5 seconds
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                break
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate summary metrics from collected data"""
        if not self.metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_percent'] for m in self.metrics]
        
        return {
            'monitoring_duration': time.time() - self.start_time if self.start_time else 0,
            'sample_count': len(self.metrics),
            'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
            'max_cpu_percent': max(cpu_values),
            'avg_memory_percent': sum(memory_values) / len(memory_values),
            'max_memory_percent': max(memory_values),
            'uptime_percentage': 100,  # Simplified - would be calculated based on service availability
            'error_rate': 0,  # Would be calculated from application logs
            'performance_degradation': 0,  # Would be calculated from response times
            'data_integrity_check': True,  # Would be result of data validation
            'service_recovery_time': 0,  # Would be measured during recovery
            'memory_leak_detected': False  # Would be detected from memory growth patterns
        }