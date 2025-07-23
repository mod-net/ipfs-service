"""
Configuration management for IPFS Storage System.

Handles environment variables and application settings.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # IPFS Configuration
    ipfs_api_url: str = Field(default="http://localhost:5001", env="IPFS_API_URL")
    ipfs_gateway_url: str = Field(default="http://localhost:8080", env="IPFS_GATEWAY_URL")
    ipfs_timeout: int = Field(default=30, env="IPFS_TIMEOUT")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./files.db", env="DATABASE_URL")
    
    # Security Configuration (Optional)
    secret_key: Optional[str] = Field(default=None, env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # File Upload Configuration
    max_file_size: int = Field(default=100 * 1024 * 1024, env="MAX_FILE_SIZE")  # 100MB
    allowed_extensions: str = Field(
        default="txt,pdf,png,jpg,jpeg,gif,mp4,mp3,doc,docx,zip,tar,gz",
        env="ALLOWED_EXTENSIONS"
    )
    
    # Application Configuration
    app_name: str = Field(default="IPFS Storage System", env="APP_NAME")
    version: str = Field(default="0.1.0", env="VERSION")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Get allowed file extensions as a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
