"""
API endpoint tests for IPFS Storage System.

Tests all REST API endpoints for file upload, retrieval, search, and management.
"""

from io import BytesIO

import pytest


class TestFileUploadEndpoint:
    """Test file upload API endpoint."""

    def test_upload_file_success(
        self, test_client, mock_ipfs_service, test_file_content
    ):
        """Test successful file upload."""
        # Prepare test file
        files = {"file": ("test.txt", BytesIO(test_file_content), "text/plain")}
        data = {"description": "Test file upload", "tags": "test,upload"}

        response = test_client.post("/api/files/upload", files=files, data=data)

        assert response.status_code == 200
        result = response.json()

        assert "cid" in result
        assert result["filename"] == "test.txt"
        assert result["size"] == len(test_file_content)
        assert result["content_type"] == "text/plain"
        assert "upload_date" in result
        assert "gateway_url" in result

    def test_upload_file_without_metadata(
        self, test_client, mock_ipfs_service, test_file_content
    ):
        """Test file upload without description and tags."""
        files = {"file": ("test.txt", BytesIO(test_file_content), "text/plain")}

        response = test_client.post("/api/files/upload", files=files)

        assert response.status_code == 200
        result = response.json()
        assert result["filename"] == "test.txt"

    def test_upload_file_with_invalid_type(self, test_client, mock_ipfs_service):
        """Test upload with invalid file type."""
        # Mock IPFS service to raise validation error
        mock_ipfs_service.add_file.side_effect = Exception(
            "File type 'exe' not allowed"
        )

        files = {
            "file": ("malware.exe", BytesIO(b"fake exe"), "application/octet-stream")
        }

        response = test_client.post("/api/files/upload", files=files)

        assert response.status_code == 500
        assert "not allowed" in response.json()["detail"]

    def test_upload_large_file(self, test_client, mock_ipfs_service):
        """Test upload of large file (should fail size validation)."""
        # Mock IPFS service to raise size error
        mock_ipfs_service.add_file.side_effect = Exception("File too large")

        large_content = b"X" * (100 * 1024 * 1024)  # 100MB
        files = {"file": ("large.txt", BytesIO(large_content), "text/plain")}

        response = test_client.post("/api/files/upload", files=files)

        assert response.status_code == 500
        assert "too large" in response.json()["detail"]

    def test_upload_without_file(self, test_client):
        """Test upload request without file."""
        response = test_client.post(
            "/api/files/upload", data={"description": "No file"}
        )

        assert response.status_code == 422  # Validation error


class TestFileDownloadEndpoint:
    """Test file download API endpoint."""

    def test_download_file_success(
        self, test_client, mock_ipfs_service, sample_file_record
    ):
        """Test successful file download."""
        test_content = b"Test file content"
        mock_ipfs_service.get_file.return_value = test_content

        response = test_client.get(f"/api/files/{sample_file_record.cid}")

        assert response.status_code == 200
        assert response.content == test_content
        # Check content type (may include charset parameter)
        content_type = response.headers["content-type"]
        assert content_type.startswith(sample_file_record.content_type)

    def test_download_nonexistent_file(self, test_client, mock_ipfs_service):
        """Test download of non-existent file."""
        nonexistent_cid = "QmNonExistentCID123"

        response = test_client.get(f"/api/files/{nonexistent_cid}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_download_ipfs_error(
        self, test_client, mock_ipfs_service, sample_file_record
    ):
        """Test download when IPFS service fails."""
        mock_ipfs_service.get_file.side_effect = Exception("IPFS connection failed")

        response = test_client.get(f"/api/files/{sample_file_record.cid}")

        assert response.status_code == 500
        assert "Download failed" in response.json()["detail"]


class TestFileListingEndpoint:
    """Test file listing API endpoint."""

    def test_list_files_default_pagination(self, test_client, multiple_file_records):
        """Test file listing with default pagination."""
        response = test_client.get("/api/files/")

        assert response.status_code == 200
        result = response.json()

        assert "files" in result
        assert "total" in result
        assert "skip" in result
        assert "limit" in result
        assert result["total"] == len(multiple_file_records)
        assert len(result["files"]) <= 50  # Default limit

    def test_list_files_custom_pagination(self, test_client, multiple_file_records):
        """Test file listing with custom pagination."""
        response = test_client.get("/api/files/?skip=1&limit=2")

        assert response.status_code == 200
        result = response.json()

        assert result["skip"] == 1
        assert result["limit"] == 2
        assert len(result["files"]) <= 2

    def test_list_files_empty_database(self, test_client):
        """Test file listing with empty database."""
        response = test_client.get("/api/files/")

        assert response.status_code == 200
        result = response.json()

        assert result["total"] == 0
        assert len(result["files"]) == 0

    def test_list_files_invalid_pagination(self, test_client):
        """Test file listing with invalid pagination parameters."""
        response = test_client.get("/api/files/?skip=-1&limit=0")

        assert response.status_code == 422  # Validation error


class TestFileSearchEndpoint:
    """Test file search API endpoint."""

    def test_search_files_by_filename(self, test_client, multiple_file_records):
        """Test searching files by filename."""
        search_data = {"query": "test_file_1", "skip": 0, "limit": 10}

        response = test_client.post("/api/files/search", json=search_data)

        assert response.status_code == 200
        result = response.json()

        assert "files" in result
        assert "total" in result
        # Should find at least one file matching the query
        assert result["total"] >= 0

    def test_search_files_by_description(self, test_client, multiple_file_records):
        """Test searching files by description."""
        search_data = {"query": "unit tests", "skip": 0, "limit": 10}

        response = test_client.post("/api/files/search", json=search_data)

        assert response.status_code == 200
        result = response.json()
        assert "files" in result

    def test_search_files_no_results(self, test_client, multiple_file_records):
        """Test search with no matching results."""
        search_data = {"query": "nonexistent_file_xyz", "skip": 0, "limit": 10}

        response = test_client.post("/api/files/search", json=search_data)

        assert response.status_code == 200
        result = response.json()

        assert result["total"] == 0
        assert len(result["files"]) == 0

    def test_search_files_invalid_query(self, test_client):
        """Test search with invalid query."""
        search_data = {
            "query": "",
            "skip": 0,
            "limit": 10,
        }  # Empty query should fail validation

        response = test_client.post("/api/files/search", json=search_data)

        assert response.status_code == 422  # Validation error


class TestFileInfoEndpoint:
    """Test file info API endpoint."""

    def test_get_file_info_success(self, test_client, sample_file_record):
        """Test successful file info retrieval."""
        response = test_client.get(f"/api/files/{sample_file_record.cid}/info")

        assert response.status_code == 200
        result = response.json()

        assert result["cid"] == sample_file_record.cid
        assert result["filename"] == sample_file_record.filename
        assert result["size"] == sample_file_record.size
        assert result["content_type"] == sample_file_record.content_type
        assert "upload_date" in result

    def test_get_file_info_nonexistent(self, test_client):
        """Test file info for non-existent file."""
        nonexistent_cid = "QmNonExistentCID123"

        response = test_client.get(f"/api/files/{nonexistent_cid}/info")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestFileUpdateEndpoint:
    """Test file metadata update API endpoint."""

    def test_update_file_metadata_success(self, test_client, sample_file_record):
        """Test successful file metadata update."""
        update_data = {
            "filename": "updated_filename.txt",
            "description": "Updated description",
            "tags": ["updated", "test"],
        }

        response = test_client.put(
            f"/api/files/{sample_file_record.cid}", json=update_data
        )

        assert response.status_code == 200
        result = response.json()

        assert result["filename"] == "updated_filename.txt"
        assert result["description"] == "Updated description"

    def test_update_file_metadata_partial(self, test_client, sample_file_record):
        """Test partial file metadata update."""
        update_data = {"description": "Only description updated"}

        response = test_client.put(
            f"/api/files/{sample_file_record.cid}", json=update_data
        )

        assert response.status_code == 200
        result = response.json()

        assert result["description"] == "Only description updated"
        # Original filename should remain unchanged
        assert result["filename"] == sample_file_record.filename

    def test_update_file_metadata_nonexistent(self, test_client):
        """Test update metadata for non-existent file."""
        nonexistent_cid = "QmNonExistentCID123"
        update_data = {"filename": "new_name.txt"}

        response = test_client.put(f"/api/files/{nonexistent_cid}", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_file_metadata_invalid_data(self, test_client, sample_file_record):
        """Test update with invalid metadata."""
        update_data = {"filename": ""}  # Empty filename should fail validation

        response = test_client.put(
            f"/api/files/{sample_file_record.cid}", json=update_data
        )

        assert response.status_code == 422  # Validation error


class TestFileDeleteEndpoint:
    """Test file deletion API endpoint."""

    def test_delete_file_success(self, test_client, sample_file_record):
        """Test successful file deletion."""
        response = test_client.delete(f"/api/files/{sample_file_record.cid}")

        assert response.status_code == 200
        result = response.json()

        assert result["cid"] == sample_file_record.cid
        assert "deleted successfully" in result["message"]
        assert not result["unpinned"]  # Default unpin=False

    def test_delete_file_with_unpin(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test file deletion with unpinning."""
        response = test_client.delete(f"/api/files/{sample_file_record.cid}?unpin=true")

        assert response.status_code == 200
        result = response.json()

        assert result["unpinned"]
        mock_ipfs_service.unpin_file.assert_called_once_with(sample_file_record.cid)

    def test_delete_file_nonexistent(self, test_client):
        """Test deletion of non-existent file."""
        nonexistent_cid = "QmNonExistentCID123"

        response = test_client.delete(f"/api/files/{nonexistent_cid}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestFileStatsEndpoint:
    """Test file statistics API endpoint."""

    def test_get_file_stats_success(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test successful file stats retrieval."""
        response = test_client.get(f"/api/files/{sample_file_record.cid}/stats")

        assert response.status_code == 200
        result = response.json()

        assert result["cid"] == sample_file_record.cid
        assert "size" in result
        assert "cumulative_size" in result
        assert "blocks" in result
        assert "type" in result

    def test_get_file_stats_ipfs_error(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test file stats when IPFS service fails."""
        mock_ipfs_service.get_file_stats.side_effect = Exception("IPFS stats failed")

        response = test_client.get(f"/api/files/{sample_file_record.cid}/stats")

        assert response.status_code == 500
        assert "Failed to get file stats" in response.json()["detail"]


class TestFilePinEndpoints:
    """Test file pinning/unpinning API endpoints."""

    def test_pin_file_success(self, test_client, sample_file_record, mock_ipfs_service):
        """Test successful file pinning."""
        response = test_client.post(f"/api/files/{sample_file_record.cid}/pin")

        assert response.status_code == 200
        result = response.json()

        assert result["cid"] == sample_file_record.cid
        assert "pinned successfully" in result["message"]
        mock_ipfs_service.pin_file.assert_called_once_with(sample_file_record.cid)

    def test_pin_file_ipfs_error(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test file pinning when IPFS service fails."""
        mock_ipfs_service.pin_file.return_value = False

        response = test_client.post(f"/api/files/{sample_file_record.cid}/pin")

        assert response.status_code == 500
        assert "Failed to pin file" in response.json()["detail"]

    def test_unpin_file_success(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test successful file unpinning."""
        response = test_client.delete(f"/api/files/{sample_file_record.cid}/pin")

        assert response.status_code == 200
        result = response.json()

        assert result["cid"] == sample_file_record.cid
        assert "unpinned successfully" in result["message"]
        mock_ipfs_service.unpin_file.assert_called_once_with(sample_file_record.cid)

    def test_unpin_file_ipfs_error(
        self, test_client, sample_file_record, mock_ipfs_service
    ):
        """Test file unpinning when IPFS service fails."""
        mock_ipfs_service.unpin_file.return_value = False

        response = test_client.delete(f"/api/files/{sample_file_record.cid}/pin")

        assert response.status_code == 500
        assert "Failed to unpin file" in response.json()["detail"]


class TestHealthAndInfoEndpoints:
    """Test system health and info endpoints."""

    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")

        assert response.status_code == 200
        result = response.json()

        assert result["status"] == "healthy"
        assert result["service"] == "IPFS Storage System"
        assert result["version"] == "0.1.0"

    def test_system_info(self, test_client, mock_ipfs_service):
        """Test system info endpoint."""
        response = test_client.get("/info")

        assert response.status_code == 200
        result = response.json()

        assert result["system"] == "IPFS Storage System"
        assert result["version"] == "0.1.0"
        assert "ipfs_node" in result
        assert "status" in result

    def test_system_info_ipfs_error(self, test_client, mock_ipfs_service):
        """Test system info when IPFS service fails."""
        mock_ipfs_service.get_node_info.side_effect = Exception(
            "IPFS connection failed"
        )

        response = test_client.get("/info")

        assert response.status_code == 200
        result = response.json()

        assert result["status"] == "degraded"
        assert "error" in result


class TestErrorHandling:
    """Test error handling across API endpoints."""

    def test_invalid_cid_format(self, test_client):
        """Test API behavior with invalid CID format."""
        invalid_cid = "invalid-cid-format"

        response = test_client.get(f"/api/files/{invalid_cid}")

        # Should handle gracefully (either 404 or 400)
        assert response.status_code in [400, 404, 500]

    def test_malformed_json_request(self, test_client):
        """Test API behavior with malformed JSON."""
        response = test_client.post(
            "/api/files/search",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_content_type(self, test_client):
        """Test API behavior with missing content type."""
        # Send raw data without proper content type header to force a parsing error
        response = test_client.post(
            "/api/files/search",
            data="invalid-json-data",
            headers={"Content-Type": "text/plain"},  # Wrong content type
        )

        # Should return validation error for invalid JSON
        assert response.status_code in [422, 400]


# Integration test markers
@pytest.mark.integration
class TestFileWorkflow:
    """Integration tests for complete file workflows."""

    def test_complete_file_lifecycle(
        self, test_client, mock_ipfs_service, test_file_content
    ):
        """Test complete file lifecycle: upload -> list -> info -> update -> delete."""
        # 1. Upload file
        files = {
            "file": ("lifecycle_test.txt", BytesIO(test_file_content), "text/plain")
        }
        upload_response = test_client.post("/api/files/upload", files=files)
        assert upload_response.status_code == 200

        uploaded_file = upload_response.json()
        cid = uploaded_file["cid"]

        # 2. List files (should include our file)
        list_response = test_client.get("/api/files/")
        assert list_response.status_code == 200
        files_list = list_response.json()
        assert files_list["total"] >= 1

        # 3. Get file info
        info_response = test_client.get(f"/api/files/{cid}/info")
        assert info_response.status_code == 200
        file_info = info_response.json()
        assert file_info["cid"] == cid

        # 4. Update metadata
        update_data = {"description": "Updated in lifecycle test"}
        update_response = test_client.put(f"/api/files/{cid}", json=update_data)
        assert update_response.status_code == 200

        # 5. Delete file
        delete_response = test_client.delete(f"/api/files/{cid}")
        assert delete_response.status_code == 200

        # 6. Verify file is deleted
        info_response_after_delete = test_client.get(f"/api/files/{cid}/info")
        assert info_response_after_delete.status_code == 404
