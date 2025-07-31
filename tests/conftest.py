"""
Pytest configuration and fixtures for IPFS Storage System tests.

Provides shared fixtures for database, IPFS service, and API client testing.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, DatabaseService, FileRecord
from app.services.ipfs import IPFSService
from main import app

# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with unique name for each test."""
    import os
    import tempfile
    import uuid

    # Create a unique temporary database file for each test
    temp_dir = tempfile.gettempdir()
    db_name = f"test_commune_ipfs_{uuid.uuid4().hex[:8]}.db"
    db_path = os.path.join(temp_dir, db_name)
    db_url = f"sqlite:///{db_path}"

    # Create engine and tables
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)

    # Create session factory for this test
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create database service and patch its SessionLocal
    db_service = DatabaseService()
    db_service.SessionLocal = TestSessionLocal

    yield db_service

    # Cleanup: close connections and remove database file
    try:
        engine.dispose()
        # Wait a moment for connections to close
        import time

        time.sleep(0.1)
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"Warning: Could not clean up test database {db_path}: {e}")


@pytest.fixture
def db_service(test_db):
    """Create a DatabaseService instance with test database."""
    return test_db


@pytest.fixture
def sample_file_record(test_db):
    """Create a sample file record in the test database."""
    # Use the same database service that the API endpoints will use
    db = test_db.get_session()
    try:
        file_record = FileRecord(
            cid="QmTestCID123456789",
            filename="test_file.txt",
            original_filename="test_file.txt",
            content_type="text/plain",
            size=1024,
            description="Test file for unit tests",
            tags='["test", "sample"]',
            uploader_ip="127.0.0.1",
            is_pinned=1,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        # Ensure the record is detached from the session so it can be used elsewhere
        db.expunge(file_record)
        return file_record
    finally:
        db.close()


@pytest.fixture
def multiple_file_records(test_db):
    """Create multiple sample file records in the test database."""
    db = test_db.get_session()
    try:
        records = []
        for i in range(5):
            file_record = FileRecord(
                cid=f"QmTestCID{i:010d}",
                filename=f"test_file_{i}.txt",
                original_filename=f"test_file_{i}.txt",
                content_type="text/plain",
                size=1024 * (i + 1),
                description=f"Test file {i} for unit tests",
                tags=f'["test", "sample", "file{i}"]',
                uploader_ip="127.0.0.1",
                is_pinned=1 if i % 2 == 0 else 0,
            )
            db.add(file_record)
            records.append(file_record)

        db.commit()
        for record in records:
            db.refresh(record)
        return records
    finally:
        db.close()


@pytest.fixture
def mock_ipfs_service():
    """Create a mock IPFS service for testing."""
    mock_service = Mock(spec=IPFSService)

    # Mock async methods
    mock_service.get_node_info = AsyncMock(
        return_value={"ID": "QmTestNodeID123456789", "Version": "0.14.0"}
    )

    import hashlib
    import uuid

    async def mock_add_file(file):
        # Generate a unique CID based on filename and a random component
        unique_id = f"{file.filename or 'test_file.txt'}_{uuid.uuid4().hex[:8]}"
        cid_hash = hashlib.sha256(unique_id.encode()).hexdigest()[:20]
        unique_cid = f"QmTest{cid_hash}"

        # Read the actual file content to get the real size
        content = await file.read()
        await file.seek(0)  # Reset file pointer

        return {
            "cid": unique_cid,
            "size": len(content),
            "filename": file.filename or "test_file.txt",
            "content_type": file.content_type or "text/plain",
            "ipfs_result": {"Hash": unique_cid},
        }

    mock_service.add_file = AsyncMock(side_effect=mock_add_file)

    # Store uploaded files for retrieval
    mock_service._uploaded_files = {}

    async def mock_get_file(cid):
        # Return test content for any CID
        return b"Test file content"

    mock_service.get_file = AsyncMock(side_effect=mock_get_file)

    mock_service.pin_file = AsyncMock(return_value=True)
    mock_service.unpin_file = AsyncMock(return_value=True)
    mock_service.get_stats = AsyncMock(
        return_value={"total_files": 1, "total_size": 17, "pinned_files": 1}
    )

    # Mock file stats method
    mock_service.get_file_stats = AsyncMock(
        return_value={
            "DataSize": 1024,
            "CumulativeSize": 1024,
            "NumLinks": 0,
            "Type": "file",
        }
    )

    mock_service.list_pinned_files = AsyncMock(return_value=["QmTestCID123456789"])
    mock_service.check_connection = AsyncMock(return_value=True)

    # Mock node info method
    mock_service.get_node_info = AsyncMock(
        return_value={
            "id": "QmTestNodeID123456789",
            "version": "0.14.0",
            "addresses": ["/ip4/127.0.0.1/tcp/4001"],
        }
    )

    # Mock sync methods
    mock_service.get_gateway_url = Mock(
        return_value="http://localhost:8080/ipfs/QmTestCID123456789"
    )
    mock_service.close = Mock()

    return mock_service


@pytest.fixture
def test_client(mock_ipfs_service, test_db):
    """Create a test client with mocked dependencies."""

    # Override the dependencies in the app directly
    from app.api.files import get_database_service, get_ipfs_service

    # Store original dependencies
    original_overrides = app.dependency_overrides.copy()

    # Set up test overrides - these must be functions that return the services
    def get_test_ipfs_service():
        return mock_ipfs_service

    def get_test_database_service():
        return test_db

    app.dependency_overrides[get_ipfs_service] = get_test_ipfs_service
    app.dependency_overrides[get_database_service] = get_test_database_service

    try:
        client = TestClient(app)
        yield client
    finally:
        # Restore original overrides
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def test_file_content():
    """Create test file content for upload tests."""
    return b"This is test file content for unit testing."


@pytest.fixture
def test_file_large():
    """Create large test file content."""
    return b"X" * (1024 * 1024)  # 1MB file


@pytest.fixture
def test_files_directory():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "test.txt").write_text("Test file content")
        (temp_path / "test.json").write_text('{"test": "data"}')
        (temp_path / "test.md").write_text("# Test Markdown")

        # Create binary test file
        (temp_path / "test.bin").write_bytes(b"\x00\x01\x02\x03\x04\x05")

        yield temp_path


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""
    test_content = b"Test file content"
    mock_file = Mock()
    mock_file.filename = "test_file.txt"
    mock_file.content_type = "text/plain"
    mock_file.size = len(test_content)
    mock_file.read = AsyncMock(return_value=test_content)
    mock_file.seek = AsyncMock()
    return mock_file


@pytest.fixture
def api_headers():
    """Create headers for API requests."""
    return {"Content-Type": "application/json", "User-Agent": "pytest-client/1.0"}


@pytest.fixture
def admin_headers():
    """Create headers for admin API requests."""
    settings = get_settings()
    return {
        "Content-Type": "application/json",
        "X-API-Key": settings.admin_api_key,
        "User-Agent": "pytest-admin/1.0",
    }


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically cleanup test files after each test."""
    yield

    # Clean up any test files that might have been created
    test_files = ["test.db", "test.db-journal", "test_upload.txt", "test_download.txt"]

    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "ipfs: marks tests that require IPFS node")


# Test utilities
class TestUtils:
    """Utility functions for tests."""

    @staticmethod
    def create_test_file_data(filename="test.txt", size=1024):
        """Create test file data."""
        return {
            "filename": filename,
            "content": b"X" * size,
            "content_type": "text/plain",
            "size": size,
        }

    @staticmethod
    def assert_file_metadata(metadata, expected_cid, expected_filename):
        """Assert file metadata contains expected values."""
        assert metadata["cid"] == expected_cid
        assert metadata["filename"] == expected_filename
        assert "upload_date" in metadata
        assert "size" in metadata

    @staticmethod
    def assert_api_error(response, status_code, error_message=None):
        """Assert API error response."""
        assert response.status_code == status_code
        if error_message:
            assert error_message in response.json().get("detail", "")


@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtils
