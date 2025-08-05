"""
Configuration management for IPFS Storage System.

Handles environment variables and application settings.
"""

import os
from functools import lru_cache

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Server Configuration
    host: str = Field(default_factory=lambda: os.getenv('COMMUNE_IPFS_HOST', 'localhost'))
    port: int = Field(default_factory=lambda: int(os.getenv('COMMUNE_IPFS_PORT', '8000')))
    debug: bool = Field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')

    # IPFS Configuration
    ipfs_api_url: str = Field(default_factory=lambda: os.getenv('IPFS_API_URL', 'http://localhost:5001'))
    ipfs_gateway_url: str = Field(default_factory=lambda: os.getenv('IPFS_GATEWAY_URL', 'http://localhost:8080'))
    ipfs_timeout: int = Field(default=30)

    # Database Configuration
    database_url: str = Field(default="sqlite:///./files.db")

    # Security Configuration (Optional)
    secret_key: str | None = Field(default=None)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    # File Upload Configuration
    max_file_size: int = Field(default=100 * 1024 * 1024)  # 100MB
    allowed_extensions: str = Field(
        default="txt,pdf,png,jpg,jpeg,gif,mp4,mp3,doc,docx,zip,tar,gz"
    )

    # Application Configuration
    app_name: str = Field(default="IPFS Storage System")
    version: str = Field(default="0.1.0")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "",
        "env_nested_delimiter": "__",
    }

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Get allowed file extensions as a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
