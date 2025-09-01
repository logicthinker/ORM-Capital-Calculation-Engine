#!/usr/bin/env python3
"""
Database migration script supporting SQLite to PostgreSQL/MySQL/Oracle transitions
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

import asyncpg
import aiosqlite
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orm_calculator.database.models import Base
from orm_calculator.config import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Database migration utility supporting multiple database types"""
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine = None
        self.target_engine = None
        
    async def initialize_connections(self):
        """Initialize database connections"""
        logger.info(f"Connecting to source database: {self.source_url}")
        self.source_engine = create_async_engine(self.source_url)
        
        logger.info(f"Connecting to target database: {self.target_url}")
        self.target_engine = create_async_engine(self.target_url)
        
    async def close_connections(self):
        """Close database connections"""
        if self.source_engine:
            await self.source_engine.dispose()
        if self.target_engine:
            await self.target_engine.dispose()
    
    async def create_target_schema(self):
        """Create target database schema"""
        logger.info("Creating target database schema...")
        
        async with self.target_engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Target schema created successfully")
    
    async def get_table_list(self) -> List[str]:
        """Get list of tables to migrate"""
        async with self.source_engine.connect() as conn:
            # Get all table names from source database
            if "sqlite" in self.source_url:
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ))
            else:
                result = await conn.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                ))
            
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(tables)} tables to migrate: {tables}")
            return tables
    
    async def migrate_table_data(self, table_name: str, batch_size: int = 1000):
        """Migrate data for a specific table"""
        logger.info(f"Migrating table: {table_name}")
        
        # Get total row count
        async with self.source_engine.connect() as conn:
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total_rows = count_result.scalar()
            
        if total_rows == 0:
            logger.info(f"Table {table_name} is empty, skipping...")
            return
            
        logger.info(f"Migrating {total_rows} rows from {table_name}")
        
        # Migrate in batches
        offset = 0
        migrated_rows = 0
        
        while offset < total_rows:
            # Read batch from source
            async with self.source_engine.connect() as source_conn:
                query = text(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
                result = await source_conn.execute(query)
                rows = result.fetchall()
                columns = result.keys()
            
            if not rows:
                break
                
            # Convert to list of dictionaries
            batch_data = [dict(zip(columns, row)) for row in rows]
            
            # Insert batch into target
            await self.insert_batch_data(table_name, batch_data, columns)
            
            migrated_rows += len(batch_data)
            offset += batch_size
            
            logger.info(f"Migrated {migrated_rows}/{total_rows} rows from {table_name}")
        
        logger.info(f"Completed migration of table {table_name}")
    
    async def insert_batch_data(self, table_name: str, batch_data: List[Dict], columns: List[str]):
        """Insert batch data into target database"""
        if not batch_data:
            return
            
        # Build parameterized insert query
        placeholders = ", ".join([f":{col}" for col in columns])
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        async with self.target_engine.begin() as conn:
            await conn.execute(text(insert_query), batch_data)
    
    async def verify_migration(self) -> Dict[str, Dict[str, int]]:
        """Verify migration by comparing row counts"""
        logger.info("Verifying migration...")
        
        tables = await self.get_table_list()
        verification_results = {}
        
        for table_name in tables:
            # Get source count
            async with self.source_engine.connect() as conn:
                source_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                source_count = source_result.scalar()
            
            # Get target count
            async with self.target_engine.connect() as conn:
                target_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                target_count = target_result.scalar()
            
            verification_results[table_name] = {
                "source_count": source_count,
                "target_count": target_count,
                "match": source_count == target_count
            }
            
            if source_count == target_count:
                logger.info(f"✓ {table_name}: {source_count} rows migrated successfully")
            else:
                logger.error(f"✗ {table_name}: Source={source_count}, Target={target_count}")
        
        return verification_results
    
    async def create_indexes(self):
        """Create indexes on target database for performance"""
        logger.info("Creating indexes on target database...")
        
        index_queries = [
            # Business indicators indexes
            "CREATE INDEX IF NOT EXISTS idx_business_indicators_entity_date ON business_indicators(entity_id, calculation_date)",
            "CREATE INDEX IF NOT EXISTS idx_business_indicators_period ON business_indicators(period)",
            
            # Loss events indexes
            "CREATE INDEX IF NOT EXISTS idx_loss_events_entity_date ON loss_events(entity_id, accounting_date)",
            "CREATE INDEX IF NOT EXISTS idx_loss_events_occurrence ON loss_events(occurrence_date)",
            "CREATE INDEX IF NOT EXISTS idx_loss_events_discovery ON loss_events(discovery_date)",
            "CREATE INDEX IF NOT EXISTS idx_loss_events_amount ON loss_events(net_amount)",
            
            # Capital calculations indexes
            "CREATE INDEX IF NOT EXISTS idx_capital_calculations_run_id ON capital_calculations(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_capital_calculations_entity_date ON capital_calculations(entity_id, calculation_date)",
            "CREATE INDEX IF NOT EXISTS idx_capital_calculations_methodology ON capital_calculations(methodology)",
            
            # Jobs indexes
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_entity ON jobs(entity_id)",
            
            # Audit trail indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_trail_run_id ON audit_trail(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_trail_initiator ON audit_trail(initiator)",
            
            # Parameter versions indexes
            "CREATE INDEX IF NOT EXISTS idx_parameter_versions_model ON parameter_versions(model_name)",
            "CREATE INDEX IF NOT EXISTS idx_parameter_versions_effective ON parameter_versions(effective_date)",
        ]
        
        async with self.target_engine.begin() as conn:
            for query in index_queries:
                try:
                    await conn.execute(text(query))
                    logger.info(f"Created index: {query.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")
        
        logger.info("Index creation completed")
    
    async def migrate_all(self, batch_size: int = 1000) -> Dict[str, Any]:
        """Perform complete database migration"""
        start_time = datetime.utcnow()
        logger.info("Starting database migration...")
        
        try:
            # Initialize connections
            await self.initialize_connections()
            
            # Create target schema
            await self.create_target_schema()
            
            # Get tables to migrate
            tables = await self.get_table_list()
            
            # Migrate each table
            for table_name in tables:
                await self.migrate_table_data(table_name, batch_size)
            
            # Create indexes
            await self.create_indexes()
            
            # Verify migration
            verification_results = await self.verify_migration()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            # Generate migration report
            migration_report = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "source_database": self.source_url,
                "target_database": self.target_url,
                "tables_migrated": len(tables),
                "verification_results": verification_results,
                "success": all(result["match"] for result in verification_results.values())
            }
            
            logger.info(f"Migration completed in {duration:.2f} seconds")
            return migration_report
            
        finally:
            await self.close_connections()


def get_database_url(db_type: str, **kwargs) -> str:
    """Generate database URL based on type and parameters"""
    if db_type == "sqlite":
        return f"sqlite+aiosqlite:///{kwargs.get('path', './data/orm_calculator.db')}"
    elif db_type == "postgresql":
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 5432)
        database = kwargs.get('database', 'orm_calculator')
        username = kwargs.get('username', 'postgres')
        password = kwargs.get('password', 'password')
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "mysql":
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 3306)
        database = kwargs.get('database', 'orm_calculator')
        username = kwargs.get('username', 'root')
        password = kwargs.get('password', 'password')
        return f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "oracle":
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 1521)
        service_name = kwargs.get('service_name', 'ORCL')
        username = kwargs.get('username', 'orm_user')
        password = kwargs.get('password', 'password')
        return f"oracle+cx_oracle://{username}:{password}@{host}:{port}/?service_name={service_name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    parser.add_argument("--source-type", required=True, choices=["sqlite", "postgresql", "mysql", "oracle"],
                       help="Source database type")
    parser.add_argument("--target-type", required=True, choices=["postgresql", "mysql", "oracle"],
                       help="Target database type")
    parser.add_argument("--source-path", help="Source SQLite database path")
    parser.add_argument("--target-host", default="localhost", help="Target database host")
    parser.add_argument("--target-port", type=int, help="Target database port")
    parser.add_argument("--target-database", default="orm_calculator", help="Target database name")
    parser.add_argument("--target-username", help="Target database username")
    parser.add_argument("--target-password", help="Target database password")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for data migration")
    parser.add_argument("--report-file", help="Path to save migration report")
    
    args = parser.parse_args()
    
    # Build source URL
    if args.source_type == "sqlite":
        source_url = get_database_url("sqlite", path=args.source_path or "./data/orm_calculator.db")
    else:
        # For non-SQLite sources, you'd need to provide connection details
        raise NotImplementedError("Non-SQLite source databases not implemented in this example")
    
    # Build target URL
    target_params = {
        "host": args.target_host,
        "database": args.target_database,
        "username": args.target_username or os.getenv(f"{args.target_type.upper()}_USER"),
        "password": args.target_password or os.getenv(f"{args.target_type.upper()}_PASSWORD"),
    }
    
    if args.target_port:
        target_params["port"] = args.target_port
    
    target_url = get_database_url(args.target_type, **target_params)
    
    # Perform migration
    migrator = DatabaseMigrator(source_url, target_url)
    
    try:
        migration_report = await migrator.migrate_all(args.batch_size)
        
        # Save report if requested
        if args.report_file:
            with open(args.report_file, "w") as f:
                json.dump(migration_report, f, indent=2)
            logger.info(f"Migration report saved to: {args.report_file}")
        
        # Print summary
        if migration_report["success"]:
            logger.info("✓ Migration completed successfully!")
        else:
            logger.error("✗ Migration completed with errors. Check verification results.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())