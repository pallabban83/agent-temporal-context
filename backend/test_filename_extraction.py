"""
Test script for filename date extraction functionality.

This script tests the extract_date_from_filename method with various filename patterns.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from temporal_embeddings import TemporalEmbeddingHandler


def test_filename_extraction():
    """Test filename date extraction with various patterns."""

    # Initialize handler (using dummy values since we only need the extraction method)
    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Test cases: (filename, expected_result, description)
    test_cases = [
        # Full date patterns
        ("Q1_2023_Earnings.pdf", "Q1 2023", "Fiscal quarter with year"),
        ("2023-12-31-Report.pdf", "2023-12-31", "ISO date format"),
        ("Annual_Report_FY2023.pdf", "2023", "Fiscal year format"),
        ("Summary_2023_01_15.pdf", "2023-01-15", "Date with underscores"),
        ("20231231_Summary.pdf", "2023-12-31", "Compact date format"),
        ("12-31-2023-Report.pdf", "2023-12-31", "US date format"),
        ("January 07, 2025.pdf", "2025-01-07", "Full month with day and comma-space"),
        ("January 07, 2023.pdf", "2023-01-07", "Full month name with day (comma-space)"),
        ("December 24,2023.pdf", "2023-12-24", "Full month name with day (comma-no space)"),
        ("March 1, 2024.pdf", "2024-03-01", "Single digit day with comma-space"),
        ("November 9,2022.pdf", "2022-11-09", "Single digit day with comma-no space"),
        ("February 15 2023.pdf", "2023-02-15", "Full month name with day (space only)"),

        # Quarter patterns
        ("Q2-2024-Financials.pdf", "Q2 2024", "Quarter with dash"),
        ("2024Q3_Report.pdf", "Q3 2024", "Year-quarter format"),
        ("Q4_FY_2023.pdf", "Q4 2023", "Quarter with FY"),
        ("first_quarter_2024.pdf", "Q1 2024", "Written quarter"),
        ("JBHT_Q4_2024_Earnings_Release_and_Schedules.pdf", "Q4 2024", "Real-world earnings release filename"),

        # Month-year patterns
        ("January_2023_Report.pdf", "2023-01", "Full month name"),
        ("Jan2024Summary.pdf", "2024-01", "Abbreviated month"),
        ("2023-05-Report.pdf", "2023-05", "Year-month numeric"),
        ("December_2024.pdf", "2024-12", "Month and year"),

        # Year only patterns
        ("Annual_2023.pdf", "2023", "Year only"),
        ("FY2024_Budget.pdf", "2024", "Fiscal year"),
        ("FY23_Report.pdf", "2023", "Short fiscal year"),

        # No date patterns
        ("random_file.pdf", None, "No date in filename"),
        ("report.pdf", None, "Simple filename"),
        ("", None, "Empty filename"),
    ]

    print("=" * 80)
    print("FILENAME DATE EXTRACTION TEST")
    print("=" * 80)
    print()

    passed = 0
    failed = 0

    for filename, expected, description in test_cases:
        try:
            result = handler.extract_date_from_filename(filename)

            # Check if result matches expected
            if result == expected:
                status = "✓ PASS"
                passed += 1
            else:
                status = "✗ FAIL"
                failed += 1

            print(f"{status} | {description}")
            print(f"     Filename: {filename}")
            print(f"     Expected: {expected}")
            print(f"     Got:      {result}")
            print()

        except Exception as e:
            print(f"✗ ERROR | {description}")
            print(f"     Filename: {filename}")
            print(f"     Error: {str(e)}")
            print()
            failed += 1

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_filename_extraction()
    sys.exit(0 if success else 1)
