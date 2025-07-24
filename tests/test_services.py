"""
Service layer tests for IPFS Storage System.

Tests IPFS service and database service functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException, UploadFile
from io import BytesIO

from app.services.ipfs import IPFSService
from app.database import DatabaseService, FileRecord
from app.config import get_settings


class TestIPFSService:
    """Test IPFS service functionality."""
    
    @pytest.fixture
    def ipfs_service(self):
        """Create IPFS service instance."""
        return IPFSService()
    
    @pytest.fixture
    def mock_ipfs_client(self):
        """Create mock IPFS client."""
        mock_client = Mock()
        mock_client.id.return_value = {
            "ID": "QmTestNodeID123456789",
            "Version": "0.14.0",
            "AgentVersion": "go-ipfs/0.14.0"
        }
        mock_client.add.return_value = {"Hash": "QmTestCID123456789"}
        mock_client.cat.return_value = b"Test file content"
        mock_client.pin.add.return_value = None
        mock_client.pin.rm.return_value = None
        mock_client.pin.ls.return_value = {"QmTestCID123456789": {"Type": "recursive"}}
        mock_client.object.stat.return_value = {
            "DataSize": 1024,
            "CumulativeSize": 1024,
            "NumLinks": 0,
            "Type": "file"
        }
        mock_client.close.return_value = None
        return mock_client
    
    @pytest.mark.asyncio
    async def test_get_node_info_success(self, ipfs_service, mock_ipfs_client):
        """Test successful IPFS node info retrieval."""
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            node_info = await ipfs_service.get_node_info()
            
            assert node_info["ID"] == "QmTestNodeID123456789"
            assert node_info["Version"] == "0.14.0"
            mock_ipfs_client.id.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_node_info_connection_error(self, ipfs_service):
        """Test IPFS node info retrieval with connection error."""
        with patch.object(ipfs_service, '_get_client', side_effect=Exception("Connection failed")):
            with pytest.raises(HTTPException) as exc_info:
                await ipfs_service.get_node_info()
            
            assert exc_info.value.status_code == 503
            assert "Failed to get IPFS node info" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_add_file_success(self, ipfs_service, mock_ipfs_client, mock_upload_file):
        """Test successful file addition to IPFS."""
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.add_file(mock_upload_file)
            
            assert result["cid"] == "QmTestCID123456789"
            assert result["filename"] == "test_file.txt"
            assert result["size"] == 17  # Size of "Test file content"
            assert result["content_type"] == "text/plain"
            mock_ipfs_client.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_file_size_limit_exceeded(self, ipfs_service, mock_upload_file):
        """Test file addition with size limit exceeded."""
        # Mock large file
        large_content = b"X" * (200 * 1024 * 1024)  # 200MB
        mock_upload_file.read = AsyncMock(return_value=large_content)
        
        with pytest.raises(HTTPException) as exc_info:
            await ipfs_service.add_file(mock_upload_file)
        
        assert exc_info.value.status_code == 413
        assert "File too large" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_add_file_invalid_extension(self, ipfs_service):
        """Test file addition with invalid extension."""
        mock_file = Mock()
        mock_file.filename = "malware.exe"
        mock_file.content_type = "application/octet-stream"
        mock_file.read = AsyncMock(return_value=b"fake executable")
        mock_file.seek = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await ipfs_service.add_file(mock_file)
        
        assert exc_info.value.status_code == 415
        assert "not allowed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_file_success(self, ipfs_service, mock_ipfs_client):
        """Test successful file retrieval from IPFS."""
        test_content = b"Test file content"
        mock_ipfs_client.cat.return_value = test_content
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            content = await ipfs_service.get_file("QmTestCID123456789")
            
            assert content == test_content
            mock_ipfs_client.cat.assert_called_once_with("QmTestCID123456789")
    
    @pytest.mark.asyncio
    async def test_get_file_not_found(self, ipfs_service, mock_ipfs_client):
        """Test file retrieval for non-existent file."""
        mock_ipfs_client.cat.side_effect = Exception("File not found")
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            with pytest.raises(HTTPException) as exc_info:
                await ipfs_service.get_file("QmNonExistentCID")
            
            assert exc_info.value.status_code == 404
            assert "Failed to retrieve file" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_pin_file_success(self, ipfs_service, mock_ipfs_client):
        """Test successful file pinning."""
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.pin_file("QmTestCID123456789")
            
            assert result is True
            mock_ipfs_client.pin.add.assert_called_once_with("QmTestCID123456789")
    
    @pytest.mark.asyncio
    async def test_pin_file_error(self, ipfs_service, mock_ipfs_client):
        """Test file pinning with error."""
        mock_ipfs_client.pin.add.side_effect = Exception("Pin failed")
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.pin_file("QmTestCID123456789")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_unpin_file_success(self, ipfs_service, mock_ipfs_client):
        """Test successful file unpinning."""
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.unpin_file("QmTestCID123456789")
            
            assert result is True
            mock_ipfs_client.pin.rm.assert_called_once_with("QmTestCID123456789")
    
    @pytest.mark.asyncio
    async def test_unpin_file_error(self, ipfs_service, mock_ipfs_client):
        """Test file unpinning with error."""
        mock_ipfs_client.pin.rm.side_effect = Exception("Unpin failed")
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.unpin_file("QmTestCID123456789")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_file_stats_success(self, ipfs_service, mock_ipfs_client):
        """Test successful file statistics retrieval."""
        expected_stats = {
            "DataSize": 1024,
            "CumulativeSize": 1024,
            "NumLinks": 0,
            "Type": "file"
        }
        mock_ipfs_client.object.stat.return_value = expected_stats
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            stats = await ipfs_service.get_file_stats("QmTestCID123456789")
            
            assert stats == expected_stats
            mock_ipfs_client.object.stat.assert_called_once_with("QmTestCID123456789")
    
    @pytest.mark.asyncio
    async def test_get_file_stats_error(self, ipfs_service, mock_ipfs_client):
        """Test file statistics retrieval with error."""
        mock_ipfs_client.object.stat.side_effect = Exception("Stats failed")
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            with pytest.raises(HTTPException) as exc_info:
                await ipfs_service.get_file_stats("QmTestCID123456789")
            
            assert exc_info.value.status_code == 404
            assert "Failed to get file stats" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_list_pinned_files_success(self, ipfs_service, mock_ipfs_client):
        """Test successful pinned files listing."""
        pinned_files = {"QmTestCID123456789": {"Type": "recursive"}}
        mock_ipfs_client.pin.ls.return_value = pinned_files
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.list_pinned_files()
            
            assert result == ["QmTestCID123456789"]
            mock_ipfs_client.pin.ls.assert_called_once_with(type='recursive')
    
    @pytest.mark.asyncio
    async def test_list_pinned_files_error(self, ipfs_service, mock_ipfs_client):
        """Test pinned files listing with error."""
        mock_ipfs_client.pin.ls.side_effect = Exception("List failed")
        
        with patch.object(ipfs_service, '_get_client', return_value=mock_ipfs_client):
            result = await ipfs_service.list_pinned_files()
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_check_connection_success(self, ipfs_service):
        """Test successful connection check."""
        with patch.object(ipfs_service, 'get_node_info', return_value={"ID": "test"}):
            result = await ipfs_service.check_connection()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(self, ipfs_service):
        """Test connection check failure."""
        with patch.object(ipfs_service, 'get_node_info', side_effect=Exception("Connection failed")):
            result = await ipfs_service.check_connection()
            
            assert result is False
    
    def test_get_gateway_url(self, ipfs_service):
        """Test gateway URL generation."""
        cid = "QmTestCID123456789"
        settings = get_settings()
        expected_url = f"{settings.ipfs_gateway_url}/ipfs/{cid}"
        
        result = ipfs_service.get_gateway_url(cid)
        
        assert result == expected_url
    
    def test_close_connection(self, ipfs_service, mock_ipfs_client):
        """Test closing IPFS client connection."""
        ipfs_service._client = mock_ipfs_client
        
        ipfs_service.close()
        
        mock_ipfs_client.close.assert_called_once()
        assert ipfs_service._client is None
    
    def test_close_connection_with_error(self, ipfs_service, mock_ipfs_client):
        """Test closing connection with error (should not raise)."""
        mock_ipfs_client.close.side_effect = Exception("Close failed")
        ipfs_service._client = mock_ipfs_client
        
        # Should not raise exception
        ipfs_service.close()
        
        assert ipfs_service._client is None


class TestDatabaseService:
    """Test database service functionality."""
    
    def test_create_file_record_success(self, db_service, test_db):
        """Test successful file record creation."""
        file_record = db_service.create_file_record(
            cid="QmTestCID123456789",
            filename="test.txt",
            original_filename="test.txt",
            content_type="text/plain",
            size=1024,
            description="Test file",
            tags='["test"]',
            uploader_ip="127.0.0.1"
        )
        
        assert file_record.cid == "QmTestCID123456789"
        assert file_record.filename == "test.txt"
        assert file_record.size == 1024
        assert file_record.id is not None
        assert file_record.upload_date is not None
    
    def test_create_file_record_duplicate_cid(self, db_service, sample_file_record):
        """Test creating file record with duplicate CID."""
        with pytest.raises(Exception):  # Should raise integrity error
            db_service.create_file_record(
                cid=sample_file_record.cid,  # Duplicate CID
                filename="duplicate.txt",
                original_filename="duplicate.txt",
                content_type="text/plain",
                size=512
            )
    
    def test_get_file_by_cid_success(self, db_service, sample_file_record):
        """Test successful file retrieval by CID."""
        file_record = db_service.get_file_by_cid(sample_file_record.cid)
        
        assert file_record is not None
        assert file_record.cid == sample_file_record.cid
        assert file_record.filename == sample_file_record.filename
    
    def test_get_file_by_cid_not_found(self, db_service):
        """Test file retrieval for non-existent CID."""
        file_record = db_service.get_file_by_cid("QmNonExistentCID")
        
        assert file_record is None
    
    def test_get_file_by_id_success(self, db_service, sample_file_record):
        """Test successful file retrieval by ID."""
        file_record = db_service.get_file_by_id(sample_file_record.id)
        
        assert file_record is not None
        assert file_record.id == sample_file_record.id
        assert file_record.cid == sample_file_record.cid
    
    def test_get_file_by_id_not_found(self, db_service):
        """Test file retrieval for non-existent ID."""
        file_record = db_service.get_file_by_id(99999)
        
        assert file_record is None
    
    def test_list_files_default_pagination(self, db_service, multiple_file_records):
        """Test file listing with default pagination."""
        files, total = db_service.list_files()
        
        assert total == len(multiple_file_records)
        assert len(files) <= 50  # Default limit
        assert all(isinstance(f, FileRecord) for f in files)
    
    def test_list_files_custom_pagination(self, db_service, multiple_file_records):
        """Test file listing with custom pagination."""
        files, total = db_service.list_files(skip=1, limit=2)
        
        assert total == len(multiple_file_records)
        assert len(files) <= 2
        # Should skip first record
        if len(files) > 0:
            assert files[0].id != multiple_file_records[0].id
    
    def test_list_files_empty_database(self, db_service):
        """Test file listing with empty database."""
        files, total = db_service.list_files()
        
        assert total == 0
        assert len(files) == 0
    
    def test_search_files_by_filename(self, db_service, multiple_file_records):
        """Test file search by filename."""
        search_query = "test_file_1"
        files, total = db_service.search_files(search_query)
        
        assert total >= 0
        # All returned files should match the search query
        for file_record in files:
            assert search_query.lower() in file_record.filename.lower() or \
                   (file_record.description and search_query.lower() in file_record.description.lower())
    
    def test_search_files_by_description(self, db_service, multiple_file_records):
        """Test file search by description."""
        search_query = "unit tests"
        files, total = db_service.search_files(search_query)
        
        assert total >= 0
        # Check that search works (at least some files should match)
        if total > 0:
            found_match = False
            for file_record in files:
                if file_record.description and search_query.lower() in file_record.description.lower():
                    found_match = True
                    break
            assert found_match or any(search_query.lower() in f.filename.lower() for f in files)
    
    def test_search_files_no_results(self, db_service, multiple_file_records):
        """Test file search with no matching results."""
        search_query = "nonexistent_file_xyz"
        files, total = db_service.search_files(search_query)
        
        assert total == 0
        assert len(files) == 0
    
    def test_search_files_with_pagination(self, db_service, multiple_file_records):
        """Test file search with pagination."""
        search_query = "test"  # Should match multiple files
        files, total = db_service.search_files(search_query, skip=1, limit=2)
        
        assert len(files) <= 2
        # Total should reflect all matching files, not just returned ones
        assert total >= len(files)
    
    def test_update_file_record_success(self, db_service, sample_file_record):
        """Test successful file record update."""
        updates = {
            "filename": "updated_filename.txt",
            "description": "Updated description",
            "tags": '["updated", "test"]'
        }
        
        updated_record = db_service.update_file_record(sample_file_record.cid, updates)
        
        assert updated_record is not None
        assert updated_record.filename == "updated_filename.txt"
        assert updated_record.description == "Updated description"
        assert updated_record.tags == '["updated", "test"]'
        # CID should remain unchanged
        assert updated_record.cid == sample_file_record.cid
    
    def test_update_file_record_not_found(self, db_service):
        """Test updating non-existent file record."""
        updates = {"filename": "new_name.txt"}
        
        updated_record = db_service.update_file_record("QmNonExistentCID", updates)
        
        assert updated_record is None
    
    def test_update_file_record_partial(self, db_service, sample_file_record):
        """Test partial file record update."""
        original_filename = sample_file_record.filename
        updates = {"description": "Only description updated"}
        
        updated_record = db_service.update_file_record(sample_file_record.cid, updates)
        
        assert updated_record is not None
        assert updated_record.description == "Only description updated"
        # Filename should remain unchanged
        assert updated_record.filename == original_filename
    
    def test_delete_file_record_success(self, db_service, sample_file_record):
        """Test successful file record deletion."""
        result = db_service.delete_file_record(sample_file_record.cid)
        
        assert result is True
        
        # Verify record is deleted
        deleted_record = db_service.get_file_by_cid(sample_file_record.cid)
        assert deleted_record is None
    
    def test_delete_file_record_not_found(self, db_service):
        """Test deleting non-existent file record."""
        result = db_service.delete_file_record("QmNonExistentCID")
        
        assert result is False
    
    def test_get_file_count(self, db_service, multiple_file_records):
        """Test getting total file count."""
        count = db_service.get_file_count()
        
        assert count == len(multiple_file_records)
    
    def test_get_file_count_empty_database(self, db_service):
        """Test getting file count from empty database."""
        count = db_service.get_file_count()
        
        assert count == 0
    
    def test_get_total_size(self, db_service, multiple_file_records):
        """Test getting total storage size."""
        total_size = db_service.get_total_size()
        
        expected_size = sum(record.size for record in multiple_file_records)
        assert total_size == expected_size
    
    def test_get_total_size_empty_database(self, db_service):
        """Test getting total size from empty database."""
        total_size = db_service.get_total_size()
        
        assert total_size == 0


class TestServiceIntegration:
    """Test integration between IPFS and database services."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_upload_integration(self, mock_ipfs_service, db_service, mock_upload_file):
        """Test complete file upload workflow."""
        # 1. Add file to IPFS
        ipfs_result = await mock_ipfs_service.add_file(mock_upload_file)
        
        # 2. Store metadata in database
        file_record = db_service.create_file_record(
            cid=ipfs_result["cid"],
            filename=ipfs_result["filename"],
            original_filename=ipfs_result["filename"],
            content_type=ipfs_result["content_type"],
            size=ipfs_result["size"],
            uploader_ip="127.0.0.1"
        )
        
        # 3. Verify integration
        assert file_record.cid == ipfs_result["cid"]
        assert file_record.filename == ipfs_result["filename"]
        
        # 4. Retrieve and verify
        retrieved_record = db_service.get_file_by_cid(ipfs_result["cid"])
        assert retrieved_record is not None
        assert retrieved_record.cid == ipfs_result["cid"]
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_deletion_integration(self, mock_ipfs_service, db_service, sample_file_record):
        """Test complete file deletion workflow."""
        # 1. Unpin from IPFS
        unpin_result = await mock_ipfs_service.unpin_file(sample_file_record.cid)
        assert unpin_result is True
        
        # 2. Delete from database
        delete_result = db_service.delete_file_record(sample_file_record.cid)
        assert delete_result is True
        
        # 3. Verify deletion
        deleted_record = db_service.get_file_by_cid(sample_file_record.cid)
        assert deleted_record is None
    
    @pytest.mark.integration
    def test_search_and_retrieval_integration(self, db_service, multiple_file_records):
        """Test search and retrieval integration."""
        # 1. Search for files
        files, total = db_service.search_files("test")
        assert total > 0
        
        # 2. Get specific file info
        if len(files) > 0:
            first_file = files[0]
            retrieved_file = db_service.get_file_by_cid(first_file.cid)
            
            assert retrieved_file is not None
            assert retrieved_file.cid == first_file.cid
            assert retrieved_file.filename == first_file.filename


# Performance and stress tests
@pytest.mark.slow
class TestServicePerformance:
    """Performance tests for services."""
    
    def test_database_bulk_operations(self, db_service, test_db):
        """Test database performance with bulk operations."""
        # Create multiple records
        records = []
        for i in range(100):
            record = db_service.create_file_record(
                cid=f"QmBulkTest{i:010d}",
                filename=f"bulk_test_{i}.txt",
                original_filename=f"bulk_test_{i}.txt",
                content_type="text/plain",
                size=1024 * i,
                uploader_ip="127.0.0.1"
            )
            records.append(record)
        
        # Test listing performance
        files, total = db_service.list_files(limit=100)
        assert total >= 100
        assert len(files) <= 100
        
        # Test search performance
        search_files, search_total = db_service.search_files("bulk_test")
        assert search_total >= 100
    
    @pytest.mark.asyncio
    async def test_ipfs_concurrent_operations(self, mock_ipfs_service):
        """Test IPFS service with concurrent operations."""
        # Create multiple mock files
        mock_files = []
        for i in range(10):
            mock_file = Mock()
            mock_file.filename = f"concurrent_test_{i}.txt"
            mock_file.content_type = "text/plain"
            mock_file.size = 1024
            mock_file.read = AsyncMock(return_value=f"Content {i}".encode())
            mock_file.seek = AsyncMock()
            mock_files.append(mock_file)
        
        # Test concurrent uploads
        tasks = [mock_ipfs_service.add_file(mock_file) for mock_file in mock_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed (mocked)
        assert len(results) == 10
        for result in results:
            assert not isinstance(result, Exception)
            assert "cid" in result
