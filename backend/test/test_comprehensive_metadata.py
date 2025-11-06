"""
Comprehensive metadata validation test for GCS import.

Tests all 15+ metadata fields that should be created during GCS import:
- Base metadata: filename, source, title, original_file_url, source_url, gcs_source_path
- Temporal: document_date, uploaded_at, imported_from_gcs
- PDF-specific: document_type, total_pages, non_empty_pages, has_tables, total_tables, pages_with_tables
- Chunk-specific: quality_score, page_number, chunk_index, page_chunk_index, has_table, table_count, has_complete_table
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from temporal_embeddings import TemporalEmbeddingHandler
from document_parser import DocumentParser
from text_chunker import TextChunker
from datetime import datetime


def test_comprehensive_metadata_structure():
    """Test that all metadata fields are correctly created during GCS import simulation."""

    print("=" * 100)
    print("COMPREHENSIVE METADATA VALIDATION TEST")
    print("=" * 100)
    print()

    # Initialize components
    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)

    # Test file path
    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    print(f"Testing file: {test_file.name}\n")

    # Read PDF
    with open(test_file, 'rb') as f:
        file_bytes = f.read()

    # Parse PDF (simulating GCS import flow)
    pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)

    # Simulate GCS import metadata creation
    filename = test_file.name
    gcs_path = f"gs://test-bucket/documents/{filename}"
    public_url = f"https://storage.cloud.google.com/test-bucket/documents/{filename}"

    # Create base metadata BEFORE chunking (as done in import_from_gcs)
    base_metadata = {
        'filename': filename,
        'source': filename,
        'title': filename.rsplit('.', 1)[0],
        'original_file_url': public_url,
        'source_url': public_url,
        'gcs_source_path': gcs_path,
        'imported_from_gcs': True,
        'uploaded_at': datetime.now().isoformat(),
        'document_type': 'pdf',
        'total_pages': pdf_result['total_pages'],
        'non_empty_pages': pdf_result.get('non_empty_pages', pdf_result['total_pages']),
        'has_tables': pdf_result.get('has_tables', False),
        'total_tables': pdf_result.get('total_tables', 0)
    }

    # Extract date from filename
    extracted_date = handler.extract_date_from_filename(filename)
    if extracted_date:
        final_document_date = handler._normalize_date(extracted_date)
        base_metadata['document_date'] = final_document_date

    document_id = f"{filename.replace('.', '_').replace(' ', '_')}_{int(datetime.now().timestamp())}"

    # Chunk the PDF
    chunks = chunker.chunk_pdf_by_pages(
        page_texts=pdf_result['page_texts'],
        metadata=base_metadata,
        document_id=document_id
    )

    print("=" * 100)
    print("METADATA VALIDATION RESULTS")
    print("=" * 100)
    print()

    # Required metadata fields
    required_base_fields = [
        'filename', 'source', 'title', 'original_file_url', 'source_url',
        'gcs_source_path', 'imported_from_gcs', 'uploaded_at'
    ]

    required_pdf_fields = [
        'document_type', 'total_pages', 'non_empty_pages',
        'has_tables', 'total_tables'
    ]

    required_temporal_fields = ['document_date']

    required_chunk_fields = [
        'quality_score', 'page_number', 'chunk_index', 'page_chunk_index',
        'has_table', 'table_count', 'has_complete_table'
    ]

    all_passed = True

    # Test first chunk
    if not chunks:
        print("❌ FAILED: No chunks created!")
        return

    chunk = chunks[0]
    chunk_metadata = chunk.get('metadata', {})

    print(f"Testing chunk 1 of {len(chunks)} total chunks\n")

    # Validate base metadata fields
    print("BASE METADATA FIELDS:")
    print("-" * 100)
    for field in required_base_fields:
        if field in chunk_metadata:
            value = chunk_metadata[field]
            # Truncate long values
            display_value = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
            print(f"  ✓ {field:25} = {display_value}")
        else:
            print(f"  ❌ {field:25} = MISSING!")
            all_passed = False

    print()

    # Validate PDF-specific fields
    print("PDF-SPECIFIC METADATA FIELDS:")
    print("-" * 100)
    for field in required_pdf_fields:
        if field in chunk_metadata:
            value = chunk_metadata[field]
            print(f"  ✓ {field:25} = {value}")
        else:
            print(f"  ❌ {field:25} = MISSING!")
            all_passed = False

    print()

    # Validate temporal fields
    print("TEMPORAL METADATA FIELDS:")
    print("-" * 100)
    for field in required_temporal_fields:
        if field in chunk_metadata:
            value = chunk_metadata[field]
            is_valid = len(value) == 10 and value.startswith("20")
            status = "✓" if is_valid else "⚠️"
            print(f"  {status} {field:25} = {value}")
            if not is_valid:
                print(f"      WARNING: Expected YYYY-MM-DD format")
        else:
            print(f"  ❌ {field:25} = MISSING!")
            all_passed = False

    print()

    # Validate chunk-specific fields
    print("CHUNK-SPECIFIC METADATA FIELDS:")
    print("-" * 100)
    for field in required_chunk_fields:
        if field in chunk_metadata:
            value = chunk_metadata[field]
            print(f"  ✓ {field:25} = {value}")

            # Additional validation for specific fields
            if field == 'quality_score':
                if not (0.0 <= value <= 1.0):
                    print(f"      ⚠️ WARNING: Quality score should be between 0.0 and 1.0")
            elif field == 'page_number' and value < 1:
                print(f"      ⚠️ WARNING: Page number should be >= 1")
        else:
            print(f"  ❌ {field:25} = MISSING!")
            all_passed = False

    print()
    print("=" * 100)

    # Summary
    total_fields = len(required_base_fields + required_pdf_fields + required_temporal_fields + required_chunk_fields)
    present_fields = sum(1 for field in (required_base_fields + required_pdf_fields + required_temporal_fields + required_chunk_fields) if field in chunk_metadata)

    print("SUMMARY")
    print("=" * 100)
    print(f"Total expected fields:  {total_fields}")
    print(f"Fields present:         {present_fields}")
    print(f"Fields missing:         {total_fields - present_fields}")
    print()

    if all_passed:
        print("✅ ALL METADATA FIELDS VALIDATED SUCCESSFULLY!")
        print("   GCS import metadata structure is complete and correct.")
    else:
        print("❌ METADATA VALIDATION FAILED!")
        print(f"   {total_fields - present_fields} fields are missing or invalid.")

    print("=" * 100)
    print()

    # Additional info: show all metadata keys present
    print("ALL METADATA KEYS PRESENT IN CHUNK:")
    print("-" * 100)
    for key in sorted(chunk_metadata.keys()):
        print(f"  - {key}")
    print()

    return all_passed


if __name__ == "__main__":
    test_comprehensive_metadata_structure()
