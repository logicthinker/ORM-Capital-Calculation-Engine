"""
Database tests
"""

import pytest
from sqlalchemy import text
from orm_calculator.database.connection import get_db, create_tables


@pytest.mark.asyncio
async def test_database_tables_exist():
    """Test that database tables are created correctly"""
    # Create tables
    await create_tables()
    
    # Get database session
    async for db in get_db():
        # Check if tables exist by querying sqlite_master
        result = await db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result.fetchall()]
        
        # Verify core tables exist
        expected_tables = [
            'business_indicators',
            'loss_events',
            'recoveries',
            'capital_calculations',
            'jobs',
            'audit_trail'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
        
        break  # Only need to test with first session