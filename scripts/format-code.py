#!/usr/bin/env python3
"""
Code formatting script
"""

import os
import sys
import subprocess

def format_code():
    """Format code using black and ruff"""
    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    print("Running black...")
    black_result = subprocess.run([
        sys.executable, "-m", "black", 
        "src/", "tests/", "scripts/"
    ])
    
    print("Running ruff...")
    ruff_result = subprocess.run([
        sys.executable, "-m", "ruff", 
        "check", "--fix", "src/", "tests/", "scripts/"
    ])
    
    print("Running mypy...")
    mypy_result = subprocess.run([
        sys.executable, "-m", "mypy", 
        "src/orm_calculator"
    ])
    
    return max(black_result.returncode, ruff_result.returncode, mypy_result.returncode)

if __name__ == "__main__":
    exit_code = format_code()
    if exit_code == 0:
        print("✅ Code formatting completed successfully!")
    else:
        print("❌ Code formatting failed!")
    sys.exit(exit_code)