"""
Admin API endpoints for IPFS Storage System.

Provides health checks, system monitoring, and secure log access.
"""

import os
import time
from datetime import datetime
from typing import Any

import psutil
from app.auth import get_current_api_key, verify_api_key_flexible
from app.config import get_settings
from app.database import DatabaseService
from app.logging_config import (
    get_log_files,
    get_logger,
    log_system_event,
    read_log_file,
)
from app.services.ipfs import IPFSService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="System uptime in seconds")

    # Component status
    database: dict[str, Any] = Field(..., description="Database health status")
    ipfs: dict[str, Any] = Field(..., description="IPFS node health status")
    storage: dict[str, Any] = Field(..., description="Storage health status")

    # System metrics
    system: dict[str, Any] = Field(..., description="System resource metrics")


class LogFileInfo(BaseModel):
    """Log file information model."""

    name: str = Field(..., description="Log file name")
    size: int = Field(..., description="File size in bytes")
    modified: str = Field(..., description="Last modified timestamp")
    readable: bool = Field(..., description="Whether file is readable")


class LogResponse(BaseModel):
    """Log content response model."""

    filename: str = Field(..., description="Log file name")
    lines: list[str] = Field(..., description="Log lines")
    total_lines: int = Field(..., description="Total lines returned")
    timestamp: datetime = Field(..., description="Response timestamp")


class SystemInfo(BaseModel):
    """System information model."""

    api_key: str = Field(..., description="Current API key")
    config: dict[str, Any] = Field(..., description="Current configuration")
    log_files: dict[str, LogFileInfo] = Field(..., description="Available log files")


# Track application start time
_start_time = time.time()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks database, IPFS, storage, and system resources.
    """
    start_time = time.time()
    logger.debug("🏥 Starting health check")

    try:
        # Database health
        db_service = DatabaseService()
        db_status = {"status": "unknown", "error": None}
        try:
            file_count = db_service.get_file_count()
            db_status = {
                "status": "healthy",
                "file_count": file_count,
                "connection": "ok",
            }
        except Exception as e:
            db_status = {"status": "unhealthy", "error": str(e), "connection": "failed"}

        # IPFS health
        ipfs_service = IPFSService()
        ipfs_status = {"status": "unknown", "error": None}
        try:
            node_info = await ipfs_service.get_node_info()
            ipfs_status = {
                "status": "healthy",
                "node_id": node_info.get("ID", "unknown"),
                "version": node_info.get("Version", "unknown"),
                "connection": "ok",
            }
        except Exception as e:
            ipfs_status = {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed",
            }

        # Storage health
        storage_status = {"status": "unknown", "error": None}
        try:
            # Check database file
            db_path = settings.database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = db_path[2:]

            storage_info = {
                "status": "healthy",
                "database_exists": os.path.exists(db_path),
                "database_size": (
                    os.path.getsize(db_path) if os.path.exists(db_path) else 0
                ),
                "logs_directory": os.path.exists("logs"),
                "disk_usage": {},
            }

            # Disk usage
            disk_usage = psutil.disk_usage(".")
            storage_info["disk_usage"] = {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": (disk_usage.used / disk_usage.total) * 100,
            }

            storage_status = storage_info

        except Exception as e:
            storage_status = {"status": "unhealthy", "error": str(e)}

        # System metrics
        system_status = {"status": "unknown", "error": None}
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            system_status = {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
                "process_count": len(psutil.pids()),
            }
        except Exception as e:
            system_status = {"status": "unhealthy", "error": str(e)}

        # Overall status
        component_statuses = [
            db_status.get("status", "unknown"),
            ipfs_status.get("status", "unknown"),
            storage_status.get("status", "unknown"),
            system_status.get("status", "unknown"),
        ]

        if all(status == "healthy" for status in component_statuses):
            overall_status = "healthy"
        elif any(status == "unhealthy" for status in component_statuses):
            overall_status = "degraded"
        else:
            overall_status = "unknown"

        uptime = time.time() - _start_time

        health_response = HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.version,
            uptime_seconds=uptime,
            database=db_status,
            ipfs=ipfs_status,
            storage=storage_status,
            system=system_status,
        )

        check_duration = time.time() - start_time
        logger.info(
            f"🏥 Health check completed: {overall_status} ({check_duration:.3f}s)"
        )

        return health_response

    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        msg = f"Health check failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/health/simple")
async def simple_health_check():
    """
    Simple health check for load balancers.

    Returns 200 OK if system is operational.
    """
    try:
        # Quick database check
        db_service = DatabaseService()
        db_service.get_file_count()

        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.warning(f"⚠️ Simple health check failed: {str(e)}")
        msg = "Service unavailable"
        raise HTTPException(status_code=503, detail=msg) from e


@router.get("/logs", response_model=dict[str, LogFileInfo])
async def list_log_files(api_key: str = Depends(verify_api_key_flexible)):
    """
    List available log files.

    Requires API key authentication.
    """
    logger.info("📋 Listing log files")
    log_system_event("LOG_FILES_LISTED", "Admin accessed log files list")

    try:
        log_files = get_log_files()
        return {
            name: LogFileInfo(**info)
            for name, info in log_files.items()
            if info.get("readable", False)
        }
    except Exception as e:
        logger.error(f"❌ Failed to list log files: {str(e)}")
        msg = f"Failed to list log files: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/logs/{filename}", response_model=LogResponse)
async def get_log_content(
    filename: str,
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to return"),
    tail: bool = Query(True, description="Read from end of file (tail) or beginning"),
    api_key: str = Depends(verify_api_key_flexible),
):
    """
    Get content from a specific log file.

    Requires API key authentication.
    """
    logger.info(f"📖 Reading log file: {filename} ({lines} lines, tail={tail})")
    log_system_event("LOG_FILE_ACCESSED", f"Admin accessed {filename} ({lines} lines)")

    try:
        log_lines = read_log_file(filename, lines=lines, tail=tail)

        return LogResponse(
            filename=filename,
            lines=[line.rstrip("\n\r") for line in log_lines],
            total_lines=len(log_lines),
            timestamp=datetime.utcnow(),
        )

    except FileNotFoundError as e:
        logger.warning(f"📁 Log file not found: {filename}")
        msg = f"Log file '{filename}' not found"
        raise HTTPException(status_code=404, detail=msg) from e
    except PermissionError as e:
        logger.error(f"🚫 Permission denied reading log file: {filename}")
        msg = f"Permission denied reading '{filename}'"
        raise HTTPException(status_code=403, detail=msg) from e
    except Exception as e:
        logger.error(f"❌ Failed to read log file {filename}: {str(e)}")
        msg = f"Failed to read log file: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/system/info", response_model=SystemInfo)
async def get_system_info(api_key: str = Depends(verify_api_key_flexible)):
    """
    Get system information including configuration and log files.

    Requires API key authentication.
    """
    logger.info("ℹ️ Getting system information")
    log_system_event("SYSTEM_INFO_ACCESSED", "Admin accessed system information")

    try:
        # Get log files
        log_files = get_log_files()
        log_files_info = {
            name: LogFileInfo(**info)
            for name, info in log_files.items()
            if info.get("readable", False)
        }

        # Get configuration (sanitized)
        config_info = {
            "host": settings.host,
            "port": settings.port,
            "debug": settings.debug,
            "ipfs_api_url": settings.ipfs_api_url,
            "ipfs_gateway_url": settings.ipfs_gateway_url,
            "database_url": settings.database_url,
            "max_file_size": settings.max_file_size,
            "allowed_extensions": settings.allowed_extensions_list,
            "app_name": settings.app_name,
            "version": settings.version,
        }

        return SystemInfo(
            api_key=get_current_api_key(), config=config_info, log_files=log_files_info
        )

    except Exception as e:
        logger.error(f"❌ Failed to get system info: {str(e)}")
        msg = f"Failed to get system info: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


def _clear_log_file(file_path: str) -> bool:
    """Clear a single log file and return True if successful."""
    if os.path.exists(file_path):
        open(file_path, "w").close()
        return True
    return False


def _clear_all_logs(logs_dir: str) -> list[str]:
    """Clear all .log files in the directory and return list of cleared files."""
    files_cleared = []
    for log_file in os.listdir(logs_dir):
        if log_file.endswith(".log"):
            file_path = os.path.join(logs_dir, log_file)
            if _clear_log_file(file_path):
                files_cleared.append(log_file)
    return files_cleared


def _clear_specific_log(logs_dir: str, log_file: str) -> list[str]:
    """Clear a specific log file and return list containing the file if cleared."""
    file_path = os.path.join(logs_dir, log_file)
    return [log_file] if _clear_log_file(file_path) else []


@router.post("/system/clear-logs")
async def clear_logs(
    log_type: str = Query(
        ..., regex="^(all|access|errors|main)$", description="Type of logs to clear"
    ),
    api_key: str = Depends(verify_api_key_flexible),
):
    """
    Clear log files (admin operation).

    Requires API key authentication.
    """
    logger.warning(f"🗑️ Clearing logs: {log_type}")
    log_system_event("LOGS_CLEARED", f"Admin cleared {log_type} logs", "WARNING")

    try:
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            raise HTTPException(status_code=404, detail="Logs directory not found")

        log_files = {
            "access": "access.log",
            "errors": "errors.log",
            "main": "ipfs_storage.log",
        }

        files_cleared = (
            _clear_all_logs(logs_dir)
            if log_type == "all"
            else _clear_specific_log(logs_dir, log_files[log_type])
        )

        return {
            "message": f"Cleared {log_type} logs",
            "files_cleared": files_cleared,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to clear logs: {str(e)}")
        msg = f"Failed to clear logs: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/metrics")
async def get_metrics(api_key: str = Depends(verify_api_key_flexible)):
    """
    Get system metrics in Prometheus format.

    Requires API key authentication.
    """
    logger.debug("📊 Getting system metrics")

    try:
        # Database metrics
        db_service = DatabaseService()
        file_count = db_service.get_file_count()

        # System metrics
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk_usage = psutil.disk_usage(".")

        # IPFS metrics
        ipfs_connected = False
        try:
            ipfs_service = IPFSService()
            await ipfs_service.get_node_info()
            ipfs_connected = True
        except Exception as e:
            logger.warning(f"Failed to connect to IPFS: {str(e)}")
            pass

        uptime = time.time() - _start_time

        metrics = {
            "ipfs_storage_files_total": file_count,
            "ipfs_storage_uptime_seconds": uptime,
            "ipfs_storage_memory_usage_bytes": memory.used,
            "ipfs_storage_memory_usage_percent": memory.percent,
            "ipfs_storage_cpu_usage_percent": cpu_percent,
            "ipfs_storage_disk_usage_bytes": disk_usage.used,
            "ipfs_storage_disk_usage_percent": (disk_usage.used / disk_usage.total)
            * 100,
            "ipfs_storage_ipfs_connected": 1 if ipfs_connected else 0,
            "ipfs_storage_health_status": 1,  # 1 for healthy, 0 for unhealthy
        }

        return metrics

    except Exception as e:
        logger.error(f"❌ Failed to get metrics: {str(e)}")
        msg = f"Failed to get metrics: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e
