#!/usr/bin/env python3
"""
IPFS Storage System - Main Application

A distributed file storage system built on IPFS with FastAPI backend
and web interface for seamless file management.
"""

import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.admin import router as admin_router
from app.api.files import router as files_router
from app.auth import get_current_api_key
from app.config import get_settings
from app.database import init_db
from app.logging_config import (
    get_logger,
    init_logging,
    log_api_access,
    log_system_event,
)
from app.services.ipfs import IPFSService

# Initialize logging first
init_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting IPFS Storage System...")
    log_system_event("SYSTEM_STARTUP", "Application starting")

    # Initialize database
    await init_db()
    logger.info("📊 Database initialized")

    # Verify IPFS connection
    try:
        from app.services.ipfs import IPFSService

        ipfs_service = IPFSService()
        node_info = await ipfs_service.get_node_info()
        logger.info(f"🌐 Connected to IPFS node: {node_info.get('ID', 'Unknown')}")
        log_system_event("IPFS_CONNECTED", f"Node ID: {node_info.get('ID', 'Unknown')}")
    except Exception as e:
        logger.warning(f"⚠️  IPFS connection warning: {e}")
        logger.warning("   Make sure IPFS daemon is running: 'ipfs daemon'")
        log_system_event("IPFS_CONNECTION_FAILED", str(e), "WARNING")

    # Display API key for admin access
    api_key = get_current_api_key()
    logger.info(f"🔑 Admin API Key: {api_key}")
    logger.info("📋 Admin endpoints available at /admin/")

    yield

    # Shutdown
    logger.info("🛑 Shutting down IPFS Storage System...")
    log_system_event("SYSTEM_SHUTDOWN", "Application shutting down")


# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title="IPFS Storage System",
    description="Distributed file storage system built on IPFS with web interface",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API access logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Process request
    response = await call_next(request)

    # Log the request
    process_time = time.time() - start_time
    log_api_access(
        method=request.method,
        path=str(request.url.path),
        status_code=response.status_code,
        response_time=process_time,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    # Add response headers
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Mount static files
static_path = Path(__file__).parent / "app" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(static_path))

# Include API routers
app.include_router(files_router, prefix="/api", tags=["files"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "IPFS Storage System", "version": "0.1.0"}


@app.get("/info")
async def system_info(ipfs_service: IPFSService):
    """Get system information."""
    try:
        node_info = await ipfs_service.get_node_info()

        return {
            "system": "IPFS Storage System",
            "version": "0.1.0",
            "ipfs_node": node_info.get("ID", "Unknown"),
            "ipfs_version": node_info.get("Version", "Unknown"),
            "database": "SQLite",
            "status": "operational",
        }
    except Exception as e:
        return {
            "system": "IPFS Storage System",
            "version": "0.1.0",
            "error": str(e),
            "status": "degraded",
        }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
