"""
API module for ORM Capital Calculator Engine
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import time
import uuid

from orm_calculator.api.routes import router
from orm_calculator.config import get_config
from orm_calculator.security.middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    AuthenticationMiddleware,
    RequestLoggingMiddleware
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Custom validation exception handler
    
    Args:
        request: FastAPI request object
        exc: Validation exception
        
    Returns:
        Standardized error response
    """
    error_details = []
    for error in exc.errors():
        error_details.append({
            "error_code": "VALIDATION_ERROR",
            "error_message": error["msg"],
            "field": ".".join(str(x) for x in error["loc"]),
            "details": {"input_value": error.get("input"), "error_type": error["type"]}
        })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "REQUEST_VALIDATION_ERROR",
            "error_message": "Request validation failed",
            "details": {"validation_errors": error_details}
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Custom HTTP exception handler
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        Standardized error response
    """
    # If detail is already a dict (from our custom exceptions), use it directly
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, wrap in standard format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "error_message": exc.detail,
            "details": {}
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    General exception handler for unexpected errors
    
    Args:
        request: FastAPI request object
        exc: Exception
        
    Returns:
        Standardized error response
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "An unexpected error occurred",
            "details": {"error_type": type(exc).__name__}
        }
    )


class RequestLoggingMiddleware:
    """Middleware for request/response logging"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate correlation ID
            correlation_id = str(uuid.uuid4())
            scope["correlation_id"] = correlation_id
            
            # Log request
            request = Request(scope, receive)
            start_time = time.time()
            
            logger.info(
                f"Request started - {request.method} {request.url.path} "
                f"[Correlation ID: {correlation_id}]"
            )
            
            # Process request
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    process_time = time.time() - start_time
                    status_code = message["status"]
                    
                    logger.info(
                        f"Request completed - {request.method} {request.url.path} "
                        f"Status: {status_code} Duration: {process_time:.3f}s "
                        f"[Correlation ID: {correlation_id}]"
                    )
                
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def create_app() -> FastAPI:
    """Create and configure FastAPI application with middleware and error handling"""
    
    # Get configuration
    config = get_config()
    
    # Create FastAPI app with enhanced OpenAPI documentation
    app = FastAPI(
        title="ORM Capital Calculator Engine",
        description="""
        **RBI Basel III SMA Compliance System**
        
        A comprehensive system for calculating operational risk capital requirements 
        in compliance with RBI's Basel III Standardized Measurement Approach (SMA).
        
        ## Features
        
        * **Job-based API**: Synchronous and asynchronous calculation execution
        * **Multiple Methods**: SMA, BIA, TSA, and what-if scenarios
        * **Data Lineage**: Complete audit trail and reproducibility
        * **Parameter Management**: Governed parameter updates with maker-checker workflow
        * **Webhook Notifications**: Real-time job completion notifications
        * **Comprehensive Validation**: Input validation with detailed error messages
        
        ## Authentication
        
        This API uses OAuth 2.0 client credentials flow for authentication.
        Include the `Authorization: Bearer <token>` header in your requests.
        
        ## Rate Limiting
        
        API requests are rate-limited to ensure system stability:
        * 100 requests per minute for calculation endpoints
        * 1000 requests per minute for status/health endpoints
        
        ## Error Handling
        
        All errors follow a standardized format:
        ```json
        {
            "error_code": "ERROR_CODE",
            "error_message": "Human readable message",
            "details": {
                "additional": "context"
            }
        }
        ```
        """,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "calculations",
                "description": "Capital calculation operations with job management"
            },
            {
                "name": "loss-data",
                "description": "Loss data management and validation"
            },
            {
                "name": "lineage",
                "description": "Data lineage tracking and audit trail access"
            },
            {
                "name": "health",
                "description": "System health and monitoring endpoints"
            }
        ],
        contact={
            "name": "ORM Capital Calculator Support",
            "email": "support@example.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        }
    )
    
    # Add security middleware (order matters - add from innermost to outermost)
    
    # Add performance monitoring middleware (innermost)
    from orm_calculator.core.performance import PerformanceMiddleware
    app.add_middleware(PerformanceMiddleware)
    
    # Add custom request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.security.cors_origins,
        allow_credentials=config.security.cors_allow_credentials,
        allow_methods=config.security.cors_allow_methods,
        allow_headers=config.security.cors_allow_headers,
        expose_headers=["X-Correlation-ID", "X-Request-ID", "X-Process-Time"]
    )
    
    # Add trusted host middleware for security (outermost)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.security.trusted_hosts
    )
    
    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        """Application startup event"""
        logger.info("ORM Capital Calculator Engine starting up...")
        
        # Initialize database connections
        from orm_calculator.database.connection import init_database
        await init_database()
        logger.info("Database initialized")
        
        # Start job processor
        from orm_calculator.api.calculation_routes import get_job_service_instance
        job_service = await get_job_service_instance()
        logger.info("Job processor started")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event"""
        logger.info("ORM Capital Calculator Engine shutting down...")
        
        # Stop job processor
        from orm_calculator.api.calculation_routes import job_service_instance
        if job_service_instance:
            await job_service_instance.stop_job_processor()
            logger.info("Job processor stopped")
        
        # Close database connections
        from orm_calculator.database.connection import close_database
        await close_database()
        logger.info("Database connections closed")
    
    return app