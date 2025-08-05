"""
IPFS Storage System Application Package.

This package contains the main application components including:
- API routes and endpoints
- Services for IPFS and database operations
- Configuration and utilities
"""

# Import subpackages to make them available when importing the app package
from . import api, auth, config, database, logging_config, services

# Re-export commonly used components for easier imports
from .config import get_settings
from .logging_config import get_logger, init_logging
from .services.ipfs import IPFSService
from .database import DatabaseService

__all__ = [
    # Subpackages
    'api',
    'auth',
    'config',
    'database',
    'logging_config',
    'services',
    
    # Functions and classes
    'get_settings',
    'get_logger',
    'init_logging',
    'IPFSService',
    'DatabaseService',
]