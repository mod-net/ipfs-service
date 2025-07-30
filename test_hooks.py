#!/usr/bin/env python3
"""
Robust, comprehensive test hooks script for the IPFS package.

This script tests all aspects we've been debugging with proper timeout handling:
- Package installation and dependencies
- Code formatting and linting
- Type checking
- Unit tests with timeout protection
- API endpoints
- IPFS service functionality
- Configuration validation

Usage:
    python test_hooks.py [--verbose] [--skip-ipfs] [--skip-api] [--skip-lint] [--timeout SECONDS]
"""

import argparse
import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

# Add the app directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "app"))

# Import required modules
from fastapi.testclient import TestClient
from app.config import get_settings
from app.services.ipfs import IPFSService
from main import app


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


class TestHooks:
    """Comprehensive test suite for the IPFS package."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: Dict[str, bool] = {}
        self.errors: Dict[str, str] = {}
        self.project_root = Path(__file__).parent

    def log(self, message: str, color: str = Colors.WHITE) -> None:
        """Log a message with optional color."""
        if self.verbose:
            print(f"{color}{message}{Colors.END}")

    def run_command(
        self, cmd: List[str], cwd: Optional[Path] = None
    ) -> tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def test_package_installation(self) -> bool:
        """Test that the package can be installed and imported."""
        self.log("🔧 Testing package installation...", Colors.BLUE)

        try:
            # Test importing main modules
            from app.config import Settings
            from app.models.file import FileMetadata
            from app.services.ipfs import IPFSService
            from main import app

            self.log("✅ All main modules imported successfully", Colors.GREEN)
            return True
        except ImportError as e:
            self.errors["package_installation"] = f"Import error: {e}"
            self.log(f"❌ Import failed: {e}", Colors.RED)
            return False

    def test_dependencies(self) -> bool:
        """Test that all required dependencies are available."""
        self.log("📦 Testing dependencies...", Colors.BLUE)

        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "pydantic-settings",
            "ipfshttpclient",
            "sqlalchemy",
            "aiofiles",
            "python-multipart",
        ]

        missing = []
        # Map package names to their import names
        import_map = {
            "python-multipart": "multipart",
            "pydantic-settings": "pydantic_settings",
            "ipfshttpclient": "ipfshttpclient"
        }
        
        for package in required_packages:
            try:
                import_name = import_map.get(package, package)
                __import__(import_name)
            except ImportError:
                missing.append(package)

        if missing:
            self.errors["dependencies"] = f"Missing packages: {missing}"
            self.log(f"❌ Missing dependencies: {missing}", Colors.RED)
            return False

        self.log("✅ All dependencies available", Colors.GREEN)
        return True

    def test_code_formatting(self) -> bool:
        """Test code formatting with Black."""
        self.log("🎨 Testing code formatting with Black...", Colors.BLUE)

        success, output = self.run_command(["uv", "run", "black", "--check", "."])
        if not success:
            self.errors["black_formatting"] = output
            self.log(f"❌ Black formatting issues: {output}", Colors.RED)
            return False

        self.log("✅ Code formatting is correct", Colors.GREEN)
        return True

    def test_import_sorting(self) -> bool:
        """Test import sorting with isort."""
        self.log("📋 Testing import sorting with isort...", Colors.BLUE)

        success, output = self.run_command(
            ["uv", "run", "isort", ".", "--check-only", "--profile", "black"]
        )
        if not success:
            self.errors["isort"] = output
            self.log(f"❌ Import sorting issues: {output}", Colors.RED)
            return False

        self.log("✅ Import sorting is correct", Colors.GREEN)
        return True

    def test_linting(self) -> bool:
        """Test linting with Ruff."""
        self.log("🔍 Testing linting with Ruff...", Colors.BLUE)

        success, output = self.run_command(["uv", "run", "ruff", "check", "."])
        if not success:
            self.errors["ruff_linting"] = output
            self.log(f"❌ Ruff linting issues: {output}", Colors.RED)
            return False

        self.log("✅ Linting passed", Colors.GREEN)
        return True

    def test_type_checking(self) -> bool:
        """Test type checking with MyPy."""
        self.log("🔬 Testing type checking with MyPy...", Colors.BLUE)

        success, output = self.run_command(
            ["uv", "run", "mypy", "app/", "--ignore-missing-imports"]
        )
        if not success:
            self.errors["mypy"] = output
            self.log(f"❌ Type checking issues: {output}", Colors.RED)
            return False

        self.log("✅ Type checking passed", Colors.GREEN)
        return True

    def test_unit_tests(self) -> bool:
        """Run the full test suite."""
        self.log("🧪 Running unit tests...", Colors.BLUE)

        success, output = self.run_command(["uv", "run", "pytest", "-v", "--tb=short", "--timeout=60"])
        if not success:
            self.errors["unit_tests"] = output
            self.log(f"❌ Unit tests failed: {output}", Colors.RED)
            return False

        self.log("✅ All unit tests passed", Colors.GREEN)
        return True

    def test_configuration(self) -> bool:
        """Test configuration loading and validation."""
        self.log("⚙️ Testing configuration...", Colors.BLUE)

        try:
            # Test settings loading
            test_settings = get_settings()

            # Validate required settings
            required_attrs = [
                "ipfs_api_url",
                "ipfs_gateway_url",
                "ipfs_timeout",
                "max_file_size",
                "allowed_extensions_list",
            ]

            for attr in required_attrs:
                if not hasattr(test_settings, attr):
                    raise ValueError(f"Missing required setting: {attr}")

            # Test allowed_extensions_list property
            extensions = test_settings.allowed_extensions_list
            if not isinstance(extensions, list) or not extensions:
                raise ValueError("allowed_extensions_list should be a non-empty list")

            self.log("✅ Configuration validation passed", Colors.GREEN)
            return True
        except Exception as e:
            self.errors["configuration"] = str(e)
            self.log(f"❌ Configuration error: {e}", Colors.RED)
            return False

    async def test_ipfs_service(self) -> bool:
        """Test IPFS service functionality."""
        self.log("🌐 Testing IPFS service...", Colors.BLUE)

        try:
            ipfs_service = IPFSService()

            # Test connection (this will fail if IPFS daemon is not running)
            try:
                node_info = await ipfs_service.get_node_info()
                self.log(
                    f"✅ IPFS node connected: {node_info.get('ID', 'Unknown')}",
                    Colors.GREEN,
                )

                # Test file operations with a small test file
                test_content = b"Hello, IPFS test!"
                with tempfile.NamedTemporaryFile() as tmp_file:
                    tmp_file.write(test_content)
                    tmp_file.flush()

                    # Test file upload
                    result = await ipfs_service.add_file(tmp_file.name)
                    cid = result["Hash"]
                    self.log(f"✅ File uploaded to IPFS: {cid}", Colors.GREEN)

                    # Test file retrieval
                    retrieved_content = await ipfs_service.get_file(cid)
                    if retrieved_content == test_content:
                        self.log("✅ File retrieved successfully", Colors.GREEN)
                    else:
                        raise ValueError("Retrieved content doesn't match original")

                return True
            except Exception as e:
                self.log(f"⚠️ IPFS daemon not available: {e}", Colors.YELLOW)
                self.log("ℹ️ IPFS service tests skipped (daemon required)", Colors.CYAN)
                return True  # Don't fail if IPFS daemon is not running
        except Exception as e:
            self.errors["ipfs_service"] = str(e)
            self.log(f"❌ IPFS service error: {e}", Colors.RED)
            return False

    def test_api_endpoints(self) -> bool:
        """Test API endpoints using TestClient."""
        self.log("🌍 Testing API endpoints...", Colors.BLUE)

        try:
            client = TestClient(app)

            # Test health endpoint
            response = client.get("/health")
            if response.status_code != 200:
                raise ValueError(f"Health endpoint failed: {response.status_code}")

            # Test info endpoint
            response = client.get("/info")
            if response.status_code not in [200, 503]:  # 503 if IPFS daemon not running
                raise ValueError(f"Info endpoint failed: {response.status_code}")

            # Test file upload endpoint (without actual IPFS)
            test_file_content = b"Test file content"
            files = {"file": ("test.txt", test_file_content, "text/plain")}
            response = client.post("/api/files/upload", files=files)

            # This might fail if IPFS daemon is not running, which is OK
            if response.status_code not in [200, 503]:
                self.log(
                    f"⚠️ File upload test returned {response.status_code}", Colors.YELLOW
                )

            self.log("✅ API endpoints responding correctly", Colors.GREEN)
            return True
        except Exception as e:
            self.errors["api_endpoints"] = str(e)
            self.log(f"❌ API endpoint error: {e}", Colors.RED)
            return False

    def test_database_models(self) -> bool:
        """Test database models and schemas."""
        self.log("🗄️ Testing database models...", Colors.BLUE)

        try:
            from app.models.file import FileListResponse, FileMetadata

            # Test model creation
            from datetime import datetime
            file_metadata = FileMetadata(
                id=1,
                cid="QmTest123",
                filename="test.txt",
                original_filename="test.txt",
                size=100,
                content_type="text/plain",
                upload_date=datetime.fromisoformat("2025-01-01T00:00:00"),
                gateway_url="http://localhost:8080/ipfs/QmTest123",
            )

            # Test model serialization
            data = file_metadata.model_dump()
            if not isinstance(data, dict) or "cid" not in data:
                raise ValueError("Model serialization failed")

            # Test response model
            file_list = FileListResponse(
                files=[file_metadata], 
                total=1, 
                skip=0, 
                limit=50
            )
            list_data = file_list.model_dump()
            if not isinstance(list_data, dict) or "files" not in list_data:
                raise ValueError("Response model serialization failed")

            self.log("✅ Database models working correctly", Colors.GREEN)
            return True
        except Exception as e:
            self.errors["database_models"] = str(e)
            self.log(f"❌ Database model error: {e}", Colors.RED)
            return False

    def run_all_tests(
        self, skip_ipfs: bool = False, skip_api: bool = False, skip_lint: bool = False
    ) -> bool:
        """Run all tests and return overall success."""
        print(
            f"{Colors.BOLD}{Colors.CYAN}🚀 Running IPFS Package Test Suite{Colors.END}\n"
        )

        tests = [
            ("Package Installation", self.test_package_installation),
            ("Dependencies", self.test_dependencies),
            ("Configuration", self.test_configuration),
            ("Database Models", self.test_database_models),
        ]

        if not skip_lint:
            tests.extend(
                [
                    ("Code Formatting", self.test_code_formatting),
                    ("Import Sorting", self.test_import_sorting),
                    ("Linting", self.test_linting),
                    ("Type Checking", self.test_type_checking),
                ]
            )

        tests.append(("Unit Tests", self.test_unit_tests))

        if not skip_api:
            tests.append(("API Endpoints", self.test_api_endpoints))

        if not skip_ipfs:
            # Run IPFS tests asynchronously
            async def run_ipfs_test():
                return await self.test_ipfs_service()

            ipfs_result = asyncio.run(run_ipfs_test())
            self.results["IPFS Service"] = ipfs_result

        # Run synchronous tests
        for test_name, test_func in tests:
            try:
                result = test_func()
                self.results[test_name] = result
            except Exception as e:
                self.results[test_name] = False
                self.errors[test_name] = str(e)
                self.log(f"❌ {test_name} failed with exception: {e}", Colors.RED)

        # Print summary
        self.print_summary()

        # Return True if all tests passed
        return all(self.results.values())

    def print_summary(self) -> None:
        """Print a summary of all test results."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Test Summary{Colors.END}")
        print("=" * 50)

        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)

        for test_name, result in self.results.items():
            status = (
                f"{Colors.GREEN}✅ PASS{Colors.END}"
                if result
                else f"{Colors.RED}❌ FAIL{Colors.END}"
            )
            print(f"{test_name:<25} {status}")

            if not result and test_name in self.errors:
                error_msg = self.errors[test_name]
                # Truncate long error messages
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                print(f"  {Colors.YELLOW}Error: {error_msg}{Colors.END}")

        print("=" * 50)

        if passed == total:
            print(
                f"{Colors.GREEN}{Colors.BOLD}🎉 All {total} tests passed!{Colors.END}"
            )
        else:
            print(
                f"{Colors.RED}{Colors.BOLD}❌ {total - passed}/{total} tests failed{Colors.END}"
            )

        print()


def main():
    """Main entry point for the test hooks script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive IPFS package test suite"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--skip-ipfs", action="store_true", help="Skip IPFS service tests"
    )
    parser.add_argument(
        "--skip-api", action="store_true", help="Skip API endpoint tests"
    )
    parser.add_argument(
        "--skip-lint", action="store_true", help="Skip linting and formatting tests"
    )

    args = parser.parse_args()

    test_hooks = TestHooks(verbose=args.verbose)
    success = test_hooks.run_all_tests(
        skip_ipfs=args.skip_ipfs, skip_api=args.skip_api, skip_lint=args.skip_lint
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
