"""
Logging configuration for IPFS Storage System.

Provides structured logging with rolling file logs and configurable levels.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import get_settings

settings = get_settings()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class IPFSLogger:
    """Centralized logging configuration for IPFS Storage System."""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging with both file and console handlers."""
        
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Rolling file handler for all logs
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "ipfs_storage.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Error-only file handler
        error_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # Access log handler for API requests
        access_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "access.log",
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=10,
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_formatter = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        access_handler.setFormatter(access_formatter)
        
        # Create access logger
        access_logger = logging.getLogger('access')
        access_logger.setLevel(logging.INFO)
        access_logger.addHandler(access_handler)
        access_logger.propagate = False
        
        # Suppress some noisy loggers
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("🔧 Logging system initialized")
        logger.info(f"📁 Log directory: {self.log_dir.absolute()}")
        logger.info(f"🐛 Debug mode: {settings.debug}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)


def log_api_access(method: str, path: str, status_code: int, 
                   response_time: float, client_ip: str, user_agent: Optional[str] = None):
    """Log API access information."""
    access_logger = logging.getLogger('access')
    access_logger.info(
        f"{client_ip} | {method} {path} | {status_code} | {response_time:.3f}s | {user_agent or 'Unknown'}"
    )


def log_file_operation(operation: str, cid: str, filename: str, 
                      size: Optional[int] = None, client_ip: Optional[str] = None):
    """Log file operations for audit trail."""
    logger = logging.getLogger('file_operations')
    size_str = f" | {size} bytes" if size else ""
    ip_str = f" | {client_ip}" if client_ip else ""
    logger.info(f"{operation} | {cid} | {filename}{size_str}{ip_str}")


def log_ipfs_operation(operation: str, cid: str, success: bool, 
                      error: Optional[str] = None, duration: Optional[float] = None):
    """Log IPFS operations for monitoring."""
    logger = logging.getLogger('ipfs_operations')
    status = "SUCCESS" if success else "FAILED"
    duration_str = f" | {duration:.3f}s" if duration else ""
    error_str = f" | Error: {error}" if error else ""
    logger.info(f"{operation} | {cid} | {status}{duration_str}{error_str}")


def log_system_event(event: str, details: Optional[str] = None, level: str = "INFO"):
    """Log system events."""
    logger = logging.getLogger('system')
    log_func = getattr(logger, level.lower(), logger.info)
    message = f"{event}"
    if details:
        message += f" | {details}"
    log_func(message)


# Initialize logging on import
_logger_instance = None

def init_logging():
    """Initialize the logging system."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = IPFSLogger()
    return _logger_instance


def get_log_files() -> dict:
    """Get information about available log files."""
    log_dir = Path("logs")
    if not log_dir.exists():
        return {}
    
    log_files = {}
    for log_file in log_dir.glob("*.log*"):
        try:
            stat = log_file.stat()
            log_files[log_file.name] = {
                'path': str(log_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'readable': log_file.is_file() and os.access(log_file, os.R_OK)
            }
        except Exception as e:
            log_files[log_file.name] = {
                'path': str(log_file),
                'error': str(e),
                'readable': False
            }
    
    return log_files


def read_log_file(filename: str, lines: int = 100, tail: bool = True) -> list:
    """Read lines from a log file."""
    log_dir = Path("logs")
    log_file = log_dir / filename
    
    if not log_file.exists() or not log_file.is_file():
        raise FileNotFoundError(f"Log file {filename} not found")
    
    if not os.access(log_file, os.R_OK):
        raise PermissionError(f"Cannot read log file {filename}")
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            if tail:
                # Read from the end of the file
                file_lines = f.readlines()
                return file_lines[-lines:] if len(file_lines) > lines else file_lines
            else:
                # Read from the beginning
                result = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    result.append(line)
                return result
    except Exception as e:
        raise RuntimeError(f"Error reading log file {filename}: {str(e)}")


# Auto-initialize logging
init_logging()
