"""
Pydantic models for file operations in IPFS Storage System.

Defines request/response models for file upload, retrieval, and metadata.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    
    cid: str = Field(..., description="IPFS Content Identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME content type")
    upload_date: datetime = Field(..., description="Upload timestamp")
    gateway_url: str = Field(..., description="IPFS gateway URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileMetadata(BaseModel):
    """Model for file metadata."""
    
    id: int = Field(..., description="Database record ID")
    cid: str = Field(..., description="IPFS Content Identifier")
    filename: str = Field(..., description="Display filename")
    original_filename: str = Field(..., description="Original uploaded filename")
    content_type: Optional[str] = Field(None, description="MIME content type")
    size: int = Field(..., description="File size in bytes")
    upload_date: datetime = Field(..., description="Upload timestamp")
    description: Optional[str] = Field(None, description="File description")
    tags: Optional[str] = Field(None, description="File tags (JSON string)")
    uploader_ip: Optional[str] = Field(None, description="Uploader IP address")
    is_pinned: bool = Field(True, description="Whether file is pinned in IPFS")
    gateway_url: str = Field(..., description="IPFS gateway URL")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileListResponse(BaseModel):
    """Response model for file listing."""
    
    files: List[FileMetadata] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    skip: int = Field(..., description="Number of files skipped")
    limit: int = Field(..., description="Maximum files returned")


class FileSearchRequest(BaseModel):
    """Request model for file search."""
    
    query: str = Field(..., min_length=1, description="Search query")
    skip: int = Field(0, ge=0, description="Number of results to skip")
    limit: int = Field(50, ge=1, le=100, description="Maximum results to return")


class FileUpdateRequest(BaseModel):
    """Request model for updating file metadata."""
    
    filename: Optional[str] = Field(None, description="New filename")
    description: Optional[str] = Field(None, description="File description")
    tags: Optional[List[str]] = Field(None, description="File tags")
    
    @validator('filename')
    def validate_filename(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Filename cannot be empty')
        return v.strip() if v else v


class FileStatsResponse(BaseModel):
    """Response model for file statistics."""
    
    cid: str = Field(..., description="IPFS Content Identifier")
    size: int = Field(..., description="File size in bytes")
    cumulative_size: int = Field(..., description="Cumulative size including metadata")
    blocks: int = Field(..., description="Number of blocks")
    type: str = Field(..., description="Object type")


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    
    system: str = Field(..., description="System name")
    version: str = Field(..., description="System version")
    ipfs_node: str = Field(..., description="IPFS node ID")
    ipfs_version: str = Field(..., description="IPFS version")
    database: str = Field(..., description="Database type")
    status: str = Field(..., description="System status")
    total_files: Optional[int] = Field(None, description="Total files stored")
    total_size: Optional[int] = Field(None, description="Total storage used")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
