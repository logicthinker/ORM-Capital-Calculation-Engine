"""
Main application entry point for ORM Capital Calculator Engine
"""

import uvicorn
import asyncio
import logging
import os

from orm_calculator.api import create_app
from orm_calculator.database import init_database, close_database
from orm_calculator.core.cache import initialize_cache, close_cache, CacheConfig, CacheType
from orm_calculator.core.performance import get_performance_monitor
from orm_calculator.core.database_optimization import get_index_manager, DatabaseType


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def startup():
    """Application startup tasks"""
    logger.info("Starting ORM Capital Calculator Engine...")
    
    # Initialize database
    logger.info("Initializing database...")
    await init_database()
    logger.info("Database initialized successfully")
    
    # Initialize cache
    logger.info("Initializing cache...")
    cache_config = CacheConfig(
        cache_type=CacheType.REDIS if os.getenv("ENVIRONMENT") == "production" else CacheType.MEMORY,
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        default_ttl=int(os.getenv("CACHE_TTL", "3600"))
    )
    await initialize_cache(cache_config)
    logger.info("Cache initialized successfully")
    
    # Initialize performance monitoring
    logger.info("Starting performance monitoring...")
    performance_monitor = get_performance_monitor()
    await performance_monitor.start_monitoring()
    logger.info("Performance monitoring started")
    
    # Create database indexes for optimization
    logger.info("Creating database indexes...")
    try:
        from orm_calculator.database.connection import get_db_session
        db_type = DatabaseType.SQLITE if os.getenv("ENVIRONMENT", "development") == "development" else DatabaseType.POSTGRESQL
        index_manager = get_index_manager(db_type)
        
        async with get_db_session().__anext__() as session:
            await index_manager.create_all_indexes(session)
            await index_manager.analyze_all_tables(session)
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Failed to create database indexes: {e}")
    
    logger.info("ORM Capital Calculator Engine startup completed")


async def shutdown():
    """Application shutdown tasks"""
    logger.info("Shutting down ORM Capital Calculator Engine...")
    
    # Stop performance monitoring
    logger.info("Stopping performance monitoring...")
    performance_monitor = get_performance_monitor()
    await performance_monitor.stop_monitoring()
    logger.info("Performance monitoring stopped")
    
    # Close cache connections
    logger.info("Closing cache connections...")
    await close_cache()
    logger.info("Cache connections closed")
    
    # Close database connections
    logger.info("Closing database connections...")
    await close_database()
    logger.info("Database connections closed")
    
    logger.info("ORM Capital Calculator Engine shutdown completed")


def main() -> None:
    """Main entry point for the application"""
    # Run the server with reload disabled for testing
    uvicorn.run(
        "orm_calculator.main:create_application",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )


def create_application():
    """Create application for uvicorn"""
    app = create_app()
    
    @app.on_event("startup")
    async def startup_event():
        await startup()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await shutdown()
    
    return app


if __name__ == "__main__":
    main()