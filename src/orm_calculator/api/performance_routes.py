"""
Performance monitoring and profiling API routes for ORM Capital Calculator Engine

Provides endpoints for performance metrics, profiling data, cache statistics,
and system monitoring for development and production monitoring.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from orm_calculator.core.performance import get_performance_monitor, PerformanceMonitor
from orm_calculator.core.cache import get_cache_manager, CacheManager
from orm_calculator.core.database_optimization import get_query_executor, ConcurrentQueryExecutor
from orm_calculator.database.connection import get_db_session
from orm_calculator.security.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/api/v1/performance", tags=["performance"])


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response model"""
    system: Dict[str, Any] = Field(..., description="System resource metrics")
    metrics: Dict[str, Any] = Field(..., description="Application metrics")
    profiles: Dict[str, Any] = Field(..., description="Performance profiles")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CacheStatsResponse(BaseModel):
    """Cache statistics response model"""
    cache_type: str = Field(..., description="Type of cache (memory/redis)")
    stats: Dict[str, Any] = Field(..., description="Cache statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DatabaseStatsResponse(BaseModel):
    """Database performance statistics response model"""
    connection_pool: Dict[str, Any] = Field(..., description="Connection pool statistics")
    query_stats: Dict[str, Any] = Field(..., description="Query performance statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ProfilingRequest(BaseModel):
    """Request model for performance profiling"""
    operation_name: str = Field(..., description="Name of operation to profile")
    duration_seconds: int = Field(default=60, ge=1, le=300, description="Profiling duration in seconds")
    include_system_metrics: bool = Field(default=True, description="Include system resource metrics")


class ProfilingResponse(BaseModel):
    """Response model for performance profiling results"""
    operation_name: str = Field(..., description="Name of profiled operation")
    duration_seconds: int = Field(..., description="Actual profiling duration")
    profile_data: Dict[str, Any] = Field(..., description="Detailed profiling data")
    system_metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics during profiling")
    recommendations: List[str] = Field(default_factory=list, description="Performance recommendations")


@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor)
) -> PerformanceMetricsResponse:
    """
    Get comprehensive performance metrics including system resources,
    application metrics, and profiling data.
    """
    try:
        summary = performance_monitor.get_performance_summary()
        
        return PerformanceMetricsResponse(
            system=summary["system"],
            metrics=summary["metrics"],
            profiles=summary["profiles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    current_user: dict = Depends(get_current_user),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> CacheStatsResponse:
    """
    Get cache performance statistics including hit rates,
    memory usage, and cache efficiency metrics.
    """
    try:
        stats = await cache_manager.cache.get_stats()
        cache_type = "redis" if hasattr(cache_manager.cache, '_redis') else "memory"
        
        return CacheStatsResponse(
            cache_type=cache_type,
            stats=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache statistics: {str(e)}")


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_statistics(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> DatabaseStatsResponse:
    """
    Get database performance statistics including connection pool
    health and query performance metrics.
    """
    try:
        # Get connection pool stats (if available)
        pool_stats = {}
        if hasattr(session.bind, 'pool'):
            pool = session.bind.pool
            pool_stats = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid()
            }
        
        # Get query performance stats from performance monitor
        performance_monitor = get_performance_monitor()
        query_stats = performance_monitor.metrics.get_histogram_stats("db_query_duration")
        
        return DatabaseStatsResponse(
            connection_pool=pool_stats,
            query_stats=query_stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database statistics: {str(e)}")


@router.get("/system/health")
async def get_system_health(
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor)
) -> Dict[str, Any]:
    """
    Get system health status including resource utilization,
    performance thresholds, and health indicators.
    """
    try:
        system_stats = performance_monitor.system_monitor.get_memory_usage()
        cpu_stats = performance_monitor.system_monitor.get_cpu_usage()
        disk_stats = performance_monitor.system_monitor.get_disk_usage()
        
        # Determine health status based on thresholds
        health_status = "healthy"
        warnings = []
        
        if system_stats["percent"] > 85:
            health_status = "warning"
            warnings.append(f"High memory usage: {system_stats['percent']:.1f}%")
        
        if cpu_stats["process_percent"] > 80:
            health_status = "warning"
            warnings.append(f"High CPU usage: {cpu_stats['process_percent']:.1f}%")
        
        if disk_stats["percent"] > 90:
            health_status = "critical"
            warnings.append(f"High disk usage: {disk_stats['percent']:.1f}%")
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "memory": system_stats,
            "cpu": cpu_stats,
            "disk": disk_stats,
            "warnings": warnings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


@router.post("/profile", response_model=ProfilingResponse)
async def start_performance_profiling(
    request: ProfilingRequest,
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor)
) -> ProfilingResponse:
    """
    Start performance profiling for a specific operation.
    This endpoint is primarily for development and debugging.
    """
    try:
        import asyncio
        
        # Start profiling
        start_time = datetime.utcnow()
        initial_stats = performance_monitor.get_performance_summary() if request.include_system_metrics else None
        
        # Wait for the specified duration while collecting metrics
        await asyncio.sleep(request.duration_seconds)
        
        # Get final stats
        final_stats = performance_monitor.get_performance_summary() if request.include_system_metrics else None
        
        # Get profile data for the operation
        profile_data = performance_monitor.profiler.get_profile_stats(request.operation_name)
        
        # Generate recommendations based on profile data
        recommendations = _generate_performance_recommendations(profile_data, initial_stats, final_stats)
        
        return ProfilingResponse(
            operation_name=request.operation_name,
            duration_seconds=request.duration_seconds,
            profile_data=profile_data,
            system_metrics=final_stats,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start profiling: {str(e)}")


@router.get("/profiles/{operation_name}")
async def get_operation_profile(
    operation_name: str,
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor)
) -> Dict[str, Any]:
    """
    Get profiling data for a specific operation.
    """
    try:
        profile_data = performance_monitor.profiler.get_profile_stats(operation_name)
        
        if profile_data.get("count", 0) == 0:
            raise HTTPException(status_code=404, detail=f"No profiling data found for operation: {operation_name}")
        
        return {
            "operation_name": operation_name,
            "profile_data": profile_data,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get operation profile: {str(e)}")


@router.get("/metrics/history")
async def get_metrics_history(
    metric_name: str = Query(..., description="Name of the metric to retrieve"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours of history to retrieve"),
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor)
) -> Dict[str, Any]:
    """
    Get historical metrics data for trend analysis.
    """
    try:
        # Get metrics from the collector
        metrics = performance_monitor.metrics.get_metrics(metric_name)
        
        # Filter by time range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_metrics = [
            {
                "value": m.value,
                "timestamp": m.timestamp.isoformat(),
                "labels": m.labels
            }
            for m in metrics
            if m.timestamp >= cutoff_time
        ]
        
        if not filtered_metrics:
            return {
                "metric_name": metric_name,
                "data_points": [],
                "summary": {"count": 0}
            }
        
        # Calculate summary statistics
        values = [m["value"] for m in filtered_metrics]
        summary = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1] if values else 0
        }
        
        return {
            "metric_name": metric_name,
            "time_range_hours": hours,
            "data_points": filtered_metrics,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics history: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Pattern to match for selective clearing"),
    current_user: dict = Depends(get_current_user),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, str]:
    """
    Clear cache entries. Use with caution in production.
    """
    try:
        await cache_manager.cache.clear(pattern)
        
        return {
            "status": "success",
            "message": f"Cache cleared{f' with pattern: {pattern}' if pattern else ' completely'}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/recommendations")
async def get_performance_recommendations(
    current_user: dict = Depends(get_current_user),
    performance_monitor: PerformanceMonitor = Depends(get_performance_monitor),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> Dict[str, List[str]]:
    """
    Get performance optimization recommendations based on current metrics.
    """
    try:
        recommendations = {
            "system": [],
            "cache": [],
            "database": [],
            "application": []
        }
        
        # System recommendations
        system_stats = performance_monitor.system_monitor.get_memory_usage()
        cpu_stats = performance_monitor.system_monitor.get_cpu_usage()
        
        if system_stats["percent"] > 80:
            recommendations["system"].append("Consider increasing available memory or optimizing memory usage")
        
        if cpu_stats["process_percent"] > 70:
            recommendations["system"].append("High CPU usage detected - consider optimizing calculations or scaling horizontally")
        
        # Cache recommendations
        cache_stats = await cache_manager.cache.get_stats()
        hit_rate = cache_stats.get("hit_rate", 0)
        
        if hit_rate < 0.7:
            recommendations["cache"].append("Low cache hit rate - consider adjusting TTL or cache keys")
        
        if cache_stats.get("size", 0) > cache_stats.get("max_size", 1000) * 0.9:
            recommendations["cache"].append("Cache near capacity - consider increasing cache size or reducing TTL")
        
        # Database recommendations
        db_stats = performance_monitor.metrics.get_histogram_stats("db_query_duration")
        if db_stats.get("avg", 0) > 1.0:  # Average query time > 1 second
            recommendations["database"].append("Slow database queries detected - consider adding indexes or optimizing queries")
        
        # Application recommendations
        calc_stats = performance_monitor.metrics.get_histogram_stats("calculation_duration")
        if calc_stats.get("p95", 0) > 30.0:  # 95th percentile > 30 seconds
            recommendations["application"].append("Long calculation times detected - consider using async processing or optimization")
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


def _generate_performance_recommendations(profile_data: Dict[str, Any], 
                                        initial_stats: Optional[Dict[str, Any]], 
                                        final_stats: Optional[Dict[str, Any]]) -> List[str]:
    """Generate performance recommendations based on profiling data"""
    recommendations = []
    
    if profile_data.get("count", 0) == 0:
        return ["No profiling data available for recommendations"]
    
    avg_duration = profile_data.get("avg_duration", 0)
    max_duration = profile_data.get("max_duration", 0)
    avg_memory_delta = profile_data.get("avg_memory_delta", 0)
    
    # Duration-based recommendations
    if avg_duration > 5.0:
        recommendations.append("Average operation duration is high - consider optimization or caching")
    
    if max_duration > avg_duration * 3:
        recommendations.append("High variance in operation duration - investigate performance bottlenecks")
    
    # Memory-based recommendations
    if avg_memory_delta > 100 * 1024 * 1024:  # 100MB
        recommendations.append("High memory usage per operation - consider memory optimization")
    
    # System-based recommendations
    if initial_stats and final_stats:
        memory_increase = (final_stats["system"]["memory"]["percent"] - 
                          initial_stats["system"]["memory"]["percent"])
        
        if memory_increase > 10:
            recommendations.append("Significant memory increase during profiling - check for memory leaks")
    
    if not recommendations:
        recommendations.append("Performance appears optimal based on current metrics")
    
    return recommendations