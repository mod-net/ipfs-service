"""
File management API endpoints for IPFS Storage System.

Provides REST API for file upload, retrieval, search, and management operations.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.database import DatabaseService, FileRecord
from app.logging_config import get_logger, log_file_operation, log_ipfs_operation
from app.models.file import (
    FileListResponse,
    FileMetadata,
    FileSearchRequest,
    FileStatsResponse,
    FileUpdateRequest,
    FileUploadResponse,
)
from app.services.ipfs import IPFSService

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


def get_ipfs_service():
    """Dependency to get IPFS service instance."""
    return IPFSService()


def get_database_service():
    """Dependency to get database service instance."""
    return DatabaseService()


def file_record_to_metadata(
    file_record: FileRecord, ipfs_service: IPFSService
) -> FileMetadata:
    """Convert FileRecord to FileMetadata with gateway URL."""
    return FileMetadata(
        id=file_record.id,
        cid=file_record.cid,
        filename=file_record.filename,
        original_filename=file_record.original_filename,
        content_type=file_record.content_type,
        size=file_record.size,
        upload_date=file_record.upload_date,
        description=file_record.description,
        tags=file_record.tags,
        uploader_ip=file_record.uploader_ip,
        is_pinned=bool(file_record.is_pinned),
        gateway_url=ipfs_service.get_gateway_url(file_record.cid),
    )


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile,
    description: str | None = Query(None, description="File description"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Upload a file to IPFS and store metadata in database.

    - **file**: File to upload (multipart/form-data)
    - **description**: Optional file description
    - **tags**: Optional comma-separated tags
    """
    try:
        logger.info(f"📤 Starting file upload: {file.filename} ({file.size} bytes)")

        # Upload file to IPFS
        import time

        start_time = time.time()
        ipfs_result = await ipfs_service.add_file(file)
        upload_duration = time.time() - start_time

        logger.info(
            f"✅ IPFS upload successful: {ipfs_result['cid']} ({upload_duration:.3f}s)"
        )
        log_ipfs_operation("UPLOAD", ipfs_result["cid"], True, duration=upload_duration)

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Process tags
        tags_json = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_list:
                tags_json = json.dumps(tag_list)

        # Store metadata in database
        file_record = db_service.create_file_record(
            cid=ipfs_result["cid"],
            filename=ipfs_result["filename"],
            original_filename=ipfs_result["filename"],
            content_type=ipfs_result["content_type"],
            size=ipfs_result["size"],
            description=description,
            tags=tags_json,
            uploader_ip=client_ip,
        )

        log_file_operation(
            "UPLOAD", file_record.cid, file_record.filename, file_record.size, client_ip
        )

        logger.info(
            f"📁 File metadata stored: {file_record.filename} -> {file_record.cid}"
        )

        return FileUploadResponse(
            cid=file_record.cid,
            filename=file_record.filename,
            size=file_record.size,
            content_type=file_record.content_type,
            upload_date=file_record.upload_date,
            gateway_url=ipfs_service.get_gateway_url(file_record.cid),
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Upload failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/files/{cid}")
async def download_file(
    cid: str,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Download a file by its IPFS CID.

    - **cid**: IPFS Content Identifier
    """
    try:
        # Get file metadata from database
        file_record = db_service.get_file_by_cid(cid)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found in database")

        # Get file content from IPFS
        content = await ipfs_service.get_file(cid)

        # Create streaming response
        def generate():
            yield content

        return StreamingResponse(
            generate(),
            media_type=file_record.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_filename}",
                "Content-Length": str(len(content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Download failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/files/", response_model=FileListResponse)
async def list_files(
    skip: int = Query(0, ge=0, description="Number of files to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum files to return"),
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    List all files with pagination.

    - **skip**: Number of files to skip (for pagination)
    - **limit**: Maximum number of files to return
    """
    try:
        # Get files from database
        files = db_service.get_all_files(skip=skip, limit=limit)
        total = db_service.get_file_count()

        # Convert to metadata objects
        file_metadata = [
            file_record_to_metadata(file_record, ipfs_service) for file_record in files
        ]

        return FileListResponse(
            files=file_metadata, total=total, skip=skip, limit=limit
        )

    except Exception as e:
        msg = f"Failed to list files: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/files/{cid}/info", response_model=FileMetadata)
async def get_file_info(
    cid: str,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Get file metadata by CID.

    - **cid**: IPFS Content Identifier
    """
    try:
        # Get file from database
        file_record = db_service.get_file_by_cid(cid)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        return file_record_to_metadata(file_record, ipfs_service)

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to get file info: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.post("/files/search", response_model=FileListResponse)
async def search_files(
    search_request: FileSearchRequest,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Search files by filename or description.

    - **query**: Search query string
    - **skip**: Number of results to skip
    - **limit**: Maximum results to return
    """
    try:
        # Search files in database
        files, total = db_service.search_files(
            query=search_request.query,
            skip=search_request.skip,
            limit=search_request.limit,
        )

        # Convert to metadata objects
        file_metadata = [
            file_record_to_metadata(file_record, ipfs_service) for file_record in files
        ]

        return FileListResponse(
            files=file_metadata,
            total=total,
            skip=search_request.skip,
            limit=search_request.limit,
        )

    except Exception as e:
        msg = f"Search failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.put("/files/{cid}", response_model=FileMetadata)
async def update_file_metadata(
    cid: str,
    update_request: FileUpdateRequest,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Update file metadata (filename, description, tags).

    - **cid**: IPFS Content Identifier
    - **filename**: New filename (optional)
    - **description**: New description (optional)
    - **tags**: New tags list (optional)
    """
    try:
        # Use a single database session for the entire operation
        db = db_service.get_session()
        try:
            # Get existing file record in the same session we'll use for updates
            file_record = db.query(FileRecord).filter(FileRecord.cid == cid).first()
            if not file_record:
                raise HTTPException(status_code=404, detail="File not found")

            # Update fields
            if update_request.filename is not None:
                file_record.filename = update_request.filename

            if update_request.description is not None:
                file_record.description = update_request.description

            if update_request.tags is not None:
                file_record.tags = (
                    json.dumps(update_request.tags) if update_request.tags else None
                )

            db.commit()
            db.refresh(file_record)

            return file_record_to_metadata(file_record, ipfs_service)

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Update failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.delete("/files/{cid}")
async def delete_file(
    cid: str,
    unpin: bool = Query(False, description="Whether to unpin from IPFS"),
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Delete file metadata from database and optionally unpin from IPFS.

    - **cid**: IPFS Content Identifier
    - **unpin**: Whether to unpin the file from IPFS (default: False)
    """
    try:
        # Check if file exists
        file_record = db_service.get_file_by_cid(cid)
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete from database
        success = db_service.delete_file_record(cid)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file record")

        # Optionally unpin from IPFS
        if unpin:
            await ipfs_service.unpin_file(cid)

        return {"message": "File deleted successfully", "cid": cid, "unpinned": unpin}

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Delete failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.get("/files/{cid}/stats", response_model=FileStatsResponse)
async def get_file_stats(
    cid: str,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Get IPFS statistics for a file.

    - **cid**: IPFS Content Identifier
    """
    try:
        stats = await ipfs_service.get_file_stats(cid)

        return FileStatsResponse(
            cid=cid,
            size=stats.get("DataSize", 0),
            cumulative_size=stats.get("CumulativeSize", 0),
            blocks=stats.get("NumLinks", 0),
            type=stats.get("Type", "unknown"),
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to get file stats: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.post("/files/{cid}/pin")
async def pin_file(
    cid: str,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Pin a file in IPFS to prevent garbage collection.

    - **cid**: IPFS Content Identifier
    """
    try:
        # Pin in IPFS
        success = await ipfs_service.pin_file(cid)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to pin file in IPFS")

        # Update database record
        file_record = db_service.get_file_by_cid(cid)
        if file_record:
            db = db_service.get_session()
            try:
                file_record.is_pinned = 1
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Failed to update pin status in database: {e}")
            finally:
                db.close()

        return {"message": "File pinned successfully", "cid": cid}

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Pin failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e


@router.delete("/files/{cid}/pin")
async def unpin_file(
    cid: str,
    ipfs_service: IPFSService = Depends(get_ipfs_service),
    db_service: DatabaseService = Depends(get_database_service),
):
    """
    Unpin a file in IPFS to allow garbage collection.

    - **cid**: IPFS Content Identifier
    """
    try:
        # Unpin from IPFS
        success = await ipfs_service.unpin_file(cid)
        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to unpin file from IPFS"
            )

        # Update database record
        file_record = db_service.get_file_by_cid(cid)
        if file_record:
            db = db_service.get_session()
            try:
                file_record.is_pinned = 0
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Failed to update pin status in database: {e}")
            finally:
                db.close()

        return {"message": "File unpinned successfully", "cid": cid}

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Unpin failed: {str(e)}"
        raise HTTPException(status_code=500, detail=msg) from e
