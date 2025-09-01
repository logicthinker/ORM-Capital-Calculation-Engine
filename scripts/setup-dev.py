#!/usr/bin/env python3
"""
Development environment setup script
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_development():
    """Set up development environment"""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 Setting up ORM Capital Calculator development environment...")
    
    # Create data directory if it doesn't exist
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Created data directory: {data_dir}")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-e", ".[dev]"
    ])
    
    if result.returncode != 0:
        print("❌ Failed to install dependencies")
        return result.returncode
    
    # Run database migrations
    print("🗄️ Setting up database...")
    migration_result = subprocess.run([
        sys.executable, "-m", "alembic", "upgrade", "head"
    ])
    
    if migration_result.returncode != 0:
        print("❌ Failed to run database migrations")
        return migration_result.returncode
    
    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    if not env_file.exists():
        env_example = project_root / ".env.example"
        if env_example.exists():
            env_file.write_text(env_example.read_text())
            print(f"✅ Created .env file from .env.example")
    
    print("🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("1. Activate your virtual environment")
    print("2. Run: python scripts/start-server.py")
    print("3. Visit: http://127.0.0.1:8000/docs")
    
    return 0

if __name__ == "__main__":
    exit_code = setup_development()
    sys.exit(exit_code)