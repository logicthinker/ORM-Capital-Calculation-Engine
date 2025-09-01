#!/usr/bin/env python3
"""
Simple test script to verify performance optimization components
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_cache():
    """Test cache functionality"""
    print("Testing cache functionality...")
    
    from orm_calculator.core.cache import initialize_cache, CacheConfig, CacheType
    
    # Test memory cache
    config = CacheConfig(cache_type=CacheType.MEMORY, max_memory_cache_size=100)
    cache_manager = await initialize_cache(config)
    
    # Test basic operations
    await cache_manager.cache.set("test_key", "test_value", ttl=60)
    value = await cache_manager.cache.get("test_key")
    assert value == "test_value", f"Expected 'test_value', got {value}"
    
    # Test exists
    exists = await cache_manager.cache.exists("test_key")
    assert exists is True, "Key should exist"
    
    # Test delete
    await cache_manager.cache.delete("test_key")
    value = await cache_manager.cache.get("test_key")
    assert value is None, "Key should be deleted"
    
    print("✓ Cache functionality working")

async def test_performance_monitoring():
    """Test performance monitoring"""
    print("Testing performance monitoring...")
    
    from orm_calculator.core.performance import get_performance_monitor
    
    monitor = get_performance_monitor()
    
    # Test metrics
    monitor.metrics.increment_counter("test_counter", 5)
    counter_value = monitor.metrics.get_counter("test_counter")
    assert counter_value == 5, f"Expected 5, got {counter_value}"
    
    # Test gauge
    monitor.metrics.set_gauge("test_gauge", 42.5)
    gauge_value = monitor.metrics.get_gauge("test_gauge")
    assert gauge_value == 42.5, f"Expected 42.5, got {gauge_value}"
    
    # Test histogram
    monitor.metrics.record_histogram("test_histogram", 1.5)
    stats = monitor.metrics.get_histogram_stats("test_histogram")
    assert stats["count"] == 1, f"Expected count 1, got {stats['count']}"
    
    print("✓ Performance monitoring working")

async def test_concurrent_processing():
    """Test concurrent processing"""
    print("Testing concurrent processing...")
    
    from orm_calculator.core.concurrent_processing import TaskGroup, ConcurrentConfig
    
    config = ConcurrentConfig(max_concurrent_tasks=3)
    
    async def test_task(value):
        await asyncio.sleep(0.1)
        return value * 2
    
    async with TaskGroup(config) as task_group:
        await task_group.add_async_task("task1", test_task(1))
        await task_group.add_async_task("task2", test_task(2))
        await task_group.add_async_task("task3", test_task(3))
        
        results = await task_group.wait_all()
    
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert all(result.success for result in results.values()), "All tasks should succeed"
    
    print("✓ Concurrent processing working")

async def test_database_optimization():
    """Test database optimization"""
    print("Testing database optimization...")
    
    from orm_calculator.core.database_optimization import (
        get_database_optimizer, DatabaseType, get_index_manager
    )
    
    # Test SQLite optimizer
    optimizer = get_database_optimizer(DatabaseType.SQLITE)
    config = optimizer.get_connection_pool_config()
    assert "poolclass" in config, "Pool config should have poolclass"
    
    # Test index manager
    index_manager = get_index_manager(DatabaseType.POSTGRESQL)
    indexes = index_manager.get_recommended_indexes()
    assert len(indexes) > 0, "Should have recommended indexes"
    
    print("✓ Database optimization working")

async def main():
    """Run all tests"""
    print("Running performance optimization tests...\n")
    
    try:
        await test_cache()
        await test_performance_monitoring()
        await test_concurrent_processing()
        await test_database_optimization()
        
        print("\n✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)