#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for Temporal Context RAG Agent

Runs all test scripts with proper Python path configuration.
Tests are organized by category.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict

# Setup paths
BACKEND_DIR = Path(__file__).parent
SRC_DIR = BACKEND_DIR / 'src'
TEST_DIR = BACKEND_DIR / 'test'

# Add src to Python path
sys.path.insert(0, str(SRC_DIR))


class TestSuite:
    """Manages and runs the test suite."""

    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0

    def run_test_script(self, test_file: Path, category: str) -> bool:
        """Run a single test script and capture results."""
        self.total_tests += 1

        print(f"\n{'='*80}")
        print(f"Running: {test_file.name} ({category})")
        print(f"{'='*80}")

        try:
            # Run the test script with src in Python path
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=BACKEND_DIR,
                capture_output=False,
                env={**os.environ, 'PYTHONPATH': str(SRC_DIR)},
                timeout=60
            )

            success = result.returncode == 0

            if success:
                self.passed_tests += 1
                status = "✓ PASSED"
            else:
                self.failed_tests += 1
                status = "✗ FAILED"

            self.results.append({
                'name': test_file.name,
                'category': category,
                'status': status,
                'success': success
            })

            print(f"\n{status}: {test_file.name}")
            return success

        except subprocess.TimeoutExpired:
            self.failed_tests += 1
            self.results.append({
                'name': test_file.name,
                'category': category,
                'status': "✗ TIMEOUT",
                'success': False
            })
            print(f"\n✗ TIMEOUT: {test_file.name}")
            return False

        except Exception as e:
            self.failed_tests += 1
            self.results.append({
                'name': test_file.name,
                'category': category,
                'status': f"✗ ERROR: {e}",
                'success': False
            })
            print(f"\n✗ ERROR: {test_file.name} - {e}")
            return False

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUITE SUMMARY")
        print("="*80)

        # Group by category
        categories: Dict[str, List] = {}
        for result in self.results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(result)

        # Print by category
        for category, tests in sorted(categories.items()):
            print(f"\n{category}:")
            for test in tests:
                print(f"  {test['status']:20} {test['name']}")

        # Overall stats
        print("\n" + "="*80)
        print(f"Total tests: {self.total_tests}")
        print(f"✓ Passed:    {self.passed_tests}")
        print(f"✗ Failed:    {self.failed_tests}")
        print("="*80)

        if self.failed_tests == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n❌ {self.failed_tests} test(s) failed")
            return False


def main():
    """Run all tests."""
    print("="*80)
    print("TEMPORAL CONTEXT RAG AGENT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Backend directory: {BACKEND_DIR}")
    print(f"Source directory:  {SRC_DIR}")
    print(f"Test directory:    {TEST_DIR}")

    suite = TestSuite()

    # Define test categories and files
    test_categories = {
        'Date Normalization Tests': [
            'test_ordinal_fix.py',
            'test_abbreviated_months.py',
            'test_temporal_normalization.py',
            'test_filename_extraction.py',
        ],
        'GCS Import Tests': [
            'test_gcs_import_dates.py',
            'test_metadata_creation.py',
        ],
        'Integration Tests': [
            'test_temporal_embedding_integration.py',
            'test_query_temporal_flow.py',
            'test_jbht_example.py',
        ],
        'Validation Tests': [
            'test_bbox_validation.py',
        ],
    }

    # Run tests by category
    for category, test_files in test_categories.items():
        print(f"\n\n{'#'*80}")
        print(f"# {category}")
        print(f"{'#'*80}")

        for test_file_name in test_files:
            test_file = TEST_DIR / test_file_name
            if test_file.exists():
                suite.run_test_script(test_file, category)
            else:
                print(f"\n⚠️  SKIPPED: {test_file_name} (file not found)")

    # Print summary
    all_passed = suite.print_summary()

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        sys.exit(130)
