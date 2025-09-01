"""
Tests for performance optimization and caching functionality
"""

import pytest
import asyncio
import time
from datetime import datetime, date
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from orm_calculator.core.cache import (
    CacheManager, MemoryCacheService, RedisCacheService, 
    CacheConfig, CacheType, initialize_cache
)
from orm_calculator.core.performance import (
    PerformanceMonitor, MetricsCollector, SystemMonitor, 
    PerformanceProfiler, get_performance_monitor
)
from orm_calculator.core.database_optimization import (
    DatabaseOptimizer, SQLiteOptimizer, PostgreSQLOptimizer,
    DatabaseIndexManager, ConcurrentQueryExecutor, DatabaseType
)
from orm_calculator.core.concurrent_processing import (
    TaskGroup, CalculationBatch, ParallelDataProcessor,
    ConcurrentConfig, run_calculations_concurrently
)
from orm_calculator.models.pydantic_models import CalculationResult, ModelNameEnum


class TestCacheService:
    """Test cache service functionality"""
    
    @pytest.fixture
    async def memory_cache(self):
        """Create memory cache for testing"""
        config = CacheConfig(cache_type=CacheType.MEMORY, max_memory_cache_size=100)
        cache_manager = await initialize_cache(config)
        yield cache_manager
        # Cleanup
        await cache_manager.cache.clear()
    
    @pytest.mark.asyncio
    async def test_memory_cache_basic_operations(self, memory_cache):
        """Test basic cache operations"""
        cache = memory_cache.cache
        
        # Test set and get
        await cache.set("test_key", "test_value", ttl=60)
        value = await cache.get("test_key")
        assert value == "test_value"
        
        # Test exists
        exists = await cache.exists("test_key")
        assert exists is True
        
        # Test delete
        await cache.delete("test_key")
        value = await cache.get("test_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, memory_cache):
        """Test cache TTL expiration"""
        cache = memory_cache.cache
        
        # Set with short TTL
        await cache.set("expire_key", "expire_value", ttl=1)
        
        # Should exist immediately
        value = await cache.get("expire_key")
        assert value == "expire_value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        value = await cache.get("expire_key")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_cache_manager_calculation_result(self, memory_cache):
        """Test caching calculation results"""
        # Create test calculation result
        result = CalculationResult(
            run_id="test_run",
            entity_id="test_entity",
            calculation_date=date.today(),
            model_name=ModelNameEnum.SMA,
            capital_requirement=1000000.0,
            business_indicator_component=800000.0,
            loss_component=200000.0,
            parameters_used={"test_param": 1.0},
            calculation_metadata={"test": "metadata"}
        )
        
        # Cache the result
        await memory_cache.cache_calculation_result(
            "test_entity", "2024-01-01", "SMA", "test_hash", result
        )
        
        # Retrieve the result
        cached_result = await memory_cache.get_calculation_result(
            "test_entity", "2024-01-01", "SMA", "test_hash"
        )
        
        assert cached_result is not None
        assert cached_result.entity_id == "test_entity"
        assert cached_result.capital_requirement == 1000000.0
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, memory_cache):
        """Test cache invalidation"""
        # Cache some data
        await memory_cache.cache_calculation_result(
            "entity1", "2024-01-01", "SMA", "hash1", 
            CalculationResult(
                run_id="run1", entity_id="entity1", calculation_date=date.today(),
                model_name=ModelNameEnum.SMA, capital_requirement=1000000.0
            )
        )
        
        # Invalidate entity cache
        await memory_cache.invalidate_entity_cache("entity1")
        
        # Should be gone
        result = await memory_cache.get_calculation_result(
            "entity1", "2024-01-01", "SMA", "hash1"
        )
        assert result is None


class TestPerformanceMonitoring:
    """Test performance monitoring functionality"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitor for testing"""
        return PerformanceMonitor()
    
    def test_metrics_collector_counters(self, performance_monitor):
        """Test metrics collector counter functionality"""
        metrics = performance_monitor.metrics
        
        # Test counter increment
        metrics.increment_counter("test_counter", 5)
        assert metrics.get_counter("test_counter") == 5
        
        # Test counter with labels
        metrics.increment_counter("test_counter", 3, {"label": "value"})
        assert metrics.get_counter("test_counter", {"label": "value"}) == 3
    
    def test_metrics_collector_gauges(self, performance_monitor):
        """Test metrics collector gauge functionality"""
        metrics = performance_monitor.metrics
        
        # Test gauge setting
        metrics.set_gauge("test_gauge", 42.5)
        assert metrics.get_gauge("test_gauge") == 42.5
        
        # Test gauge with labels
        metrics.set_gauge("test_gauge", 100.0, {"type": "memory"})
        assert metrics.get_gauge("test_gauge", {"type": "memory"}) == 100.0
    
    def test_metrics_collector_histograms(self, performance_monitor):
        """Test metrics collector histogram functionality"""
        metrics = performance_monitor.metrics
        
        # Record some values
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 15.0, 20.0]
        for value in values:
            metrics.record_histogram("test_histogram", value)
        
        # Get statistics
        stats = metrics.get_histogram_stats("test_histogram")
        
        assert stats["count"] == len(values)
        assert stats["min"] == 1.0
        assert stats["max"] == 20.0
        assert stats["avg"] == sum(values) / len(values)
    
    def test_system_monitor(self, performance_monitor):
        """Test system monitoring functionality"""
        system_monitor = performance_monitor.system_monitor
        
        # Test memory usage
        memory_stats = system_monitor.get_memory_usage()
        assert "rss_mb" in memory_stats
        assert "percent" in memory_stats
        assert memory_stats["rss_mb"] > 0
        
        # Test CPU usage
        cpu_stats = system_monitor.get_cpu_usage()
        assert "process_percent" in cpu_stats
        assert "system_percent" in cpu_stats
        assert "cpu_count" in cpu_stats
    
    @pytest.mark.asyncio
    async def test_performance_profiler(self, performance_monitor):
        """Test performance profiler functionality"""
        profiler = performance_monitor.profiler
        
        # Profile a simple operation
        async with profiler.profile("test_operation"):
            await asyncio.sleep(0.1)  # Simulate work
        
        # Get profile stats
        stats = profiler.get_profile_stats("test_operation")
        
        assert stats["count"] == 1
        assert stats["avg_duration"] >= 0.1
        assert stats["min_duration"] >= 0.1
    
    def test_request_recording(self, performance_monitor):
        """Test HTTP request recording"""
        # Record some requests
        performance_monitor.record_request("GET", "/api/test", 200, 0.5)
        performance_monitor.record_request("POST", "/api/test", 201, 1.2)
        performance_monitor.record_request("GET", "/api/test", 404, 0.3)
        
        # Check metrics
        total_requests = performance_monitor.metrics.get_counter("http_requests_total")
        assert total_requests >= 3
        
        # Check duration stats
        duration_stats = performance_monitor.metrics.get_histogram_stats("http_request_duration")
        assert duration_stats["count"] >= 3


class TestDatabaseOptimization:
    """Test database optimization functionality"""
    
    @pytest.fixture
    def sqlite_optimizer(self):
        """Create SQLite optimizer for testing"""
        return SQLiteOptimizer()
    
    @pytest.fixture
    def postgresql_optimizer(self):
        """Create PostgreSQL optimizer for testing"""
        return PostgreSQLOptimizer()
    
    def test_sqlite_connection_config(self, sqlite_optimizer):
        """Test SQLite connection pool configuration"""
        config = sqlite_optimizer.get_connection_pool_config()
        
        assert "poolclass" in config
        assert "connect_args" in config
        assert config["connect_args"]["check_same_thread"] is False
    
    def test_postgresql_connection_config(self, postgresql_optimizer):
        """Test PostgreSQL connection pool configuration"""
        config = postgresql_optimizer.get_connection_pool_config()
        
        assert "pool_size" in config
        assert "max_overflow" in config
        assert config["pool_pre_ping"] is True
    
    @pytest.mark.asyncio
    async def test_query_optimization(self, sqlite_optimizer):
        """Test query optimization"""
        original_query = "SELECT * FROM table WHERE id = :id ORDER BY created_at"
        params = {"id": 123}
        
        optimized_query, optimized_params = await sqlite_optimizer.optimize_query(
            original_query, params
        )
        
        assert optimized_params == params
        assert "SELECT" in optimized_query
    
    def test_index_manager_recommendations(self):
        """Test database index recommendations"""
        index_manager = DatabaseIndexManager(DatabaseType.POSTGRESQL)
        indexes = index_manager.get_recommended_indexes()
        
        assert len(indexes) > 0
        
        # Check for expected indexes
        index_names = [idx.name for idx in indexes]
        assert "idx_business_indicators_entity_date" in index_names
        assert "idx_loss_events_entity_dates" in index_names
    
    @pytest.mark.asyncio
    async def test_concurrent_query_executor(self):
        """Test concurrent query execution"""
        executor = ConcurrentQueryExecutor(max_concurrent=3)
        
        # Mock session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_session.execute.return_value = mock_result
        
        # Test concurrent queries
        queries = [
            ("SELECT 1", {}),
            ("SELECT 2", {}),
            ("SELECT 3", {})
        ]
        
        results = await executor.execute_concurrent_queries(mock_session, queries)
        
        assert len(results) == 3
        assert mock_session.execute.call_count == 3


class TestConcurrentProcessing:
    """Test concurrent processing functionality"""
    
    @pytest.mark.asyncio
    async def test_task_group_basic(self):
        """Test basic task group functionality"""
        config = ConcurrentConfig(max_concurrent_tasks=3)
        
        async with TaskGroup(config) as task_group:
            # Add some async tasks
            await task_group.add_async_task("task1", asyncio.sleep(0.1))
            await task_group.add_async_task("task2", asyncio.sleep(0.1))
            await task_group.add_async_task("task3", asyncio.sleep(0.1))
            
            results = await task_group.wait_all()
        
        assert len(results) == 3
        assert all(result.success for result in results.values())
    
    @pytest.mark.asyncio
    async def test_task_group_with_errors(self):
        """Test task group error handling"""
        config = ConcurrentConfig(max_concurrent_tasks=2)
        
        async def failing_task():
            raise ValueError("Test error")
        
        async def success_task():
            return "success"
        
        async with TaskGroup(config) as task_group:
            await task_group.add_async_task("fail_task", failing_task())
            await task_group.add_async_task("success_task", success_task())
            
            results = await task_group.wait_all()
        
        assert len(results) == 2
        assert not results["fail_task"].success
        assert results["success_task"].success
        assert results["success_task"].result == "success"
    
    @pytest.mark.asyncio
    async def test_calculation_batch(self):
        """Test calculation batch processing"""
        batch = CalculationBatch()
        
        # Mock calculation function
        async def mock_calculation(entity_id: str):
            await asyncio.sleep(0.1)  # Simulate work
            return f"result_for_{entity_id}"
        
        entities = ["entity1", "entity2", "entity3"]
        results = await batch.process_entity_calculations(
            entities, mock_calculation, "SMA"
        )
        
        assert len(results) == 3
        for entity_id in entities:
            task_id = f"SMA_{entity_id}"
            assert task_id in results
            assert results[task_id].success
    
    @pytest.mark.asyncio
    async def test_parallel_data_processor(self):
        """Test parallel data processing"""
        processor = ParallelDataProcessor(chunk_size=2, max_concurrent=2)
        
        # Test data
        data = list(range(10))
        
        # Mock processor function
        async def process_chunk(chunk):
            await asyncio.sleep(0.1)  # Simulate processing
            return sum(chunk)
        
        results = await processor.process_data_chunks(data, process_chunk)
        
        # Should have 5 chunks (10 items / 2 per chunk)
        assert len(results) == 5
        assert sum(results) == sum(data)  # Total should match
    
    @pytest.mark.asyncio
    async def test_run_calculations_concurrently(self):
        """Test concurrent calculation utility function"""
        # Mock calculations
        calculations = {}
        for i in range(5):
            async def calc(value=i):
                await asyncio.sleep(0.1)
                return value * 2
            calculations[f"calc_{i}"] = calc
        
        results = await run_calculations_concurrently(calculations, max_concurrent=3)
        
        assert len(results) == 5
        for i in range(5):
            calc_id = f"calc_{i}"
            assert calc_id in results
            assert results[calc_id].success
            assert results[calc_id].result == i * 2


class TestPerformanceIntegration:
    """Integration tests for performance optimization"""
    
    @pytest.mark.asyncio
    async def test_cache_and_performance_integration(self):
        """Test integration between caching and performance monitoring"""
        # Initialize cache
        config = CacheConfig(cache_type=CacheType.MEMORY)
        cache_manager = await initialize_cache(config)
        
        # Get performance monitor
        perf_monitor = get_performance_monitor()
        
        # Simulate some cache operations with performance tracking
        start_time = time.perf_counter()
        
        # Cache some data
        await cache_manager.cache.set("perf_test", {"data": "test"}, ttl=60)
        
        # Record the operation
        duration = time.perf_counter() - start_time
        perf_monitor.metrics.record_timer("cache_operation", duration)
        
        # Get cache stats
        cache_stats = await cache_manager.cache.get_stats()
        
        assert "sets" in cache_stats
        assert cache_stats["sets"] >= 1
        
        # Get performance stats
        timer_stats = perf_monitor.metrics.get_histogram_stats("cache_operation")
        assert timer_stats["count"] >= 1
    
    @pytest.mark.asyncio
    async def test_concurrent_calculations_with_caching(self):
        """Test concurrent calculations with caching enabled"""
        # Mock calculation service with caching
        cache_manager = await initialize_cache(CacheConfig(cache_type=CacheType.MEMORY))
        
        # Simulate cached calculation
        cached_result = CalculationResult(
            run_id="cached_run",
            entity_id="test_entity",
            calculation_date=date.today(),
            model_name=ModelNameEnum.SMA,
            capital_requirement=1000000.0
        )
        
        await cache_manager.cache_calculation_result(
            "test_entity", "2024-01-01", "SMA", "test_hash", cached_result
        )
        
        # Mock calculation function that checks cache first
        async def cached_calculation(entity_id: str):
            result = await cache_manager.get_calculation_result(
                entity_id, "2024-01-01", "SMA", "test_hash"
            )
            if result:
                return result
            
            # Simulate calculation
            await asyncio.sleep(0.1)
            return CalculationResult(
                run_id="new_run",
                entity_id=entity_id,
                calculation_date=date.today(),
                model_name=ModelNameEnum.SMA,
                capital_requirement=2000000.0
            )
        
        # Test with cached entity (should be fast)
        start_time = time.perf_counter()
        result = await cached_calculation("test_entity")
        cached_duration = time.perf_counter() - start_time
        
        assert result.capital_requirement == 1000000.0  # Cached value
        assert cached_duration < 0.05  # Should be very fast
        
        # Test with non-cached entity (should be slower)
        start_time = time.perf_counter()
        result = await cached_calculation("other_entity")
        uncached_duration = time.perf_counter() - start_time
        
        assert result.capital_requirement == 2000000.0  # New calculation
        assert uncached_duration > 0.1  # Should take longer
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_during_load(self):
        """Test performance monitoring under load"""
        perf_monitor = get_performance_monitor()
        
        # Start monitoring
        await perf_monitor.start_monitoring()
        
        try:
            # Simulate load with concurrent operations
            async def simulate_work(work_id: int):
                # Record request
                start_time = time.perf_counter()
                
                # Simulate some work
                await asyncio.sleep(0.1)
                
                duration = time.perf_counter() - start_time
                perf_monitor.record_request("GET", f"/api/test/{work_id}", 200, duration)
                
                return f"work_{work_id}_done"
            
            # Run concurrent work
            tasks = [simulate_work(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 10
            
            # Check performance metrics
            request_stats = perf_monitor.metrics.get_histogram_stats("http_request_duration")
            assert request_stats["count"] >= 10
            
            # Get system stats
            system_stats = perf_monitor.get_performance_summary()
            assert "system" in system_stats
            assert "metrics" in system_stats
            
        finally:
            # Stop monitoring
            await perf_monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_database_connection_pooling():
    """Test database connection pooling optimization"""
    from orm_calculator.database.connection import DatabaseManager, DatabaseConfig
    
    # Test with SQLite (development)
    config = DatabaseConfig()
    config.environment = "development"
    
    db_manager = DatabaseManager()
    db_manager.config = config
    
    await db_manager.initialize()
    
    try:
        # Test multiple concurrent connections
        async def test_connection():
            async with db_manager.get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar()
        
        # Run concurrent connections
        tasks = [test_connection() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == 1 for result in results)
        
        # Test health check
        health = await db_manager.health_check()
        assert health is True
        
    finally:
        await db_manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])