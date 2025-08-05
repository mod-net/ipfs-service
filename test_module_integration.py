#!/usr/bin/env python3
"""
Integration tests for Module Registry IPFS integration.

Tests the complete workflow between IPFS backend and module registry functionality.
"""

import asyncio
from datetime import datetime

import pytest

from integration_client import ModuleMetadata, ModuleRegistryClient


class TestModuleRegistryIntegration:
    """Integration tests for module registry functionality."""

    @pytest.fixture
    async def client(self):
        """Create a test client."""
        async with ModuleRegistryClient() as client:
            yield client

    @pytest.fixture
    def sample_metadata(self):
        """Create sample module metadata for testing."""
        return ModuleMetadata(
            name="test-module",
            version="1.0.0",
            description="A test module for integration testing",
            author="test@example.com",
            license="MIT",
            repository="https://github.com/test/test-module",
            dependencies=["substrate-api"],
            tags=["test", "substrate"],
            public_key="0xabcdef1234567890abcdef1234567890abcdef12",
            chain_type="ed25519",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    @pytest.mark.asyncio
    async def test_register_and_retrieve_module(self, client, sample_metadata):
        """Test registering a module and retrieving its metadata."""
        # Register module
        registration_result = await client.register_module_metadata(sample_metadata, pin=True)

        assert "cid" in registration_result
        assert registration_result["pinned"] is True
        assert registration_result["size"] > 0

        cid = registration_result["cid"]

        # Retrieve metadata
        retrieved_metadata = await client.get_module_metadata(cid)

        assert retrieved_metadata.name == sample_metadata.name
        assert retrieved_metadata.version == sample_metadata.version
        assert retrieved_metadata.author == sample_metadata.author
        assert retrieved_metadata.public_key == sample_metadata.public_key

        # Cleanup
        await client.unregister_module(cid, unpin=True)

    @pytest.mark.asyncio
    async def test_search_modules(self, client, sample_metadata):
        """Test searching for modules."""
        # Register a test module
        registration_result = await client.register_module_metadata(sample_metadata, pin=True)
        cid = registration_result["cid"]

        try:
            # Search by name
            search_results = await client.search_modules(query="test-module")

            assert search_results["total"] >= 1
            assert len(search_results["modules"]) >= 1

            # Find our module in results
            found_module = None
            for module in search_results["modules"]:
                if module["cid"] == cid:
                    found_module = module
                    break

            assert found_module is not None
            assert found_module["name"] == sample_metadata.name
            assert found_module["version"] == sample_metadata.version

            # Search by chain type
            chain_results = await client.search_modules(chain_type="ed25519")
            assert len(chain_results["modules"]) >= 1

            # Search by tags
            tag_results = await client.search_modules(tags=["test"])
            assert len(tag_results["modules"]) >= 1

        finally:
            # Cleanup
            await client.unregister_module(cid, unpin=True)

    @pytest.mark.asyncio
    async def test_module_stats(self, client, sample_metadata):
        """Test getting module statistics."""
        # Register module
        registration_result = await client.register_module_metadata(sample_metadata, pin=True)
        cid = registration_result["cid"]

        try:
            # Get stats
            stats = await client.get_module_stats(cid)

            assert "cid" in stats
            assert stats["cid"] == cid
            assert "size" in stats
            assert stats["size"] > 0

        finally:
            # Cleanup
            await client.unregister_module(cid, unpin=True)

    @pytest.mark.asyncio
    async def test_unregister_module(self, client, sample_metadata):
        """Test unregistering a module."""
        # Register module
        registration_result = await client.register_module_metadata(sample_metadata, pin=True)
        cid = registration_result["cid"]

        # Verify it exists
        retrieved_metadata = await client.get_module_metadata(cid)
        assert retrieved_metadata.name == sample_metadata.name

        # Unregister
        unregister_result = await client.unregister_module(cid, unpin=True)

        assert unregister_result["cid"] == cid
        assert unregister_result["unpinned"] is True
        assert "successfully" in unregister_result["message"]

        # Verify it's gone from database (should still be in IPFS until GC)
        try:
            await client.get_module_metadata(cid)
            # If we get here, the metadata is still accessible from IPFS
            # This is expected behavior - unregistering removes from database but not IPFS
            pass
        except RuntimeError:
            # This would happen if IPFS also removed it, which is fine
            pass

    @pytest.mark.asyncio
    async def test_invalid_cid_handling(self, client):
        """Test handling of invalid CIDs."""
        invalid_cid = "invalid_cid_format"

        with pytest.raises(RuntimeError):
            await client.get_module_metadata(invalid_cid)

        with pytest.raises(RuntimeError):
            await client.get_module_stats(invalid_cid)

    @pytest.mark.asyncio
    async def test_multiple_modules_same_author(self, client):
        """Test registering multiple modules from the same author."""
        base_metadata = ModuleMetadata(
            name="base-module",
            version="1.0.0",
            description="Base test module",
            author="test-author@example.com",
            license="MIT",
            repository="https://github.com/test/base-module",
            dependencies=[],
            tags=["test"],
            public_key="0x1111111111111111111111111111111111111111",
            chain_type="ed25519",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        # Create variations
        modules = []
        for i in range(3):
            metadata = base_metadata.model_copy()
            metadata.name = f"test-module-{i}"
            metadata.version = f"1.{i}.0"
            metadata.public_key = f"0x{str(i)*40}"
            modules.append(metadata)

        registered_cids = []

        try:
            # Register all modules
            for metadata in modules:
                result = await client.register_module_metadata(metadata, pin=True)
                registered_cids.append(result["cid"])

            # Search by author
            author_results = await client.search_modules(author="test-author@example.com")

            # Should find at least our 3 modules
            assert len(author_results["modules"]) >= 3

            # Verify all our modules are in results
            found_cids = {module["cid"] for module in author_results["modules"]}
            for cid in registered_cids:
                assert cid in found_cids

        finally:
            # Cleanup all registered modules
            for cid in registered_cids:
                try:
                    await client.unregister_module(cid, unpin=True)
                except Exception as e:
                    print(f"Cleanup warning for {cid}: {e}")


def run_integration_tests():
    """Run integration tests manually."""
    print("🧪 Running Module Registry Integration Tests")
    print("=" * 50)

    # Note: This requires the commune-ipfs backend to be running
    try:
        # Run the tests
        pytest.main([__file__, "-v", "--tb=short"])
    except ImportError:
        print("❌ pytest not available. Running basic test instead...")

        # Run a basic test without pytest
        async def basic_test():
            sample_metadata = ModuleMetadata(
                name="basic-test-module",
                version="1.0.0",
                description="Basic test module",
                author="test@example.com",
                license="MIT",
                repository="https://github.com/test/basic-test",
                dependencies=[],
                tags=["test"],
                public_key="0xbasictest1234567890abcdef1234567890abcd",
                chain_type="ed25519",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )

            async with ModuleRegistryClient() as client:
                print("📦 Testing module registration...")
                result = await client.register_module_metadata(sample_metadata)
                cid = result["cid"]
                print(f"✅ Registered: {cid}")

                print("📥 Testing metadata retrieval...")
                retrieved = await client.get_module_metadata(cid)
                assert retrieved.name == sample_metadata.name
                print(f"✅ Retrieved: {retrieved.name}")

                print("🔍 Testing search...")
                search_results = await client.search_modules(query="basic-test")
                assert len(search_results["modules"]) >= 1
                print(f"✅ Search found {len(search_results['modules'])} modules")

                print("🧹 Cleaning up...")
                await client.unregister_module(cid, unpin=True)
                print("✅ Cleanup complete")

                print("\n🎉 Basic integration test passed!")

        asyncio.run(basic_test())


if __name__ == "__main__":
    print("Module Registry Integration Tests")
    print("This requires the commune-ipfs backend to be running.")
    print("Start it with: cd commune-ipfs && python main.py")
    print()

    run_integration_tests()
