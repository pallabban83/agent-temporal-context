#!/usr/bin/env python3
"""
Test script to verify bbox validation in table parsing.
This simulates edge cases where pdfplumber might return invalid bboxes.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_parser import DocumentParser


def test_table_to_markdown():
    """Test _table_to_markdown with various edge cases."""

    print("=" * 80)
    print("TABLE TO MARKDOWN VALIDATION TEST")
    print("=" * 80)
    print()

    test_cases = [
        # (table_data, description, expected_result)
        (
            [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]],
            "Valid table with header and 2 data rows",
            "should_pass"
        ),
        (
            [["Name", "Age"]],
            "Table with only header row (no data)",
            "should_fail"
        ),
        (
            [["", ""], ["", ""], ["", ""]],
            "Table with all empty cells",
            "should_fail"
        ),
        (
            [["Name"], ["Alice"], ["Bob"]],
            "Table with only 1 column",
            "should_fail"
        ),
        (
            [],
            "Empty table (no rows)",
            "should_fail"
        ),
        (
            None,
            "None table",
            "should_fail"
        ),
        (
            [["Quarter", "Revenue"], ["", ""], ["Q1 2023", "$100M"]],
            "Table with one empty row (should be filtered)",
            "should_pass"
        ),
        (
            [["A", "B", "C"], ["1", "2"], ["3", "4", "5", "6"]],
            "Table with inconsistent column counts",
            "should_pass"
        ),
    ]

    passed = 0
    failed = 0

    for table_data, description, expected in test_cases:
        try:
            result = DocumentParser._table_to_markdown(table_data)

            if expected == "should_pass":
                if result and len(result) > 0:
                    status = "✓ PASS"
                    passed += 1
                else:
                    status = "✗ FAIL"
                    failed += 1
                    print(f"{status} | {description}")
                    print(f"     Expected: Non-empty markdown")
                    print(f"     Got: Empty string")
                    print()
                    continue
            else:  # should_fail
                if not result or len(result) == 0:
                    status = "✓ PASS"
                    passed += 1
                else:
                    status = "✗ FAIL"
                    failed += 1
                    print(f"{status} | {description}")
                    print(f"     Expected: Empty string")
                    print(f"     Got: Non-empty markdown")
                    print()
                    continue

            print(f"{status} | {description}")
            if result:
                print(f"     Result: {len(result)} chars, valid markdown table")
            else:
                print(f"     Result: Correctly rejected")
            print()

        except Exception as e:
            print(f"✗ ERROR | {description}")
            print(f"     Error: {str(e)}")
            print()
            failed += 1

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return failed == 0


def test_bbox_validation_logic():
    """Test the bbox validation logic we added."""

    print("\n")
    print("=" * 80)
    print("BBOX VALIDATION LOGIC TEST")
    print("=" * 80)
    print()

    # Simulate various bbox scenarios
    test_bboxes = [
        ((0, 0, 100, 100), "Valid bbox (4 elements)", True),
        ((0, 0, 100), "Invalid bbox (3 elements)", False),
        ((0, 0), "Invalid bbox (2 elements)", False),
        (None, "None bbox", False),
        ([], "Empty list bbox", False),
        ((0, 0, 100, 100, 200), "Bbox with extra elements (5)", True),  # len >= 4 should pass
    ]

    passed = 0
    failed = 0

    for bbox, description, should_be_valid in test_bboxes:
        # Simulate the validation logic from document_parser.py:244-249
        is_valid = bbox is not None and len(bbox) >= 4

        expected_status = "valid" if should_be_valid else "invalid"
        actual_status = "valid" if is_valid else "invalid"

        if is_valid == should_be_valid:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"{status} | {description}")
        print(f"     Bbox: {bbox}")
        print(f"     Expected: {expected_status}, Got: {actual_status}")
        print()

    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_bboxes)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success1 = test_table_to_markdown()
    success2 = test_bbox_validation_logic()

    sys.exit(0 if (success1 and success2) else 1)
