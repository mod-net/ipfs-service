#!/usr/bin/env python3
"""
Master test runner for IPFS package.
Runs all test categories with proper organization and reporting.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_test_script(script_name):
    """Run a test script and return success status and output."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        return False, f"Script {script_name} not found"

    try:
        result = subprocess.run(
            ["uv", "run", "python", script_name],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=300,
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output

    except subprocess.TimeoutExpired:
        return False, "Script timed out"
    except Exception as e:
        return False, str(e)


def main():
    """Run all test categories."""
    parser = argparse.ArgumentParser(description="Run all IPFS package tests")
    parser.add_argument("--skip-lint", action="store_true", help="Skip linting tests")
    parser.add_argument("--skip-units", action="store_true", help="Skip unit tests")
    parser.add_argument("--core-only", action="store_true", help="Run only core tests")

    args = parser.parse_args()

    print("🚀 IPFS Package Complete Test Suite")
    print("=" * 50)

    test_categories = [
        ("Core Functionality", "test_core.py", False),  # Always run
        ("Code Quality", "test_lint.py", args.skip_lint or args.core_only),
        ("Unit Tests", "test_units.py", args.skip_units or args.core_only),
    ]

    results = []
    total_start = time.time()

    for category_name, script_name, skip in test_categories:
        if skip:
            print(f"\n⏭️ Skipping {category_name}")
            continue

        print(f"\n🔄 Running {category_name}...")
        print("-" * 30)

        start_time = time.time()
        success, output = run_test_script(script_name)
        duration = time.time() - start_time

        results.append((category_name, success, duration))

        if success:
            print(f"✅ {category_name} completed successfully ({duration:.1f}s)")
        else:
            print(f"❌ {category_name} failed ({duration:.1f}s)")
            # Show last few lines of output for context
            lines = output.split("\n")[-10:]
            for line in lines:
                if line.strip():
                    print(f"   {line}")

    # Final summary
    total_duration = time.time() - total_start
    print("\n" + "=" * 50)
    print("📊 FINAL TEST SUMMARY")
    print("=" * 50)

    passed = 0
    for category_name, success, duration in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{category_name:<20} {status} ({duration:.1f}s)")
        if success:
            passed += 1

    total_tests = len(results)
    print("-" * 50)
    print(f"Total: {passed}/{total_tests} test categories passed")
    print(f"Duration: {total_duration:.1f} seconds")

    if passed == total_tests:
        print("\n🎉 ALL TEST CATEGORIES PASSED!")
        print("\n📋 IPFS Package Status: READY ✅")
        return True
    else:
        print(f"\n⚠️ {total_tests - passed} test categories need attention")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
