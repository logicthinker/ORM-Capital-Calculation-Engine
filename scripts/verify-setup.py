#!/usr/bin/env python3
"""
Setup verification script
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.9+")
        return False

def check_dependencies():
    """Check if key dependencies are installed"""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        import uvicorn
        import alembic
        import pytest
        print("✅ All key dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def check_project_structure():
    """Check project structure"""
    required_dirs = [
        "src/orm_calculator",
        "src/orm_calculator/api",
        "src/orm_calculator/database",
        "src/orm_calculator/models",
        "src/orm_calculator/services",
        "tests",
        "scripts",
        "migrations",
        "data",
        "docs"
    ]
    
    required_files = [
        "pyproject.toml",
        "README.md",
        "Makefile",
        ".gitignore",
        "src/orm_calculator/__init__.py",
        "src/orm_calculator/main.py",
        "src/orm_calculator/api/__init__.py",
        "src/orm_calculator/database/models.py",
        "src/orm_calculator/database/connection.py",
        "tests/conftest.py",
        "tests/test_api.py",
        "alembic.ini"
    ]
    
    missing_dirs = []
    missing_files = []
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if not missing_dirs and not missing_files:
        print("✅ Project structure complete")
        return True
    else:
        if missing_dirs:
            print(f"❌ Missing directories: {missing_dirs}")
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
        return False

def check_database():
    """Check database setup"""
    db_path = Path("data/orm_calculator.db")
    if not db_path.exists():
        print("❌ Database file not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'business_indicators',
            'loss_events',
            'recoveries',
            'capital_calculations',
            'jobs',
            'audit_trail',
            'alembic_version'
        ]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        
        conn.close()
        
        if not missing_tables:
            print("✅ Database schema complete")
            return True
        else:
            print(f"❌ Missing database tables: {missing_tables}")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def run_tests():
    """Run tests"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main verification function"""
    print("🔍 ORM Capital Calculator - Setup Verification")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("Database Setup", check_database),
        ("Tests", run_tests)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        result = check_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL CHECKS PASSED! Setup is complete.")
        print("\nNext steps:")
        print("1. Run: python scripts/start-server.py")
        print("2. Visit: http://127.0.0.1:8000/docs")
        print("3. Start implementing the next task!")
        return 0
    else:
        print(f"❌ {total - passed} checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)