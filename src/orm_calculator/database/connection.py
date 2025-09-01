"""
Database connection management for ORM Capital Calculator Engine

Provides SQLAlchemy database connection with support for SQLite (development)
and PostgreSQL (production) with automatic configuration detection.
"""

import os
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from orm_calculator.models.orm_models import Base


class DatabaseConfig:
    """Database configuration management"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.database_url = self._get_database_url()
        self.echo_sql = os.getenv("DB_ECHO", "false").lower() == "true"
        
    def _get_database_url(self) -> str:
        """Get database URL based on environment"""
        if self.environment == "development":
            # SQLite for development
            db_path = os.getenv("SQLITE_DB_PATH", "./data/orm_calculator.db")
            # Ensure data directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"
        else:
            # PostgreSQL for production
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "orm_calculator")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "")
            
            return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database"""
        return self.database_url.startswith("sqlite")


class DatabaseManager:
    """Database connection manager with async support"""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.engine = None
        self.session_factory = None
        
    async def initialize(self) -> None:
        """Initialize database connection and create tables"""
        # Get database-specific optimization configuration
        from orm_calculator.core.database_optimization import (
            get_database_optimizer, DatabaseType, ConnectionPoolManager
        )
        
        db_type = DatabaseType.SQLITE if self.config.is_sqlite else DatabaseType.POSTGRESQL
        pool_manager = ConnectionPoolManager(db_type)
        pool_config = pool_manager.get_pool_config()
        
        # Create async engine with optimized configuration
        if self.config.is_sqlite:
            # SQLite specific configuration with optimizations
            self.engine = create_async_engine(
                self.config.database_url,
                echo=self.config.echo_sql,
                **pool_config
            )
            
            # Enable foreign key constraints and performance pragmas for SQLite
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                # Foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Performance optimizations
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
                cursor.close()
        else:
            # PostgreSQL configuration with optimized pool settings
            self.engine = create_async_engine(
                self.config.database_url,
                echo=self.config.echo_sql,
                **pool_config
            )
        
        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables if in development mode
        if self.config.environment == "development":
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status and health information"""
        if not self.engine:
            return {"status": "not_initialized"}
        
        try:
            pool = self.engine.pool
            
            pool_info = {
                "status": "healthy",
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "pool_class": pool.__class__.__name__
            }
            
            # Calculate utilization
            total_connections = pool.size() + pool.overflow()
            active_connections = pool.checkedout()
            pool_info["utilization_percent"] = (active_connections / total_connections * 100) if total_connections > 0 else 0
            
            # Add database-specific information
            if self.config.is_sqlite:
                pool_info["database_type"] = "SQLite"
                pool_info["database_path"] = self.config.database_url.split("///")[-1]
            else:
                pool_info["database_type"] = "PostgreSQL"
                pool_info["max_overflow"] = getattr(pool, 'max_overflow', 'N/A')
                pool_info["pool_timeout"] = getattr(pool, 'timeout', 'N/A')
            
            return pool_info
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "database_type": "SQLite" if self.config.is_sqlite else "PostgreSQL"
            }


# Global database manager instance
db_manager = DatabaseManager()


async def init_database() -> None:
    """Initialize database connection"""
    await db_manager.initialize()


async def close_database() -> None:
    """Close database connections"""
    await db_manager.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session in FastAPI"""
    async with db_manager.get_session() as session:
        yield session