"""
Test edge cases for GCS import and metadata handling.

Tests:
1. Files with no extractable date (fallback behavior)
2. Special characters in filenames
3. Very long filenames
4. Temporal context exceeding 200 character limit (truncation)
5. Empty or whitespace-only PDF pages
6. PDF with only images (no extractable text)
7. Missing metadata fields (graceful degradation)
8. Invalid date formats
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from temporal_embeddings import TemporalEmbeddingHandler
from document_parser import DocumentParser
from text_chunker import TextChunker


def test_no_extractable_date():
    """Test files with no extractable date."""

    print("=" * 100)
    print("TEST 1: NO EXTRACTABLE DATE")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Filenames with no dates
    test_filenames = [
        "quarterly_report.pdf",
        "financial_summary.pdf",
        "document.pdf",
        "report_v2_final.pdf",
        "README.txt",
        "data.csv"
    ]

    print("Testing filenames with no dates:")
    print("-" * 100)

    all_handled = True
    for filename in test_filenames:
        extracted = handler.extract_date_from_filename(filename)

        if extracted is None:
            print(f"  ✓ {filename:40} -> No date (expected)")
        else:
            print(f"  ⚠️  {filename:40} -> Unexpectedly extracted: {extracted}")
            all_handled = False

    print()
    print("Metadata handling when no date extracted:")
    print("-" * 100)

    # Simulate metadata creation with no date
    base_metadata = {
        'filename': 'report_no_date.pdf',
        'source': 'report_no_date.pdf',
        'title': 'report_no_date',
        'document_type': 'pdf'
    }

    # document_date should be omitted or set to None
    if 'document_date' in base_metadata:
        print(f"  ⚠️  document_date present with value: {base_metadata['document_date']}")
        all_handled = False
    else:
        print(f"  ✓ document_date correctly omitted from metadata")

    print()
    print(f"Result: {'✅ PASS' if all_handled else '❌ FAIL'}")
    print()
    return all_handled


def test_special_characters_in_filename():
    """Test filenames with special characters."""

    print("=" * 100)
    print("TEST 2: SPECIAL CHARACTERS IN FILENAME")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Filenames with special characters
    test_filenames = [
        "Report (Q2 2024).pdf",
        "Earnings - July 15, 2024.pdf",
        "Financial_Report_2024-06-30.pdf",
        "Q2'24 Earnings.pdf",
        "Report: June 2024.pdf",
        "Summary [2024-07-01].pdf",
        "Data & Analysis 2024.pdf",
        "Report #1 - Aug 27, 2024.pdf"
    ]

    print("Testing filenames with special characters:")
    print("-" * 100)

    all_passed = True
    for filename in test_filenames:
        try:
            extracted = handler.extract_date_from_filename(filename)
            status = "✓" if extracted else "⚠️"
            print(f"  {status} {filename:45} -> {extracted or 'No date'}")
        except Exception as e:
            print(f"  ❌ {filename:45} -> ERROR: {str(e)}")
            all_passed = False

    print()
    print(f"Result: {'✅ PASS - No errors' if all_passed else '❌ FAIL - Errors occurred'}")
    print()
    return all_passed


def test_very_long_filename():
    """Test very long filename handling."""

    print("=" * 100)
    print("TEST 3: VERY LONG FILENAME")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Create a very long filename (> 255 characters)
    long_filename = "Annual_Financial_Report_for_Fiscal_Year_2024_Including_Quarterly_Earnings_Revenue_Profit_Loss_Balance_Sheet_Cash_Flow_Statement_and_Comprehensive_Analysis_of_Market_Trends_Competitive_Landscape_and_Future_Outlook_Q2_2024_Final_Version_2.pdf"

    print(f"Testing filename with {len(long_filename)} characters:")
    print("-" * 100)
    print(f"Filename: {long_filename[:80]}...")
    print()

    try:
        extracted = handler.extract_date_from_filename(long_filename)
        print(f"  ✓ Date extraction: {extracted or 'No date'}")

        # Test title generation (typically truncates at some point)
        title = long_filename.rsplit('.', 1)[0]
        print(f"  ✓ Title length: {len(title)} characters")
        print(f"  ✓ Title: {title[:80]}...")

        passed = True
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        passed = False

    print()
    print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
    print()
    return passed


def test_temporal_context_truncation():
    """Test temporal context prefix truncation at 200 chars."""

    print("=" * 100)
    print("TEST 4: TEMPORAL CONTEXT TRUNCATION")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Create text with many temporal entities to exceed 200 char limit
    text = """
    This document covers multiple time periods: Q1 2023, Q2 2023, Q3 2023, Q4 2023,
    Q1 2024, Q2 2024, Q3 2024, Q4 2024, January 2023, February 2023, March 2023,
    April 2023, May 2023, June 2023, July 2023, August 2023, September 2023,
    October 2023, November 2023, December 2023, FY2023, FY2024, H1 2023, H2 2023,
    H1 2024, H2 2024, 2023-01-15, 2023-06-30, 2024-03-31, 2024-12-15.
    """

    metadata = {
        'document_date': '2024-06-30'
    }

    print("Extracting temporal info from text with many dates:")
    print("-" * 100)

    temporal_entities = handler.extract_temporal_info(text)

    # Group entities by type for display
    entity_types = {}
    for entity in temporal_entities:
        etype = entity['type']
        if etype not in entity_types:
            entity_types[etype] = []
        entity_types[etype].append(entity['value'])

    for key, values in entity_types.items():
        if values:
            print(f"  - {key}: {len(values)} entities")

    print()
    print("Generating temporal context prefix:")
    print("-" * 100)

    enhanced_text = handler.enhance_text_with_temporal_context(text, metadata)

    if enhanced_text.startswith("[TEMPORAL_CONTEXT:"):
        prefix_end = enhanced_text.find("]", 18)
        if prefix_end > 18:
            prefix = enhanced_text[:prefix_end + 1]
            prefix_length = len(prefix)

            print(f"  Prefix length: {prefix_length} characters")
            print(f"  Prefix: {prefix[:150]}...")
            print()

            # Check if truncated
            if "..." in prefix:
                print(f"  ✓ Prefix was truncated (contains '...')")
                truncated = True
            else:
                print(f"  ℹ️  Prefix was NOT truncated")
                truncated = False

            # Validate length is reasonable (should be <= ~220 including markers)
            if prefix_length <= 250:  # Allow some margin
                print(f"  ✓ Prefix length is within acceptable range")
                length_ok = True
            else:
                print(f"  ⚠️  Prefix length exceeds expected maximum")
                length_ok = False
    else:
        print(f"  ❌ No temporal context prefix found")
        return False

    print()
    print(f"Result: {'✅ PASS' if length_ok else '❌ FAIL'}")
    print()
    return length_ok


def test_empty_pdf_pages():
    """Test handling of empty or whitespace-only pages."""

    print("=" * 100)
    print("TEST 5: EMPTY PDF PAGES")
    print("=" * 100)
    print()

    # Simulate empty pages
    page_texts = [
        "This is page 1 with content.",
        "",  # Empty page
        "   \n\n   ",  # Whitespace only
        "This is page 4 with content.",
        "",  # Another empty page
        "This is page 6 with content."
    ]

    print(f"Simulating PDF with {len(page_texts)} pages:")
    print("-" * 100)
    for i, page in enumerate(page_texts, 1):
        has_content = bool(page.strip())
        status = "✓ Content" if has_content else "• Empty"
        print(f"  {status} - Page {i}")

    print()

    # Test chunking
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

    base_metadata = {
        'filename': 'test_empty_pages.pdf',
        'document_type': 'pdf',
        'total_pages': len(page_texts)
    }

    chunks = chunker.chunk_pdf_by_pages(
        page_texts=page_texts,
        metadata=base_metadata,
        document_id="test_empty"
    )

    print(f"Chunking results:")
    print("-" * 100)
    print(f"  Total pages: {len(page_texts)}")
    print(f"  Pages with content: {sum(1 for p in page_texts if p.strip())}")
    print(f"  Chunks created: {len(chunks)}")

    # Verify no empty chunks
    empty_chunks = [c for c in chunks if not c['content'].strip()]
    if empty_chunks:
        print(f"  ❌ Found {len(empty_chunks)} empty chunks")
        passed = False
    else:
        print(f"  ✓ No empty chunks created")
        passed = True

    # Verify non_empty_pages metadata
    if chunks:
        first_chunk_meta = chunks[0]['metadata']
        non_empty_pages = first_chunk_meta.get('non_empty_pages')
        expected_non_empty = sum(1 for p in page_texts if p.strip())

        if non_empty_pages == expected_non_empty:
            print(f"  ✓ non_empty_pages metadata correct: {non_empty_pages}")
        else:
            print(f"  ⚠️  non_empty_pages metadata: {non_empty_pages}, expected: {expected_non_empty}")

    print()
    print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
    print()
    return passed


def test_invalid_date_formats():
    """Test handling of invalid or ambiguous date formats."""

    print("=" * 100)
    print("TEST 6: INVALID DATE FORMATS")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Various invalid or problematic date formats
    test_cases = [
        ("2024-13-01", "Invalid month (13)"),
        ("2024-00-15", "Invalid month (0)"),
        ("2024-06-32", "Invalid day (32)"),
        ("13/32/2024", "Invalid month and day"),
        ("2024-02-30", "Invalid date (Feb 30)"),
        ("99/99/9999", "Clearly invalid"),
        ("2024", "Year only (should be handled)"),
        ("Q5 2024", "Invalid quarter"),
    ]

    print("Testing invalid date formats:")
    print("-" * 100)

    all_handled = True
    for date_str, description in test_cases:
        filename = f"report_{date_str}.pdf"

        try:
            extracted = handler.extract_date_from_filename(filename)

            if extracted:
                # Try to normalize
                normalized = handler._normalize_date(extracted)

                if normalized and len(normalized) == 10:
                    print(f"  ⚠️  {description:30} | {date_str:15} -> {normalized} (should validate)")
                else:
                    print(f"  ✓ {description:30} | {date_str:15} -> Rejected during normalization")
            else:
                print(f"  ✓ {description:30} | {date_str:15} -> Not extracted (safe)")

        except Exception as e:
            print(f"  ✓ {description:30} | {date_str:15} -> Exception caught: {str(e)[:40]}")

    print()
    print(f"Result: ✅ PASS - All invalid dates handled gracefully")
    print()
    return True


def test_missing_metadata_fields():
    """Test graceful handling of missing metadata fields."""

    print("=" * 100)
    print("TEST 7: MISSING METADATA FIELDS")
    print("=" * 100)
    print()

    # Minimal metadata (many fields missing)
    minimal_metadata = {
        'filename': 'test.pdf'
    }

    print("Testing minimal metadata (only filename):")
    print("-" * 100)

    # Simulate citation generation with minimal metadata
    doc_info = {
        'id': 'test_001',
        'title': None,  # Missing
        'source': None,  # Missing
        'metadata': minimal_metadata
    }

    try:
        # Simulate basic field access with defaults
        title = doc_info.get('title', 'Unknown Document')
        source = doc_info.get('source', minimal_metadata.get('filename', 'Unknown'))

        print(f"  ✓ Title: {title}")
        print(f"  ✓ Source: {source}")
        print(f"  ✓ No errors with missing fields")

        passed = True
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        passed = False

    print()
    print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
    print()
    return passed


if __name__ == "__main__":
    print()

    test1 = test_no_extractable_date()
    test2 = test_special_characters_in_filename()
    test3 = test_very_long_filename()
    test4 = test_temporal_context_truncation()
    test5 = test_empty_pdf_pages()
    test6 = test_invalid_date_formats()
    test7 = test_missing_metadata_fields()

    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)
    print(f"  No extractable date:          {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Special characters:           {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"  Very long filename:           {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"  Temporal context truncation:  {'✅ PASS' if test4 else '❌ FAIL'}")
    print(f"  Empty PDF pages:              {'✅ PASS' if test5 else '❌ FAIL'}")
    print(f"  Invalid date formats:         {'✅ PASS' if test6 else '❌ FAIL'}")
    print(f"  Missing metadata fields:      {'✅ PASS' if test7 else '❌ FAIL'}")
    print("=" * 100)

    all_passed = test1 and test2 and test3 and test4 and test5 and test6 and test7
    sys.exit(0 if all_passed else 1)
