#!/usr/bin/env python3
"""
IPFS Storage System - Main Application

A distributed file storage system built on IPFS with FastAPI backend
and web interface for seamless file management.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn

from app.config import get_settings
from app.database import init_db
from app.api.files import router as files_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print("🚀 Starting IPFS Storage System...")
    
    # Initialize database
    await init_db()
    print("📊 Database initialized")
    
    # Verify IPFS connection
    try:
        from app.services.ipfs import IPFSService
        ipfs_service = IPFSService()
        node_info = await ipfs_service.get_node_info()
        print(f"🌐 Connected to IPFS node: {node_info.get('ID', 'Unknown')}")
    except Exception as e:
        print(f"⚠️  IPFS connection warning: {e}")
        print("   Make sure IPFS daemon is running: 'ipfs daemon'")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down IPFS Storage System...")


# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title="IPFS Storage System",
    description="Distributed file storage system built on IPFS with web interface",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
static_path = Path(__file__).parent / "app" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(static_path))

# Include API routers
app.include_router(files_router, prefix="/api", tags=["files"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "IPFS Storage System",
        "version": "0.1.0"
    }


@app.get("/info")
async def system_info():
    """Get system information."""
    try:
        from app.services.ipfs import IPFSService
        ipfs_service = IPFSService()
        node_info = await ipfs_service.get_node_info()
        
        return {
            "system": "IPFS Storage System",
            "version": "0.1.0",
            "ipfs_node": node_info.get('ID', 'Unknown'),
            "ipfs_version": node_info.get('Version', 'Unknown'),
            "database": "SQLite",
            "status": "operational"
        }
    except Exception as e:
        return {
            "system": "IPFS Storage System",
            "version": "0.1.0",
            "error": str(e),
            "status": "degraded"
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
