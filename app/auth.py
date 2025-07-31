"""
Authentication module for IPFS Storage System.

Provides API key authentication for protected endpoints.
"""

import hashlib
import secrets

from app.config import get_settings
from app.logging_config import get_logger
from fastapi import Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

settings = get_settings()
logger = get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


class APIKeyAuth:
    """API Key authentication handler with proper typing."""

    def __init__(self) -> None:
        self.api_key: str = self._get_or_generate_api_key()
        logger.info("🔐 API key authentication initialized")

    def _get_or_generate_api_key(self) -> str:
        """Get API key from environment or generate a new one."""
        if settings.secret_key:
            # Use the secret key as base for API key
            return hashlib.sha256(
                f"ipfs_api_{settings.secret_key}".encode()
            ).hexdigest()[:32]
        else:
            # Generate a random API key
            api_key = secrets.token_urlsafe(32)
            logger.warning(
                "🔑 Generated random API key. Set SECRET_KEY in environment for persistent key."
            )
            logger.warning(f"🔑 Current API key: {api_key}")
            return api_key

    def verify_api_key(self, provided_key: str) -> bool:
        """Verify if the provided API key is valid."""
        return secrets.compare_digest(provided_key, self.api_key)

    def get_api_key(self) -> str:
        """Get the current API key."""
        return self.api_key


# Global auth instance
auth_handler = APIKeyAuth()


async def verify_api_key_header(x_api_key: str | None = Header(None)) -> str:
    """Dependency to verify API key from header."""
    if not x_api_key:
        logger.warning("🚫 API key missing in request header")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_handler.verify_api_key(x_api_key):
        logger.warning(f"🚫 Invalid API key attempted: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("✅ Valid API key authenticated")
    return x_api_key


async def verify_api_key_bearer(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    """Dependency to verify API key from Bearer token."""
    if not credentials:
        logger.warning("🚫 Bearer token missing in request")
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide as Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_handler.verify_api_key(credentials.credentials):
        logger.warning(
            f"🚫 Invalid bearer token attempted: {credentials.credentials[:8]}..."
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("✅ Valid bearer token authenticated")
    return credentials.credentials


async def verify_api_key_flexible(
    credentials: HTTPAuthorizationCredentials | None,
    x_api_key: str | None = Header(None),
) -> str:
    """Dependency that accepts API key from either header or bearer token."""

    # Try header first
    if x_api_key and auth_handler.verify_api_key(x_api_key):
        logger.debug("✅ Valid API key from header")
        return x_api_key

    # Try bearer token
    if credentials and auth_handler.verify_api_key(credentials.credentials):
        logger.debug("✅ Valid API key from bearer token")
        return credentials.credentials

    # Neither worked
    logger.warning("🚫 No valid API key provided in header or bearer token")
    raise HTTPException(
        status_code=401,
        detail="API key required. Provide X-API-Key header or Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_api_key() -> str:
    """Get the current API key for display purposes."""
    return auth_handler.get_api_key()


def generate_new_api_key() -> str:
    """Generate a new API key (for admin purposes)."""
    new_key = secrets.token_urlsafe(32)
    auth_handler.api_key = new_key
    logger.info("🔄 New API key generated")
    return new_key
