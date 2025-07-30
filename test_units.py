#!/usr/bin/env python3
"""
Unit test runner for IPFS package.
Runs the full pytest suite with proper timeout handling.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_tests(timeout=300):
    """Run pytest with timeout protection."""
    print("🧪 Running unit tests...")
    start_time = time.time()

    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "-v", "--tb=short"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        duration = time.time() - start_time
        success = result.returncode == 0
        output = result.stdout + result.stderr

        if success:
            # Extract test summary
            lines = output.split("\n")
            summary_lines = [
                line
                for line in lines
                if "passed" in line
                and (
                    "warning" in line
                    or "failed" in line
                    or line.strip().endswith("passed")
                )
            ]
            summary = summary_lines[-1] if summary_lines else "Tests completed"

            print(f"✅ All tests passed: {summary}")
            print(f"⏱️ Duration: {duration:.2f}s")
            return True, summary
        else:
            print(f"❌ Tests failed (exit code: {result.returncode})")
            print(f"⏱️ Duration: {duration:.2f}s")

            # Show key failure info
            error_lines = [
                line
                for line in output.split("\n")
                if "FAILED" in line or "ERROR" in line
            ]
            if error_lines:
                print("Key failures:")
                for line in error_lines[:5]:  # Show first 5 failures
                    print(f"  {line}")

            return False, f"Tests failed: {result.returncode}"

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"⏰ Tests timed out after {duration:.2f}s")
        return False, f"Tests timed out after {timeout}s"
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 Test execution failed: {e}")
        return False, str(e)


def main():
    """Run unit tests."""
    print("🧪 IPFS Package Unit Tests")
    print("=" * 35)

    success, message = run_tests()

    print("\n" + "=" * 35)
    if success:
        print("🎉 Unit tests passed!")
        return True
    else:
        print(f"⚠️ Unit tests failed: {message}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
