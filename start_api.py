#!/usr/bin/env python3
"""
Startup script for FastAPI application on Railway.
Handles PORT environment variable correctly.
"""
import os
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable, default to 8000 if not set
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # Start the FastAPI application
    uvicorn.run(
        "app.api.main:app",
        host=host,
        port=port,
        log_level="info"
    )
