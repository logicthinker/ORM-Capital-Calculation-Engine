#!/usr/bin/env python3
"""
Test runner script
"""

import os
import sys
import subprocess

def run_tests():
    """Run all tests with coverage"""
    # Change to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=src/orm_calculator",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-v"
    ]
    
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)