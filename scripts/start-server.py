#!/usr/bin/env python3
"""
Development server startup script
"""

import os
import sys
import uvicorn

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

if __name__ == "__main__":
    uvicorn.run(
        "orm_calculator.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=["src"]
    )