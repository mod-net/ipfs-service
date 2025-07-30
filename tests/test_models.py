"""
Pydantic model validation tests for IPFS Storage System.

Tests all request/response models for proper validation and serialization.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.file import (
    ErrorResponse,
    FileListResponse,
    FileMetadata,
    FileSearchRequest,
    FileStatsResponse,
    FileUpdateRequest,
    FileUploadResponse,
    HealthResponse,
    SystemInfoResponse,
)


class TestFileUploadResponse:
    """Test FileUploadResponse model validation."""

    def test_valid_file_upload_response(self):
        """Test valid file upload response creation."""
        response = FileUploadResponse(
            cid="QmTestCID123456789",
            filename="test.txt",
            size=1024,
            content_type="text/plain",
            upload_date=datetime.utcnow(),
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert response.cid == "QmTestCID123456789"
        assert response.filename == "test.txt"
        assert response.size == 1024
        assert response.content_type == "text/plain"
        assert isinstance(response.upload_date, datetime)
        assert response.gateway_url == "http://localhost:8080/ipfs/QmTestCID123456789"

    def test_file_upload_response_without_content_type(self):
        """Test file upload response without content type (optional field)."""
        response = FileUploadResponse(
            cid="QmTestCID123456789",
            filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert response.content_type is None

    def test_file_upload_response_missing_required_fields(self):
        """Test file upload response with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            FileUploadResponse(
                cid="QmTestCID123456789",
                # Missing filename, size, upload_date, gateway_url
            )

        errors = exc_info.value.errors()
        required_fields = {"filename", "size", "upload_date", "gateway_url"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)

    def test_file_upload_response_json_serialization(self):
        """Test JSON serialization with datetime encoding."""
        upload_date = datetime.utcnow()
        response = FileUploadResponse(
            cid="QmTestCID123456789",
            filename="test.txt",
            size=1024,
            content_type="text/plain",
            upload_date=upload_date,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        json_data = response.dict()
        assert json_data["upload_date"] == upload_date

        # Test JSON encoding
        json_str = response.json()
        assert upload_date.isoformat() in json_str


class TestFileMetadata:
    """Test FileMetadata model validation."""

    def test_valid_file_metadata(self):
        """Test valid file metadata creation."""
        metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="original_test.txt",
            content_type="text/plain",
            size=1024,
            upload_date=datetime.utcnow(),
            description="Test file",
            tags='["test", "sample"]',
            uploader_ip="127.0.0.1",
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert metadata.id == 1
        assert metadata.cid == "QmTestCID123456789"
        assert metadata.filename == "test.txt"
        assert metadata.original_filename == "original_test.txt"
        assert metadata.is_pinned is True

    def test_file_metadata_optional_fields(self):
        """Test file metadata with optional fields as None."""
        metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert metadata.content_type is None
        assert metadata.description is None
        assert metadata.tags is None
        assert metadata.uploader_ip is None

    def test_file_metadata_missing_required_fields(self):
        """Test file metadata with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadata(
                # Missing required fields
                filename="test.txt"
            )

        errors = exc_info.value.errors()
        required_fields = {
            "id",
            "cid",
            "original_filename",
            "size",
            "upload_date",
            "gateway_url",
        }
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)


class TestFileListResponse:
    """Test FileListResponse model validation."""

    def test_valid_file_list_response(self):
        """Test valid file list response creation."""
        file_metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        response = FileListResponse(files=[file_metadata], total=1, skip=0, limit=50)

        assert len(response.files) == 1
        assert response.total == 1
        assert response.skip == 0
        assert response.limit == 50
        assert isinstance(response.files[0], FileMetadata)

    def test_empty_file_list_response(self):
        """Test empty file list response."""
        response = FileListResponse(files=[], total=0, skip=0, limit=50)

        assert len(response.files) == 0
        assert response.total == 0

    def test_file_list_response_missing_fields(self):
        """Test file list response with missing required fields."""
        with pytest.raises(ValidationError):
            FileListResponse(
                files=[]
                # Missing total, skip, limit
            )


class TestFileSearchRequest:
    """Test FileSearchRequest model validation."""

    def test_valid_file_search_request(self):
        """Test valid file search request creation."""
        request = FileSearchRequest(query="test file", skip=0, limit=10)

        assert request.query == "test file"
        assert request.skip == 0
        assert request.limit == 10

    def test_file_search_request_defaults(self):
        """Test file search request with default values."""
        request = FileSearchRequest(query="test")

        assert request.query == "test"
        assert request.skip == 0  # Default value
        assert request.limit == 50  # Default value

    def test_file_search_request_empty_query(self):
        """Test file search request with empty query (should fail)."""
        with pytest.raises(ValidationError) as exc_info:
            FileSearchRequest(query="")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("query",) for error in errors)

    def test_file_search_request_invalid_pagination(self):
        """Test file search request with invalid pagination values."""
        # Negative skip
        with pytest.raises(ValidationError):
            FileSearchRequest(query="test", skip=-1)

        # Invalid limit (too high)
        with pytest.raises(ValidationError):
            FileSearchRequest(query="test", limit=101)

        # Invalid limit (too low)
        with pytest.raises(ValidationError):
            FileSearchRequest(query="test", limit=0)


class TestFileUpdateRequest:
    """Test FileUpdateRequest model validation."""

    def test_valid_file_update_request(self):
        """Test valid file update request creation."""
        request = FileUpdateRequest(
            filename="updated_file.txt",
            description="Updated description",
            tags=["updated", "test"],
        )

        assert request.filename == "updated_file.txt"
        assert request.description == "Updated description"
        assert request.tags == ["updated", "test"]

    def test_file_update_request_optional_fields(self):
        """Test file update request with optional fields as None."""
        request = FileUpdateRequest()

        assert request.filename is None
        assert request.description is None
        assert request.tags is None

    def test_file_update_request_partial_update(self):
        """Test file update request with only some fields."""
        request = FileUpdateRequest(description="Only description updated")

        assert request.filename is None
        assert request.description == "Only description updated"
        assert request.tags is None

    def test_file_update_request_filename_validation(self):
        """Test filename validation in update request."""
        # Empty filename should fail validation
        with pytest.raises(ValidationError) as exc_info:
            FileUpdateRequest(filename="")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("filename",) for error in errors)

    def test_file_update_request_filename_whitespace_handling(self):
        """Test filename whitespace handling."""
        request = FileUpdateRequest(filename="  spaced_filename.txt  ")

        # Should be stripped
        assert request.filename == "spaced_filename.txt"


class TestFileStatsResponse:
    """Test FileStatsResponse model validation."""

    def test_valid_file_stats_response(self):
        """Test valid file stats response creation."""
        response = FileStatsResponse(
            cid="QmTestCID123456789",
            size=1024,
            cumulative_size=1024,
            blocks=1,
            type="file",
        )

        assert response.cid == "QmTestCID123456789"
        assert response.size == 1024
        assert response.cumulative_size == 1024
        assert response.blocks == 1
        assert response.type == "file"

    def test_file_stats_response_missing_fields(self):
        """Test file stats response with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            FileStatsResponse(
                cid="QmTestCID123456789"
                # Missing size, cumulative_size, blocks, type
            )

        errors = exc_info.value.errors()
        required_fields = {"size", "cumulative_size", "blocks", "type"}
        error_fields = {error["loc"][0] for error in errors}
        assert required_fields.issubset(error_fields)


class TestSystemInfoResponse:
    """Test SystemInfoResponse model validation."""

    def test_valid_system_info_response(self):
        """Test valid system info response creation."""
        response = SystemInfoResponse(
            system="IPFS Storage System",
            version="0.1.0",
            ipfs_node="QmTestNodeID123456789",
            ipfs_version="0.14.0",
            database="SQLite",
            status="operational",
            total_files=100,
            total_size=1024000,
        )

        assert response.system == "IPFS Storage System"
        assert response.version == "0.1.0"
        assert response.ipfs_node == "QmTestNodeID123456789"
        assert response.ipfs_version == "0.14.0"
        assert response.database == "SQLite"
        assert response.status == "operational"
        assert response.total_files == 100
        assert response.total_size == 1024000

    def test_system_info_response_optional_fields(self):
        """Test system info response with optional fields as None."""
        response = SystemInfoResponse(
            system="IPFS Storage System",
            version="0.1.0",
            ipfs_node="QmTestNodeID123456789",
            ipfs_version="0.14.0",
            database="SQLite",
            status="operational",
        )

        assert response.total_files is None
        assert response.total_size is None


class TestHealthResponse:
    """Test HealthResponse model validation."""

    def test_valid_health_response(self):
        """Test valid health response creation."""
        timestamp = datetime.utcnow()
        response = HealthResponse(
            status="healthy",
            service="IPFS Storage System",
            version="0.1.0",
            timestamp=timestamp,
        )

        assert response.status == "healthy"
        assert response.service == "IPFS Storage System"
        assert response.version == "0.1.0"
        assert response.timestamp == timestamp

    def test_health_response_default_timestamp(self):
        """Test health response with default timestamp."""
        response = HealthResponse(
            status="healthy", service="IPFS Storage System", version="0.1.0"
        )

        assert isinstance(response.timestamp, datetime)
        # Should be recent (within last minute)
        time_diff = datetime.utcnow() - response.timestamp
        assert time_diff.total_seconds() < 60

    def test_health_response_json_serialization(self):
        """Test health response JSON serialization."""
        response = HealthResponse(
            status="healthy", service="IPFS Storage System", version="0.1.0"
        )

        json_str = response.json()
        assert response.timestamp.isoformat() in json_str


class TestErrorResponse:
    """Test ErrorResponse model validation."""

    def test_valid_error_response(self):
        """Test valid error response creation."""
        timestamp = datetime.utcnow()
        response = ErrorResponse(
            error="File not found",
            detail="The requested file does not exist",
            code="FILE_NOT_FOUND",
            timestamp=timestamp,
        )

        assert response.error == "File not found"
        assert response.detail == "The requested file does not exist"
        assert response.code == "FILE_NOT_FOUND"
        assert response.timestamp == timestamp

    def test_error_response_minimal(self):
        """Test error response with only required fields."""
        response = ErrorResponse(error="Something went wrong")

        assert response.error == "Something went wrong"
        assert response.detail is None
        assert response.code is None
        assert isinstance(response.timestamp, datetime)

    def test_error_response_default_timestamp(self):
        """Test error response with default timestamp."""
        response = ErrorResponse(error="Error occurred")

        assert isinstance(response.timestamp, datetime)
        # Should be recent (within last minute)
        time_diff = datetime.utcnow() - response.timestamp
        assert time_diff.total_seconds() < 60

    def test_error_response_json_serialization(self):
        """Test error response JSON serialization."""
        response = ErrorResponse(
            error="Test error", detail="Test error detail", code="TEST_ERROR"
        )

        json_str = response.json()
        assert "Test error" in json_str
        assert response.timestamp.isoformat() in json_str


class TestModelValidationEdgeCases:
    """Test edge cases and validation scenarios."""

    def test_large_file_size_validation(self):
        """Test models with large file sizes."""
        large_size = 10 * 1024 * 1024 * 1024  # 10GB

        metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="large_file.bin",
            original_filename="large_file.bin",
            size=large_size,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert metadata.size == large_size

    def test_unicode_filename_validation(self):
        """Test models with unicode filenames."""
        unicode_filename = "测试文件.txt"

        metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename=unicode_filename,
            original_filename=unicode_filename,
            size=1024,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert metadata.filename == unicode_filename
        assert metadata.original_filename == unicode_filename

    def test_special_characters_in_description(self):
        """Test models with special characters in description."""
        special_description = "File with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"

        metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            description=special_description,
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        assert metadata.description == special_description

    def test_long_cid_validation(self):
        """Test models with very long CIDs."""
        long_cid = "Qm" + "a" * 100  # Very long CID

        metadata = FileMetadata(
            id=1,
            cid=long_cid,
            filename="test.txt",
            original_filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url=f"http://localhost:8080/ipfs/{long_cid}",
        )

        assert metadata.cid == long_cid

    def test_empty_tags_list(self):
        """Test update request with empty tags list."""
        request = FileUpdateRequest(tags=[])

        assert request.tags == []

    def test_none_vs_empty_string_handling(self):
        """Test difference between None and empty string handling."""
        # None should be allowed for optional fields
        request1 = FileUpdateRequest(description=None)
        assert request1.description is None

        # Empty string should be allowed for description
        request2 = FileUpdateRequest(description="")
        assert request2.description == ""

        # But empty filename should fail validation
        with pytest.raises(ValidationError):
            FileUpdateRequest(filename="")


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_file_metadata_round_trip_serialization(self):
        """Test file metadata serialization and deserialization."""
        original_metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            size=1024,
            upload_date=datetime.utcnow(),
            description="Test file",
            tags='["test", "sample"]',
            uploader_ip="127.0.0.1",
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        # Serialize to dict
        metadata_dict = original_metadata.dict()

        # Deserialize back to model
        restored_metadata = FileMetadata(**metadata_dict)

        # Should be identical
        assert restored_metadata.id == original_metadata.id
        assert restored_metadata.cid == original_metadata.cid
        assert restored_metadata.filename == original_metadata.filename
        assert restored_metadata.upload_date == original_metadata.upload_date

    def test_file_list_response_serialization(self):
        """Test file list response serialization."""
        file_metadata = FileMetadata(
            id=1,
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            size=1024,
            upload_date=datetime.utcnow(),
            is_pinned=True,
            gateway_url="http://localhost:8080/ipfs/QmTestCID123456789",
        )

        response = FileListResponse(files=[file_metadata], total=1, skip=0, limit=50)

        # Test JSON serialization
        json_str = response.json()
        assert "QmTestCID123456789" in json_str
        assert "test.txt" in json_str

        # Test dict serialization
        response_dict = response.dict()
        assert len(response_dict["files"]) == 1
        assert response_dict["total"] == 1
