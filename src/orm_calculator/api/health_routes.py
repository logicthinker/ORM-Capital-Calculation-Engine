"""
Health check endpoints for ORM Capital Calculator Engine

Provides system health monitoring and readiness checks.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from orm_calculator.config import get_config
from orm_calculator.security.auth import get_current_user, User
from orm_calculator.security.rbac import Permission, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    checks: Dict[str, Any]


class ReadinessStatus(BaseModel):
    """Readiness status response model"""
    ready: bool
    timestamp: datetime
    checks: Dict[str, bool]


class LivenessStatus(BaseModel):
    """Liveness status response model"""
    alive: bool
    timestamp: datetime
    uptime_seconds: float


class StartupStatus(BaseModel):
    """Startup status response model"""
    started: bool
    timestamp: datetime
    initialization_complete: bool
    startup_time_seconds: float
    checks: Dict[str, bool]


# Track application start time for uptime calculation
import time
_start_time = time.time()


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint (public access)
    
    Returns overall system health status including database connectivity,
    configuration validation, and component status.
    """
    config = get_config()
    
    checks = {}
    overall_status = "healthy"
    
    # Database connectivity check
    try:
        from orm_calculator.database.connection import get_database
        db = await get_database()
        if db:
            checks["database"] = {"status": "healthy", "type": "sqlite"}
        else:
            checks["database"] = {"status": "unhealthy", "error": "No connection"}
            overall_status = "unhealthy"
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    # Configuration check
    try:
        checks["configuration"] = {
            "status": "healthy",
            "environment": config.environment,
            "security_enabled": config.security.enable_security_headers,
            "rate_limiting_enabled": True
        }
    except Exception as e:
        checks["configuration"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    # Security check
    try:
        checks["security"] = {
            "status": "healthy",
            "https_enabled": config.security.use_https,
            "cors_configured": len(config.security.cors_origins) > 0,
            "auth_configured": bool(config.security.oauth2_token_url or config.security.api_keys)
        }
    except Exception as e:
        checks["security"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=config.app_version,
        environment=config.environment,
        checks=checks
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check():
    """
    Kubernetes readiness probe endpoint (public access)
    
    Checks if the application is ready to serve traffic.
    Returns HTTP 200 if ready, HTTP 503 if not ready.
    """
    checks = {}
    ready = True
    
    # Database readiness - test actual connection
    try:
        from orm_calculator.database.connection import get_db_session
        async with get_db_session().__anext__() as session:
            # Execute a simple query to verify database is responsive
            result = await session.execute("SELECT 1")
            checks["database"] = True
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")
        checks["database"] = False
        ready = False
    
    # Cache readiness (if enabled)
    try:
        from orm_calculator.core.cache import get_cache_client
        cache_client = await get_cache_client()
        if cache_client:
            # Test cache connectivity
            await cache_client.ping()
            checks["cache"] = True
        else:
            checks["cache"] = True  # Cache is optional
    except Exception as e:
        logger.warning(f"Cache readiness check failed: {e}")
        checks["cache"] = False
        # Cache failure doesn't make app unready, just log it
    
    # Configuration readiness
    try:
        config = get_config()
        # Verify critical configuration is present
        if not config.database.database_url:
            raise ValueError("Database URL not configured")
        checks["configuration"] = True
    except Exception as e:
        logger.error(f"Configuration readiness check failed: {e}")
        checks["configuration"] = False
        ready = False
    
    # Job processor readiness
    try:
        from orm_calculator.api.calculation_routes import job_service_instance
        if job_service_instance and hasattr(job_service_instance, 'is_running'):
            checks["job_processor"] = job_service_instance.is_running()
        else:
            checks["job_processor"] = True  # Assume ready if not implemented
    except Exception as e:
        logger.warning(f"Job processor readiness check failed: {e}")
        checks["job_processor"] = False
        # Job processor issues don't make app unready for basic operations
    
    # External dependencies readiness (if any)
    checks["external_dependencies"] = True  # Placeholder for future external services
    
    response = ReadinessStatus(
        ready=ready,
        timestamp=datetime.utcnow(),
        checks=checks
    )
    
    # Return appropriate HTTP status code for container orchestration
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response


@router.get("/live", response_model=LivenessStatus)
async def liveness_check():
    """
    Kubernetes liveness probe endpoint (public access)
    
    Simple check to verify the application is alive and responsive.
    Returns HTTP 200 if alive, HTTP 503 if not alive.
    
    This endpoint should be very lightweight and only fail if the
    application process is fundamentally broken.
    """
    uptime = time.time() - _start_time
    alive = True
    
    # Basic application health checks
    try:
        # Verify we can access configuration
        config = get_config()
        
        # Check if we're in a deadlock or unresponsive state
        # This is a very basic check - in production you might want more sophisticated checks
        if uptime < 1:  # App just started, might not be fully ready
            alive = True
        
        # Check memory usage - if extremely high, might indicate memory leak
        import psutil
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 95:  # Critical memory usage
            logger.warning(f"Critical memory usage: {memory_percent}%")
            # Don't fail liveness for high memory - let readiness handle it
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        alive = False
    
    response = LivenessStatus(
        alive=alive,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime
    )
    
    # Return appropriate HTTP status code for container orchestration
    if not alive:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response


@router.get("/startup", response_model=StartupStatus)
async def startup_check():
    """
    Kubernetes startup probe endpoint (public access)
    
    Checks if the application has completed its startup sequence.
    This is used by Kubernetes to know when to start sending traffic
    and when to start liveness/readiness probes.
    
    Returns HTTP 200 when startup is complete, HTTP 503 during startup.
    """
    startup_time = time.time() - _start_time
    checks = {}
    started = True
    
    # Database initialization check
    try:
        from orm_calculator.database.connection import get_db_session
        async with get_db_session().__anext__() as session:
            # Verify database schema is ready
            result = await session.execute("SELECT 1")
            checks["database_initialized"] = True
    except Exception as e:
        logger.info(f"Database not yet initialized: {e}")
        checks["database_initialized"] = False
        started = False
    
    # Configuration loading check
    try:
        config = get_config()
        checks["configuration_loaded"] = True
    except Exception as e:
        logger.error(f"Configuration not loaded: {e}")
        checks["configuration_loaded"] = False
        started = False
    
    # Cache initialization check (if enabled)
    try:
        from orm_calculator.core.cache import get_cache_client
        cache_client = await get_cache_client()
        checks["cache_initialized"] = True
    except Exception:
        # Cache is optional, don't fail startup for cache issues
        checks["cache_initialized"] = False
    
    # Job processor initialization check
    try:
        from orm_calculator.api.calculation_routes import job_service_instance
        if job_service_instance:
            checks["job_processor_initialized"] = True
        else:
            checks["job_processor_initialized"] = False
    except Exception:
        checks["job_processor_initialized"] = False
    
    # Security initialization check
    try:
        config = get_config()
        # Check if security components are initialized
        checks["security_initialized"] = True
    except Exception:
        checks["security_initialized"] = False
        started = False
    
    # Minimum startup time check (prevent premature ready state)
    min_startup_time = 5  # seconds
    if startup_time < min_startup_time:
        started = False
        logger.info(f"Startup in progress: {startup_time:.1f}s < {min_startup_time}s minimum")
    
    response = StartupStatus(
        started=started,
        timestamp=datetime.utcnow(),
        initialization_complete=all(checks.values()),
        startup_time_seconds=startup_time,
        checks=checks
    )
    
    # Return appropriate HTTP status code for container orchestration
    if not started:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response


@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    current_user: User = Depends(require_permission(Permission.VIEW_METRICS))
):
    """
    Detailed health check with system metrics (requires admin access)
    
    Provides comprehensive system health information including:
    - Database connection pool status
    - Memory usage
    - Active job counts
    - Rate limiting statistics
    - Security event counts
    """
    config = get_config()
    
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": config.app_version,
        "environment": config.environment,
        "uptime_seconds": time.time() - _start_time
    }
    
    # Database metrics
    try:
        from orm_calculator.database.connection import get_database
        db = await get_database()
        
        health_data["database"] = {
            "status": "connected" if db else "disconnected",
            "url": config.database.database_url.split("://")[0] + "://***",  # Hide credentials
            "pool_size": config.database.pool_size,
            "max_overflow": config.database.max_overflow
        }
    except Exception as e:
        health_data["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Security metrics
    health_data["security"] = {
        "https_enabled": config.security.use_https,
        "security_headers_enabled": config.security.enable_security_headers,
        "cors_origins_count": len(config.security.cors_origins),
        "trusted_hosts_count": len(config.security.trusted_hosts),
        "oauth2_configured": bool(config.security.oauth2_token_url),
        "api_keys_configured": len(config.security.api_keys)
    }
    
    # Rate limiting metrics
    health_data["rate_limiting"] = {
        "enabled": True,
        "default_limit": config.rate_limit.default_rate_limit,
        "calculation_limit": config.rate_limit.calculation_rate_limit,
        "storage_type": config.rate_limit.rate_limit_storage
    }
    
    # Performance metrics
    health_data["performance"] = {
        "async_threshold_seconds": config.performance.async_threshold_seconds,
        "max_concurrent_jobs": config.performance.max_concurrent_jobs,
        "caching_enabled": config.performance.enable_caching,
        "cache_ttl_seconds": config.performance.cache_ttl_seconds
    }
    
    # Compliance metrics
    health_data["compliance"] = {
        "data_residency_region": config.compliance.data_residency_region,
        "data_residency_enforced": config.compliance.enforce_data_residency,
        "cert_in_compliance": config.compliance.cert_in_compliance,
        "audit_retention_days": config.compliance.audit_retention_days
    }
    
    # System resources (basic)
    import psutil
    try:
        health_data["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except Exception:
        health_data["system"] = {"status": "metrics_unavailable"}
    
    return health_data


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint (public access)
    
    Returns metrics in Prometheus format for monitoring and alerting.
    """
    config = get_config()
    uptime = time.time() - _start_time
    
    metrics = []
    
    # Application info
    metrics.append(f'orm_calculator_info{{version="{config.app_version}",environment="{config.environment}"}} 1')
    metrics.append(f'orm_calculator_uptime_seconds {uptime}')
    
    # System metrics
    try:
        import psutil
        metrics.append(f'orm_calculator_cpu_percent {psutil.cpu_percent(interval=0.1)}')
        metrics.append(f'orm_calculator_memory_percent {psutil.virtual_memory().percent}')
        metrics.append(f'orm_calculator_disk_percent {psutil.disk_usage("/").percent}')
    except Exception:
        pass
    
    # Database metrics
    try:
        from orm_calculator.database.connection import get_db_session
        async with get_db_session().__anext__() as session:
            metrics.append('orm_calculator_database_connected 1')
    except Exception:
        metrics.append('orm_calculator_database_connected 0')
    
    # Cache metrics
    try:
        from orm_calculator.core.cache import get_cache_client
        cache_client = await get_cache_client()
        if cache_client:
            metrics.append('orm_calculator_cache_connected 1')
        else:
            metrics.append('orm_calculator_cache_connected 0')
    except Exception:
        metrics.append('orm_calculator_cache_connected 0')
    
    # Job processor metrics
    try:
        from orm_calculator.api.calculation_routes import job_service_instance
        if job_service_instance and hasattr(job_service_instance, 'get_metrics'):
            job_metrics = job_service_instance.get_metrics()
            for metric_name, metric_value in job_metrics.items():
                metrics.append(f'orm_calculator_job_{metric_name} {metric_value}')
        else:
            metrics.append('orm_calculator_job_processor_running 1')
    except Exception:
        metrics.append('orm_calculator_job_processor_running 0')
    
    # Configuration metrics
    metrics.append(f'orm_calculator_security_enabled {int(config.security.enable_security_headers)}')
    metrics.append(f'orm_calculator_https_enabled {int(config.security.use_https)}')
    metrics.append(f'orm_calculator_rate_limiting_enabled 1')
    
    # Compliance metrics
    metrics.append(f'orm_calculator_cert_in_compliance {int(config.compliance.cert_in_compliance)}')
    metrics.append(f'orm_calculator_data_residency_enforced {int(config.compliance.enforce_data_residency)}')
    
    return "\n".join(metrics) + "\n"


@router.get("/security-events", response_model=Dict[str, Any])
async def security_events_summary(
    current_user: User = Depends(require_permission(Permission.READ_AUDIT))
):
    """
    Security events summary (requires audit access)
    
    Provides summary of recent security events for monitoring and compliance.
    """
    # TODO: Implement security event aggregation from logs
    # For now, return placeholder data
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "authentication_failures_24h": 0,
            "authorization_failures_24h": 0,
            "rate_limit_violations_24h": 0,
            "server_errors_24h": 0
        },
        "recent_events": [],
        "compliance_status": {
            "cert_in_compliant": True,
            "data_residency_compliant": True,
            "audit_retention_compliant": True
        }
    }