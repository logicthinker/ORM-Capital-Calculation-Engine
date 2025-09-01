#!/usr/bin/env python3
"""
Initialize database with current schema

Creates the database tables based on the current SQLAlchemy models.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from orm_calculator.database.connection import init_database, close_database


async def main():
    """Initialize the database"""
    try:
        print("Initializing database...")
        await init_database()
        print("Database initialized successfully!")
        
        # Test database connection
        from orm_calculator.database.connection import db_manager
        health_check = await db_manager.health_check()
        if health_check:
            print("Database health check passed!")
        else:
            print("Database health check failed!")
            
    except Exception as e:
        print(f"Error initializing database: {e}")
        return 1
    finally:
        await close_database()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)