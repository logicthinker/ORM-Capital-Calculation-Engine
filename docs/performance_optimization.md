# Performance Optimization Guide

This document describes the performance optimization features implemented in the ORM Capital Calculator Engine, including caching, concurrent processing, database optimization, and monitoring capabilities.

## Overview

The performance optimization system includes:

- **Redis-based caching** for frequently accessed parameters and calculation results
- **Database query optimization** with proper indexing strategies
- **Calculation result caching** with configurable TTL management
- **Concurrent processing** for independent calculations using asyncio task groups
- **Performance monitoring** with metrics collection
- **Database connection pooling** with configurable pool sizes
- **Query result pagination** for large datasets
- **Performance profiling endpoints** for development and monitoring

## Caching System

### Cache Types

The system supports two cache implementations:

1. **Memory Cache** (Development)
   - In-memory storage with LRU eviction
   - Configurable maximum size
   - No external dependencies

2. **Redis Cache** (Production)
   - Distributed caching with Redis
   - Automatic failover and reconnection
   - Configurable TTL and eviction policies

### Cache Configuration

```python
from orm_calculator.core.cache import CacheConfig, CacheType

# Memory cache configuration
config = CacheConfig(
    cache_type=CacheType.MEMORY,
    max_memory_cache_size=1000,
    default_ttl=3600
)

# Redis cache configuration
config = CacheConfig(
    cache_type=CacheType.REDIS,
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    default_ttl=3600
)
```

### Cache Usage

```python
from orm_calculator.core.cache import get_cache_manager

# Get cache manager
cache_manager = await get_cache_manager()

# Cache calculation result
await cache_manager.cache_calculation_result(
    entity_id="ENTITY001",
    calculation_date="2024-01-01",
    model_name="SMA",
    parameters_hash="abc123",
    result=calculation_result,
    ttl=3600
)

# Retrieve cached result
cached_result = await cache_manager.get_calculation_result(
    entity_id="ENTITY001",
    calculation_date="2024-01-01",
    model_name="SMA",
    parameters_hash="abc123"
)
```

## Performance Monitoring

### Metrics Collection

The system collects various performance metrics:

- **Response times** for HTTP requests
- **Memory usage** and CPU utilization
- **Database query performance**
- **Cache hit/miss rates**
- **Calculation execution times**
- **Error rates** and failure counts

### Performance Monitoring Usage

```python
from orm_calculator.core.performance import get_performance_monitor

# Get performance monitor
monitor = get_performance_monitor()

# Record custom metrics
monitor.metrics.increment_counter("custom_operation", labels={"type": "calculation"})
monitor.metrics.record_histogram("operation_duration", 1.5)
monitor.metrics.set_gauge("active_connections", 10)

# Get performance summary
summary = monitor.get_performance_summary()
```

### Performance Profiling

```python
from orm_calculator.core.performance import performance_timer

# Decorator for automatic timing
@performance_timer("calculation_execution")
async def calculate_capital(request):
    # Calculation logic here
    pass

# Context manager for profiling
async with monitor.profiler.profile("database_query"):
    result = await session.execute(query)
```

## Database Optimization

### Connection Pooling

The system uses optimized connection pooling:

**SQLite (Development):**
- Static pool with optimized pragmas
- WAL mode for better concurrency
- Memory-mapped I/O for performance

**PostgreSQL (Production):**
- Configurable pool size and overflow
- Connection pre-ping for health checks
- Automatic connection recycling

### Database Indexes

Recommended indexes are automatically created:

```sql
-- Business indicators
CREATE INDEX idx_business_indicators_entity_date ON business_indicators(entity_id, calculation_date);

-- Loss events
CREATE INDEX idx_loss_events_entity_dates ON loss_events(entity_id, accounting_date, occurrence_date);

-- Capital calculations
CREATE INDEX idx_capital_calculations_run_id ON capital_calculations(run_id);
```

### Query Optimization

```python
from orm_calculator.core.database_optimization import get_database_optimizer, DatabaseType

# Get optimizer for your database
optimizer = get_database_optimizer(DatabaseType.POSTGRESQL)

# Optimize query
optimized_query, params = await optimizer.optimize_query(original_query, params)
```

## Concurrent Processing

### Task Groups

Execute multiple tasks concurrently:

```python
from orm_calculator.core.concurrent_processing import TaskGroup, ConcurrentConfig

config = ConcurrentConfig(max_concurrent_tasks=10, timeout_seconds=300)

async with TaskGroup(config) as task_group:
    await task_group.add_async_task("calc1", calculate_entity_1())
    await task_group.add_async_task("calc2", calculate_entity_2())
    
    results = await task_group.wait_all()
```

### Batch Processing

Process multiple calculations efficiently:

```python
from orm_calculator.core.concurrent_processing import get_calculation_batch

batch = get_calculation_batch()

# Process multiple entities
results = await batch.process_entity_calculations(
    entities=["ENTITY001", "ENTITY002", "ENTITY003"],
    calculation_func=calculate_sma,
    model_name="SMA"
)
```

### Parallel Data Processing

Process large datasets in chunks:

```python
from orm_calculator.core.concurrent_processing import get_data_processor

processor = get_data_processor(chunk_size=1000, max_concurrent=5)

results = await processor.process_data_chunks(
    data=large_dataset,
    processor_func=process_chunk
)
```

## API Endpoints

### Performance Metrics

```http
GET /api/v1/performance/metrics
```

Returns comprehensive performance metrics including system resources, application metrics, and profiling data.

### Cache Statistics

```http
GET /api/v1/performance/cache/stats
```

Returns cache performance statistics including hit rates and memory usage.

### Database Statistics

```http
GET /api/v1/performance/database/stats
```

Returns database performance statistics including connection pool health.

### System Health

```http
GET /api/v1/performance/system/health
```

Returns system health status with resource utilization and warnings.

### Performance Profiling

```http
POST /api/v1/performance/profile
Content-Type: application/json

{
    "operation_name": "sma_calculation",
    "duration_seconds": 60,
    "include_system_metrics": true
}
```

Starts performance profiling for a specific operation.

## Configuration

### Environment Variables

```bash
# Cache Configuration
CACHE_TYPE=redis
CACHE_TTL=3600
REDIS_HOST=localhost
REDIS_PORT=6379

# Performance Monitoring
PERFORMANCE_MONITORING_ENABLED=true
PERFORMANCE_MONITORING_INTERVAL=30
MAX_CONCURRENT_CALCULATIONS=10

# Database Optimization
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
```

### Application Configuration

```python
from orm_calculator.core.cache import CacheConfig, CacheType
from orm_calculator.core.concurrent_processing import ConcurrentConfig

# Cache configuration
cache_config = CacheConfig(
    cache_type=CacheType.REDIS,
    redis_host="redis-server",
    default_ttl=3600
)

# Concurrent processing configuration
concurrent_config = ConcurrentConfig(
    max_concurrent_tasks=10,
    max_thread_workers=4,
    timeout_seconds=300
)
```

## Best Practices

### Caching Strategy

1. **Cache calculation results** with appropriate TTL based on data volatility
2. **Use cache invalidation** when underlying data changes
3. **Monitor cache hit rates** and adjust TTL accordingly
4. **Implement cache warming** for frequently accessed data

### Performance Monitoring

1. **Set up alerts** for performance thresholds
2. **Monitor resource utilization** regularly
3. **Profile critical operations** during development
4. **Track performance trends** over time

### Database Optimization

1. **Create appropriate indexes** for query patterns
2. **Monitor query performance** and optimize slow queries
3. **Use connection pooling** effectively
4. **Implement query pagination** for large result sets

### Concurrent Processing

1. **Limit concurrency** to avoid resource exhaustion
2. **Handle errors gracefully** in concurrent operations
3. **Use appropriate timeout values**
4. **Monitor task completion rates**

## Troubleshooting

### High Memory Usage

1. Check cache size and eviction policies
2. Monitor for memory leaks in calculations
3. Adjust concurrent task limits
4. Review data processing chunk sizes

### Slow Performance

1. Check cache hit rates
2. Analyze database query performance
3. Monitor system resource utilization
4. Review concurrent processing configuration

### Cache Issues

1. Verify Redis connectivity (if using Redis cache)
2. Check cache TTL settings
3. Monitor cache eviction rates
4. Review cache key patterns

### Database Performance

1. Check connection pool utilization
2. Analyze slow query logs
3. Verify index usage
4. Monitor connection timeouts

## Monitoring and Alerting

Set up monitoring for key metrics:

- **Response time percentiles** (p50, p95, p99)
- **Error rates** by operation type
- **Cache hit rates** by cache type
- **Database connection pool** utilization
- **System resource usage** (CPU, memory, disk)
- **Concurrent task** completion rates

Configure alerts for:

- Response times exceeding thresholds
- Error rates above acceptable levels
- Cache hit rates below targets
- Resource utilization limits
- Database connection pool exhaustion