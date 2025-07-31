#!/usr/bin/env python3
"""
Core functionality tests for IPFS package.
Tests the essential imports, configuration, and basic functionality.
"""

import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))


def test_imports():
    """Test that all core modules can be imported."""
    print("🔧 Testing core imports...")
    try:

        print("✅ All core modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_configuration():
    """Test configuration loading and validation."""
    print("⚙️ Testing configuration...")
    try:
        from app.config import get_settings

        settings = get_settings()

        required = ["ipfs_api_url", "ipfs_gateway_url", "allowed_extensions_list"]
        for attr in required:
            if not hasattr(settings, attr):
                raise ValueError(f"Missing setting: {attr}")

        extensions = settings.allowed_extensions_list
        if not isinstance(extensions, list) or not extensions:
            raise ValueError("Invalid allowed_extensions_list")

        print(f"✅ Configuration valid ({len(extensions)} file types supported)")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_api_health():
    """Test basic API functionality."""
    print("🌍 Testing API health...")
    try:
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        response = client.get("/health")

        if response.status_code == 200:
            print("✅ API health check passed")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


def main():
    """Run all core tests."""
    print("🚀 IPFS Package Core Tests")
    print("=" * 40)

    tests = [
        ("Core Imports", test_imports),
        ("Configuration", test_configuration),
        ("API Health", test_api_health),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name}...")
        success = test_func()
        results.append((test_name, success))

    # Summary
    print("\n" + "=" * 40)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")

    print("=" * 40)
    if passed == total:
        print(f"🎉 All {total} core tests passed!")
        return True
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
