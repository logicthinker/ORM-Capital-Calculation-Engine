#!/usr/bin/env python3
"""
Script to create parameter governance tables

This script creates the parameter governance tables directly in the database
to support the parameter management workflow implementation.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from orm_calculator.database.connection import db_manager


async def create_parameter_tables():
    """Create parameter governance tables"""
    
    await db_manager.initialize()
    engine = db_manager.engine
    
    # SQL to create parameter_versions table
    create_parameter_versions_sql = """
    CREATE TABLE IF NOT EXISTS parameter_versions (
        id TEXT PRIMARY KEY,
        version_id TEXT NOT NULL UNIQUE,
        model_name TEXT NOT NULL,
        parameter_name TEXT NOT NULL,
        parameter_type TEXT NOT NULL CHECK (parameter_type IN ('COEFFICIENT', 'THRESHOLD', 'MULTIPLIER', 'FLAG', 'MAPPING', 'FORMULA')),
        parameter_category TEXT NOT NULL,
        parameter_value TEXT NOT NULL,  -- JSON as TEXT for SQLite
        previous_value TEXT,            -- JSON as TEXT for SQLite
        version_number INTEGER NOT NULL DEFAULT 1,
        parent_version_id TEXT,
        status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING_REVIEW', 'REVIEWED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'ACTIVE', 'SUPERSEDED')),
        effective_date DATE NOT NULL,
        expiry_date DATE,
        created_by TEXT NOT NULL,
        reviewed_by TEXT,
        approved_by TEXT,
        change_reason TEXT NOT NULL,
        business_justification TEXT NOT NULL,
        impact_assessment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        reviewed_at DATETIME,
        approved_at DATETIME,
        activated_at DATETIME,
        immutable_diff TEXT,
        requires_rbi_approval BOOLEAN DEFAULT FALSE,
        rbi_approval_reference TEXT,
        disclosure_required BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (parent_version_id) REFERENCES parameter_versions(version_id)
    );
    """
    
    # SQL to create parameter_workflow table
    create_parameter_workflow_sql = """
    CREATE TABLE IF NOT EXISTS parameter_workflow (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        parameter_version_id TEXT NOT NULL,
        step_name TEXT NOT NULL,
        step_status TEXT NOT NULL,
        actor TEXT NOT NULL,
        actor_role TEXT NOT NULL,
        action TEXT NOT NULL,
        comments TEXT,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        completed_at DATETIME,
        due_date DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parameter_version_id) REFERENCES parameter_versions(version_id)
    );
    """
    
    # SQL to create parameter_configuration table
    create_parameter_configuration_sql = """
    CREATE TABLE IF NOT EXISTS parameter_configuration (
        id TEXT PRIMARY KEY,
        model_name TEXT NOT NULL,
        active_version_id TEXT NOT NULL,
        configuration_name TEXT NOT NULL,
        description TEXT,
        activated_by TEXT NOT NULL,
        activated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        next_version_id TEXT,
        next_activation_date DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (active_version_id) REFERENCES parameter_versions(version_id),
        FOREIGN KEY (next_version_id) REFERENCES parameter_versions(version_id)
    );
    """
    
    # SQL to create indexes
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_param_model_name ON parameter_versions(model_name, parameter_name);",
        "CREATE INDEX IF NOT EXISTS idx_param_status ON parameter_versions(status);",
        "CREATE INDEX IF NOT EXISTS idx_param_effective ON parameter_versions(effective_date);",
        "CREATE INDEX IF NOT EXISTS idx_param_version ON parameter_versions(version_number);",
        "CREATE INDEX IF NOT EXISTS idx_workflow_id ON parameter_workflow(workflow_id);",
        "CREATE INDEX IF NOT EXISTS idx_workflow_status ON parameter_workflow(step_status);",
        "CREATE INDEX IF NOT EXISTS idx_workflow_actor ON parameter_workflow(actor);",
        "CREATE INDEX IF NOT EXISTS idx_config_model ON parameter_configuration(model_name);",
        "CREATE INDEX IF NOT EXISTS idx_config_active ON parameter_configuration(active_version_id);"
    ]
    
    try:
        async with engine.begin() as conn:
            print("Creating parameter_versions table...")
            await conn.execute(text(create_parameter_versions_sql))
            
            print("Creating parameter_workflow table...")
            await conn.execute(text(create_parameter_workflow_sql))
            
            print("Creating parameter_configuration table...")
            await conn.execute(text(create_parameter_configuration_sql))
            
            print("Creating indexes...")
            for index_sql in create_indexes_sql:
                await conn.execute(text(index_sql))
            
            print("✅ Parameter governance tables created successfully!")
            
    except Exception as e:
        print(f"❌ Error creating parameter tables: {e}")
        raise
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_parameter_tables())