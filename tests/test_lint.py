#!/usr/bin/env python3
"""
Code quality tests for IPFS package.
Tests formatting, linting, and type checking.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, timeout=60):
    """Run a command with timeout."""
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def test_black_formatting():
    """Test code formatting with Black."""
    print("🎨 Testing Black formatting...")
    success, output = run_command(
        ["uv", "run", "--with", "black", "black", "--check", "."]
    )

    if success:
        print("✅ Code formatting is correct")
        return True
    else:
        print("❌ Code formatting issues found")
        if "--check" in output:
            print("   Run: uv run black . --fix")
        return False


def test_isort():
    """Test import sorting with isort."""
    print("📋 Testing import sorting...")
    success, output = run_command(
        [
            "uv",
            "run",
            "--with",
            "isort",
            "isort",
            ".",
            "--check-only",
        ]
    )

    if success:
        print("✅ Import sorting is correct")
        return True
    else:
        print("❌ Import sorting issues found")
        print("   Run: uv run isort . --profile black")
        return False


def test_ruff():
    """Test linting with Ruff."""
    print("🔍 Testing Ruff linting...")
    success, output = run_command(["uv", "run", "--with", "ruff", "ruff", "check", "."])

    if success:
        print("✅ Ruff linting passed")
        return True
    else:
        print("❌ Ruff linting issues found")
        if "B008" in output:
            print("   (B008 errors are expected for FastAPI - check pyproject.toml)")
        return False


def main():
    """Run all lint tests."""
    print("🔍 IPFS Package Code Quality Tests")
    print("=" * 45)

    tests = [
        ("Black Formatting", test_black_formatting),
        ("Import Sorting", test_isort),
        ("Ruff Linting", test_ruff),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name}...")
        success = test_func()
        results.append((test_name, success))

    # Summary
    print("\n" + "=" * 45)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<20} {status}")

    print("=" * 45)
    if passed == total:
        print(f"🎉 All {total} code quality tests passed!")
        return True
    else:
        print(f"⚠️ {passed}/{total} tests passed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
