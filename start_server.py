#!/usr/bin/env python3
"""
Start the ORM Capital Calculator server
"""

import sys
import os
import uvicorn

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Start the server"""
    print("Starting ORM Capital Calculator Engine...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("Alternative Docs: http://127.0.0.1:8000/redoc")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "orm_calculator.main:create_application",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()