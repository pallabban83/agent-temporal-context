#!/usr/bin/env python3
"""
Test Runner for Temporal Context RAG Agent

This script runs all tests in the test suite with proper configuration.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py -v                 # Verbose output
    python run_tests.py -k test_name       # Run specific test
    python run_tests.py --markers          # List all test markers
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the test suite using pytest."""

    # Ensure we're in the backend directory
    backend_dir = Path(__file__).parent

    print("=" * 80)
    print("Temporal Context RAG Agent - Test Suite")
    print("=" * 80)
    print(f"Backend directory: {backend_dir}")
    print(f"Test directory: {backend_dir / 'test'}")
    print("=" * 80)

    # Build pytest command
    pytest_args = [
        sys.executable, "-m", "pytest",
        str(backend_dir / "test"),
    ]

    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])

    print(f"\nRunning: {' '.join(pytest_args)}\n")
    print("=" * 80)

    # Run pytest
    try:
        result = subprocess.run(pytest_args, cwd=backend_dir)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("\n❌ ERROR: pytest not found!")
        print("\nPlease install pytest:")
        print("    pip install pytest pytest-cov")
        print("\nOr install all dependencies:")
        print("    pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(130)

if __name__ == "__main__":
    main()
