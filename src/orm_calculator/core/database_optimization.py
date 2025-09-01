"""
Database optimization utilities for ORM Capital Calculator Engine

Provides database-specific optimizations, indexing strategies, connection pooling,
and query optimization for both SQLite (development) and PostgreSQL (production).
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import text, Index, Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.orm import Query

from orm_calculator.database.connection import DatabaseManager


class DatabaseType(str, Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    ORACLE = "oracle"
    MSSQL = "mssql"


class IndexType(str, Enum):
    """Database index types"""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    BRIN = "brin"
    COLUMNSTORE = "columnstore"


@dataclass
class IndexDefinition:
    """Database index definition"""
    name: str
    table: str
    columns: List[str]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    partial_condition: Optional[str] = None
    include_columns: Optional[List[str]] = None


@dataclass
class QueryOptimization:
    """Query optimization configuration"""
    use_index_hints: bool = False
    enable_parallel_query: bool = False
    max_parallel_workers: int = 4
    enable_partitioning: bool = False
    partition_column: Optional[str] = None


class DatabaseOptimizer(ABC):
    """Abstract database optimizer"""
    
    @abstractmethod
    async def create_indexes(self, session: AsyncSession, indexes: List[IndexDefinition]) -> None:
        """Create database indexes"""
        pass
    
    @abstractmethod
    async def analyze_tables(self, session: AsyncSession, tables: List[str]) -> None:
        """Update table statistics"""
        pass
    
    @abstractmethod
    async def optimize_query(self, query: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Optimize query for specific database"""
        pass
    
    @abstractmethod
    def get_connection_pool_config(self) -> Dict[str, Any]:
        """Get optimal connection pool configuration"""
        pass


class SQLiteOptimizer(DatabaseOptimizer):
    """SQLite-specific optimizations"""
    
    async def create_indexes(self, session: AsyncSession, indexes: List[IndexDefinition]) -> None:
        """Create SQLite indexes"""
        for index in indexes:
            columns_str = ", ".join(index.columns)
            unique_str = "UNIQUE " if index.unique else ""
            
            sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {index.name} ON {index.table} ({columns_str})"
            
            if index.partial_condition:
                sql += f" WHERE {index.partial_condition}"
            
            await session.execute(text(sql))
        
        await session.commit()
    
    async def analyze_tables(self, session: AsyncSession, tables: List[str]) -> None:
        """Update SQLite table statistics"""
        await session.execute(text("ANALYZE"))
        await session.commit()
    
    async def optimize_query(self, query: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Optimize query for SQLite"""
        # SQLite-specific optimizations
        optimized_query = query
        
        # Add query planner hints for complex queries
        if "JOIN" in query.upper() and "ORDER BY" in query.upper():
            # Suggest using covering indexes
            optimized_query = f"/* SQLite: Use covering indexes */ {query}"
        
        return optimized_query, params
    
    def get_connection_pool_config(self) -> Dict[str, Any]:
        """Get SQLite connection pool configuration"""
        return {
            "poolclass": StaticPool,
            "pool_pre_ping": False,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20,
                "isolation_level": None
            }
        }
    
    async def configure_sqlite_pragmas(self, session: AsyncSession) -> None:
        """Configure SQLite pragmas for performance"""
        pragmas = [
            "PRAGMA journal_mode = WAL",  # Write-Ahead Logging
            "PRAGMA synchronous = NORMAL",  # Balance safety and performance
            "PRAGMA cache_size = -64000",  # 64MB cache
            "PRAGMA temp_store = MEMORY",  # Store temp tables in memory
            "PRAGMA mmap_size = 268435456",  # 256MB memory-mapped I/O
            "PRAGMA optimize"  # Optimize query planner
        ]
        
        for pragma in pragmas:
            await session.execute(text(pragma))


class PostgreSQLOptimizer(DatabaseOptimizer):
    """PostgreSQL-specific optimizations"""
    
    async def create_indexes(self, session: AsyncSession, indexes: List[IndexDefinition]) -> None:
        """Create PostgreSQL indexes"""
        for index in indexes:
            columns_str = ", ".join(index.columns)
            unique_str = "UNIQUE " if index.unique else ""
            using_clause = f"USING {index.index_type.value}" if index.index_type != IndexType.BTREE else ""
            
            sql = f"CREATE {unique_str}INDEX CONCURRENTLY IF NOT EXISTS {index.name} ON {index.table} {using_clause} ({columns_str})"
            
            if index.include_columns:
                include_str = ", ".join(index.include_columns)
                sql += f" INCLUDE ({include_str})"
            
            if index.partial_condition:
                sql += f" WHERE {index.partial_condition}"
            
            await session.execute(text(sql))
        
        await session.commit()
    
    async def analyze_tables(self, session: AsyncSession, tables: List[str]) -> None:
        """Update PostgreSQL table statistics"""
        for table in tables:
            await session.execute(text(f"ANALYZE {table}"))
        await session.commit()
    
    async def optimize_query(self, query: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Optimize query for PostgreSQL"""
        optimized_query = query
        
        # Add PostgreSQL-specific optimizations
        if "ORDER BY" in query.upper() and "LIMIT" in query.upper():
            # Use index-only scans when possible
            optimized_query = f"/* PostgreSQL: Consider index-only scan */ {query}"
        
        # Enable parallel query for large datasets
        if "COUNT(*)" in query.upper() or "SUM(" in query.upper():
            optimized_query = f"SET max_parallel_workers_per_gather = 4; {query}"
        
        return optimized_query, params
    
    def get_connection_pool_config(self) -> Dict[str, Any]:
        """Get PostgreSQL connection pool configuration"""
        return {
            "poolclass": QueuePool,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "pool_timeout": 30
        }
    
    async def configure_postgresql_settings(self, session: AsyncSession) -> None:
        """Configure PostgreSQL session settings for performance"""
        settings = [
            "SET work_mem = '256MB'",
            "SET maintenance_work_mem = '512MB'",
            "SET effective_cache_size = '2GB'",
            "SET random_page_cost = 1.1",
            "SET enable_partitionwise_join = on",
            "SET enable_partitionwise_aggregate = on"
        ]
        
        for setting in settings:
            await session.execute(text(setting))


class QueryPaginator:
    """Utility for paginating large query results"""
    
    def __init__(self, page_size: int = 1000):
        self.page_size = page_size
    
    async def paginate_query(self, session: AsyncSession, base_query: str, 
                           params: Dict[str, Any], total_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Paginate a query and return all results"""
        results = []
        offset = 0
        
        # Get total count if not provided
        if total_count is None:
            count_query = f"SELECT COUNT(*) FROM ({base_query}) as count_subquery"
            count_result = await session.execute(text(count_query), params)
            total_count = count_result.scalar()
        
        # Paginate through results
        while offset < total_count:
            paginated_query = f"{base_query} LIMIT {self.page_size} OFFSET {offset}"
            result = await session.execute(text(paginated_query), params)
            page_results = [dict(row._mapping) for row in result]
            
            if not page_results:
                break
            
            results.extend(page_results)
            offset += self.page_size
        
        return results
    
    async def paginate_query_generator(self, session: AsyncSession, base_query: str, 
                                     params: Dict[str, Any]):
        """Generator for paginated query results"""
        offset = 0
        
        while True:
            paginated_query = f"{base_query} LIMIT {self.page_size} OFFSET {offset}"
            result = await session.execute(text(paginated_query), params)
            page_results = [dict(row._mapping) for row in result]
            
            if not page_results:
                break
            
            for row in page_results:
                yield row
            
            offset += self.page_size


class ConnectionPoolManager:
    """Advanced connection pool management"""
    
    def __init__(self, db_type: DatabaseType):
        self.db_type = db_type
        self.optimizer = self._get_optimizer()
    
    def _get_optimizer(self) -> DatabaseOptimizer:
        """Get database-specific optimizer"""
        if self.db_type == DatabaseType.SQLITE:
            return SQLiteOptimizer()
        elif self.db_type == DatabaseType.POSTGRESQL:
            return PostgreSQLOptimizer()
        else:
            # Default to PostgreSQL optimizer for other databases
            return PostgreSQLOptimizer()
    
    def get_pool_config(self) -> Dict[str, Any]:
        """Get optimized pool configuration"""
        base_config = self.optimizer.get_connection_pool_config()
        
        # Add monitoring and health check configuration
        base_config.update({
            "pool_reset_on_return": "commit",
            "pool_logging_name": "orm_calculator_pool"
        })
        
        return base_config
    
    async def health_check_pool(self, engine: AsyncEngine) -> Dict[str, Any]:
        """Check connection pool health"""
        pool = engine.pool
        
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }


class DatabaseIndexManager:
    """Manages database indexes for optimal performance"""
    
    def __init__(self, db_type: DatabaseType):
        self.db_type = db_type
        self.optimizer = self._get_optimizer()
    
    def _get_optimizer(self) -> DatabaseOptimizer:
        """Get database-specific optimizer"""
        if self.db_type == DatabaseType.SQLITE:
            return SQLiteOptimizer()
        elif self.db_type == DatabaseType.POSTGRESQL:
            return PostgreSQLOptimizer()
        else:
            return PostgreSQLOptimizer()
    
    def get_recommended_indexes(self) -> List[IndexDefinition]:
        """Get recommended indexes for ORM calculator tables"""
        indexes = [
            # Business indicators indexes
            IndexDefinition(
                name="idx_business_indicators_entity_date",
                table="business_indicators",
                columns=["entity_id", "calculation_date"],
                index_type=IndexType.BTREE
            ),
            IndexDefinition(
                name="idx_business_indicators_period",
                table="business_indicators",
                columns=["period"],
                index_type=IndexType.BTREE
            ),
            
            # Loss events indexes
            IndexDefinition(
                name="idx_loss_events_entity_dates",
                table="loss_events",
                columns=["entity_id", "accounting_date", "occurrence_date"],
                index_type=IndexType.BTREE
            ),
            IndexDefinition(
                name="idx_loss_events_amount",
                table="loss_events",
                columns=["gross_amount"],
                index_type=IndexType.BTREE,
                partial_condition="gross_amount >= 100000"  # Above threshold
            ),
            
            # Capital calculations indexes
            IndexDefinition(
                name="idx_capital_calculations_run_id",
                table="capital_calculations",
                columns=["run_id"],
                index_type=IndexType.BTREE,
                unique=True
            ),
            IndexDefinition(
                name="idx_capital_calculations_entity_date",
                table="capital_calculations",
                columns=["entity_id", "calculation_date"],
                index_type=IndexType.BTREE
            ),
            
            # Jobs indexes
            IndexDefinition(
                name="idx_jobs_status_created",
                table="jobs",
                columns=["status", "created_at"],
                index_type=IndexType.BTREE
            ),
            
            # Audit trail indexes
            IndexDefinition(
                name="idx_audit_trail_run_id",
                table="audit_trail",
                columns=["run_id"],
                index_type=IndexType.BTREE
            ),
            IndexDefinition(
                name="idx_audit_trail_timestamp",
                table="audit_trail",
                columns=["timestamp"],
                index_type=IndexType.BTREE
            )
        ]
        
        # Add PostgreSQL-specific indexes
        if self.db_type == DatabaseType.POSTGRESQL:
            indexes.extend([
                # GIN indexes for JSON columns
                IndexDefinition(
                    name="idx_parameters_config_gin",
                    table="parameters",
                    columns=["config"],
                    index_type=IndexType.GIN
                ),
                # Partial indexes for active records
                IndexDefinition(
                    name="idx_jobs_active",
                    table="jobs",
                    columns=["id", "status"],
                    index_type=IndexType.BTREE,
                    partial_condition="status IN ('queued', 'running')"
                )
            ])
        
        return indexes
    
    async def create_all_indexes(self, session: AsyncSession) -> None:
        """Create all recommended indexes"""
        indexes = self.get_recommended_indexes()
        await self.optimizer.create_indexes(session, indexes)
    
    async def analyze_all_tables(self, session: AsyncSession) -> None:
        """Analyze all tables to update statistics"""
        tables = [
            "business_indicators",
            "loss_events",
            "capital_calculations",
            "jobs",
            "audit_trail",
            "parameters",
            "recoveries"
        ]
        await self.optimizer.analyze_tables(session, tables)


class ConcurrentQueryExecutor:
    """Executes independent queries concurrently"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_concurrent_queries(self, session: AsyncSession, 
                                       queries: List[Tuple[str, Dict[str, Any]]]) -> List[Any]:
        """Execute multiple queries concurrently"""
        async def execute_single_query(query_params):
            query, params = query_params
            async with self.semaphore:
                result = await session.execute(text(query), params)
                return result.fetchall()
        
        tasks = [execute_single_query(qp) for qp in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def execute_concurrent_calculations(self, calculations: List[callable]) -> List[Any]:
        """Execute multiple calculations concurrently"""
        async def execute_single_calculation(calc_func):
            async with self.semaphore:
                if asyncio.iscoroutinefunction(calc_func):
                    return await calc_func()
                else:
                    return calc_func()
        
        tasks = [execute_single_calculation(calc) for calc in calculations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


# Global instances
_db_optimizer: Optional[DatabaseOptimizer] = None
_index_manager: Optional[DatabaseIndexManager] = None
_query_executor: Optional[ConcurrentQueryExecutor] = None


def get_database_optimizer(db_type: DatabaseType) -> DatabaseOptimizer:
    """Get database optimizer instance"""
    global _db_optimizer
    if _db_optimizer is None:
        if db_type == DatabaseType.SQLITE:
            _db_optimizer = SQLiteOptimizer()
        elif db_type == DatabaseType.POSTGRESQL:
            _db_optimizer = PostgreSQLOptimizer()
        else:
            _db_optimizer = PostgreSQLOptimizer()
    return _db_optimizer


def get_index_manager(db_type: DatabaseType) -> DatabaseIndexManager:
    """Get database index manager instance"""
    global _index_manager
    if _index_manager is None:
        _index_manager = DatabaseIndexManager(db_type)
    return _index_manager


def get_query_executor(max_concurrent: int = 10) -> ConcurrentQueryExecutor:
    """Get concurrent query executor instance"""
    global _query_executor
    if _query_executor is None:
        _query_executor = ConcurrentQueryExecutor(max_concurrent)
    return _query_executor