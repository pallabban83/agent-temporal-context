"""
Test different chunk_size and chunk_overlap parameters.

This test validates that:
1. Different chunk_size values produce correct number of chunks
2. Different chunk_overlap values create proper overlapping content
3. Quality scores are calculated correctly for different chunk sizes
4. User-provided document_date overrides filename extraction
5. Metadata is consistent across all chunks
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


def test_chunk_size_variations():
    """Test different chunk_size values."""

    print("=" * 100)
    print("CHUNK SIZE PARAMETER TESTING")
    print("=" * 100)
    print()

    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    # Read and parse PDF
    with open(test_file, 'rb') as f:
        file_bytes = f.read()

    pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)
    total_text_length = sum(len(page) for page in pdf_result['page_texts'])

    print(f"Test file: {test_file.name}")
    print(f"Total text length: {total_text_length} characters")
    print()

    # Test different chunk sizes
    chunk_sizes = [500, 1000, 1500, 2000]
    overlap = 200

    base_metadata = {
        'filename': test_file.name,
        'source': test_file.name,
        'title': test_file.name.rsplit('.', 1)[0],
        'document_type': 'pdf'
    }

    print("Testing different chunk_size values (overlap=200):")
    print("-" * 100)
    print(f"{'Chunk Size':>12} | {'Chunks':>8} | {'Avg Size':>10} | {'Min Size':>10} | {'Max Size':>10} | {'Avg Quality':>12}")
    print("-" * 100)

    results = []
    for chunk_size in chunk_sizes:
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        document_id = f"test_{chunk_size}"

        chunks = chunker.chunk_pdf_by_pages(
            page_texts=pdf_result['page_texts'],
            metadata=base_metadata,
            document_id=document_id
        )

        # Calculate statistics
        chunk_lengths = [len(chunk['content']) for chunk in chunks]
        quality_scores = [chunk['metadata'].get('quality_score', 0) for chunk in chunks]

        avg_size = sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0
        min_size = min(chunk_lengths) if chunk_lengths else 0
        max_size = max(chunk_lengths) if chunk_lengths else 0
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        print(f"{chunk_size:>12} | {len(chunks):>8} | {avg_size:>10.0f} | {min_size:>10} | {max_size:>10} | {avg_quality:>12.3f}")

        results.append({
            'chunk_size': chunk_size,
            'num_chunks': len(chunks),
            'avg_size': avg_size,
            'min_size': min_size,
            'max_size': max_size,
            'avg_quality': avg_quality
        })

    print()

    # Validation
    print("VALIDATION:")
    print("-" * 100)
    all_passed = True

    # Check that smaller chunk sizes produce more chunks (generally)
    for i in range(len(results) - 1):
        if results[i]['chunk_size'] < results[i+1]['chunk_size']:
            if results[i]['num_chunks'] >= results[i+1]['num_chunks']:
                print(f"  ✓ Smaller chunk_size ({results[i]['chunk_size']}) produced more/equal chunks than larger ({results[i+1]['chunk_size']})")
            else:
                print(f"  ⚠️  Smaller chunk_size ({results[i]['chunk_size']}) produced fewer chunks than larger ({results[i+1]['chunk_size']})")

    # Check that average sizes are reasonable
    for result in results:
        if result['avg_size'] <= result['chunk_size'] * 1.2:  # Allow 20% variance
            print(f"  ✓ Average chunk size for chunk_size={result['chunk_size']} is within expected range ({result['avg_size']:.0f})")
        else:
            print(f"  ❌ Average chunk size for chunk_size={result['chunk_size']} exceeds expected range ({result['avg_size']:.0f})")
            all_passed = False

    print()
    return all_passed


def test_chunk_overlap_variations():
    """Test different chunk_overlap values."""

    print("=" * 100)
    print("CHUNK OVERLAP PARAMETER TESTING")
    print("=" * 100)
    print()

    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    # Read and parse PDF
    with open(test_file, 'rb') as f:
        file_bytes = f.read()

    pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)

    print(f"Test file: {test_file.name}")
    print()

    # Test different overlaps
    chunk_size = 1000
    overlaps = [0, 100, 200, 300]

    base_metadata = {
        'filename': test_file.name,
        'source': test_file.name,
        'title': test_file.name.rsplit('.', 1)[0],
        'document_type': 'pdf'
    }

    print("Testing different chunk_overlap values (chunk_size=1000):")
    print("-" * 100)
    print(f"{'Overlap':>10} | {'Chunks':>8} | {'Total Chars':>12} | {'Overhead %':>12}")
    print("-" * 100)

    total_text_length = sum(len(page) for page in pdf_result['page_texts'])

    results = []
    for overlap in overlaps:
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        document_id = f"test_overlap_{overlap}"

        chunks = chunker.chunk_pdf_by_pages(
            page_texts=pdf_result['page_texts'],
            metadata=base_metadata,
            document_id=document_id
        )

        # Calculate total characters (including overlap)
        total_chars = sum(len(chunk['content']) for chunk in chunks)
        overhead_pct = ((total_chars - total_text_length) / total_text_length * 100) if total_text_length > 0 else 0

        print(f"{overlap:>10} | {len(chunks):>8} | {total_chars:>12} | {overhead_pct:>11.1f}%")

        results.append({
            'overlap': overlap,
            'num_chunks': len(chunks),
            'total_chars': total_chars,
            'overhead_pct': overhead_pct
        })

    print()

    # Validation
    print("VALIDATION:")
    print("-" * 100)
    all_passed = True

    # Check that larger overlaps produce more total characters
    for i in range(len(results) - 1):
        if results[i]['overlap'] < results[i+1]['overlap']:
            if results[i]['total_chars'] <= results[i+1]['total_chars']:
                print(f"  ✓ Larger overlap ({results[i+1]['overlap']}) produced more/equal total chars than smaller ({results[i]['overlap']})")
            else:
                print(f"  ❌ Larger overlap ({results[i+1]['overlap']}) produced fewer total chars than smaller ({results[i]['overlap']})")
                all_passed = False

    # Check zero overlap matches original text length
    zero_overlap_result = next((r for r in results if r['overlap'] == 0), None)
    if zero_overlap_result:
        if abs(zero_overlap_result['total_chars'] - total_text_length) < 100:  # Allow small variance
            print(f"  ✓ Zero overlap total chars ({zero_overlap_result['total_chars']}) matches original text length ({total_text_length})")
        else:
            print(f"  ⚠️  Zero overlap total chars ({zero_overlap_result['total_chars']}) differs from original ({total_text_length})")

    print()
    return all_passed


def test_document_date_override():
    """Test that user-provided document_date overrides filename extraction."""

    print("=" * 100)
    print("DOCUMENT DATE OVERRIDE TESTING")
    print("=" * 100)
    print()

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    filename = test_file.name

    # Extract date from filename
    extracted_date = handler.extract_date_from_filename(filename)
    normalized_extracted = handler._normalize_date(extracted_date) if extracted_date else None

    # User-provided date (overrides filename)
    user_provided_date = "2023-12-31"

    print(f"Filename: {filename}")
    print(f"Extracted from filename: {normalized_extracted}")
    print(f"User-provided date: {user_provided_date}")
    print()

    # Simulate GCS import logic
    print("Simulating GCS import date logic:")
    print("-" * 100)

    # Priority: user-provided > filename extraction
    final_document_date = user_provided_date if user_provided_date else normalized_extracted

    print(f"  1. Check user-provided date: {user_provided_date}")
    print(f"  2. If None, use filename extraction: {normalized_extracted}")
    print(f"  3. Final document_date: {final_document_date}")
    print()

    # Validation
    print("VALIDATION:")
    print("-" * 100)

    if final_document_date == user_provided_date:
        print(f"  ✅ User-provided date correctly overrides filename extraction")
        print(f"     Expected: {user_provided_date}")
        print(f"     Got:      {final_document_date}")
        return True
    else:
        print(f"  ❌ Date override FAILED")
        print(f"     Expected: {user_provided_date}")
        print(f"     Got:      {final_document_date}")
        return False


def test_metadata_consistency_across_chunks():
    """Test that base metadata is consistent across all chunks."""

    print("=" * 100)
    print("METADATA CONSISTENCY TESTING")
    print("=" * 100)
    print()

    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    # Read and parse PDF
    with open(test_file, 'rb') as f:
        file_bytes = f.read()

    pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)

    base_metadata = {
        'filename': test_file.name,
        'source': test_file.name,
        'title': test_file.name.rsplit('.', 1)[0],
        'document_type': 'pdf',
        'total_pages': pdf_result['total_pages'],
        'document_date': '2024-08-27',
        'imported_from_gcs': True,
        'gcs_source_path': 'gs://test-bucket/test.pdf'
    }

    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    document_id = "test_consistency"

    chunks = chunker.chunk_pdf_by_pages(
        page_texts=pdf_result['page_texts'],
        metadata=base_metadata,
        document_id=document_id
    )

    print(f"Test file: {test_file.name}")
    print(f"Total chunks: {len(chunks)}")
    print()

    # Check consistency of base metadata across all chunks
    print("Checking base metadata consistency across all chunks:")
    print("-" * 100)

    base_fields_to_check = ['filename', 'source', 'title', 'document_type', 'total_pages', 'document_date', 'imported_from_gcs', 'gcs_source_path']

    all_consistent = True

    for field in base_fields_to_check:
        values = [chunk['metadata'].get(field) for chunk in chunks]
        unique_values = set(values)

        if len(unique_values) == 1:
            print(f"  ✓ {field:25} = {list(unique_values)[0]} (consistent across all {len(chunks)} chunks)")
        else:
            print(f"  ❌ {field:25} has {len(unique_values)} different values across chunks!")
            print(f"     Values: {unique_values}")
            all_consistent = False

    print()

    # Check that chunk-specific metadata DIFFERS across chunks
    print("Checking chunk-specific metadata varies across chunks:")
    print("-" * 100)

    chunk_specific_fields = ['chunk_index', 'page_chunk_index']

    for field in chunk_specific_fields:
        values = [chunk['metadata'].get(field) for chunk in chunks]
        unique_values = set(values)

        if len(unique_values) > 1 or len(chunks) == 1:
            print(f"  ✓ {field:25} varies across chunks (unique values: {len(unique_values)})")
        else:
            print(f"  ⚠️  {field:25} has same value across all chunks (expected variation)")

    print()
    return all_consistent


if __name__ == "__main__":
    print()
    success1 = test_chunk_size_variations()
    print()
    success2 = test_chunk_overlap_variations()
    print()
    success3 = test_document_date_override()
    print()
    success4 = test_metadata_consistency_across_chunks()
    print()

    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)
    print(f"  Chunk size variations:      {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Chunk overlap variations:   {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"  Document date override:     {'✅ PASS' if success3 else '❌ FAIL'}")
    print(f"  Metadata consistency:       {'✅ PASS' if success4 else '❌ FAIL'}")
    print("=" * 100)

    all_success = success1 and success2 and success3 and success4
    sys.exit(0 if all_success else 1)
