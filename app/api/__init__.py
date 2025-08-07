"""
API package for the IPFS Storage System.

This package contains all the API routes and endpoints for the application.
"""

from .files import router as files_router
from .admin import router as admin_router
from .modules import router as modules_router

__all__ = ["files_router", "admin_router", "modules_router"]
