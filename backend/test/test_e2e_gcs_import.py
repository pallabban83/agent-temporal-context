"""
End-to-end GCS import simulation test.

This test simulates the complete flow of importing a document from GCS:
1. Mock GCS file listing
2. Download file bytes (using local test file)
3. Parse PDF with metadata
4. Chunk with proper metadata
5. Extract date from filename
6. Generate embeddings with temporal context
7. Create complete metadata structure
8. Validate all metadata fields
9. Test citation generation
10. Verify temporal context enhancement
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from temporal_embeddings import TemporalEmbeddingHandler
from document_parser import DocumentParser
from text_chunker import TextChunker


def test_end_to_end_gcs_import():
    """Simulate the complete GCS import flow."""

    print("=" * 100)
    print("END-TO-END GCS IMPORT SIMULATION TEST")
    print("=" * 100)
    print()

    # ========================================
    # STEP 1: Mock GCS File Listing
    # ========================================
    print("STEP 1: Mock GCS file listing")
    print("-" * 100)

    test_pdfs_dir = Path(__file__).parent.parent / "test_pdfs"
    test_file = test_pdfs_dir / "Aug 27, 2024.pdf"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    # Simulate GCS file info
    gcs_file_info = {
        'filename': test_file.name,
        'gcs_path': f'gs://test-bucket/documents/{test_file.name}',
        'public_url': f'https://storage.cloud.google.com/test-bucket/documents/{test_file.name}',
        'content_type': 'application/pdf',
        'size': test_file.stat().st_size
    }

    print(f"  ✓ Simulated GCS path: {gcs_file_info['gcs_path']}")
    print(f"  ✓ Public URL: {gcs_file_info['public_url']}")
    print(f"  ✓ File size: {gcs_file_info['size']} bytes")
    print()

    # ========================================
    # STEP 2: Download file bytes
    # ========================================
    print("STEP 2: Download file bytes (using local test file)")
    print("-" * 100)

    with open(test_file, 'rb') as f:
        file_bytes = f.read()

    print(f"  ✓ Downloaded {len(file_bytes)} bytes")
    print()

    # ========================================
    # STEP 3: Parse PDF with metadata
    # ========================================
    print("STEP 3: Parse PDF with metadata extraction")
    print("-" * 100)

    parsed = DocumentParser.parse_document(
        file_bytes,
        gcs_file_info['filename'],
        gcs_file_info['content_type']
    )

    print(f"  ✓ Document type: {parsed['type']}")
    print(f"  ✓ Text length: {len(parsed['text'])} characters")

    # Get detailed PDF info
    pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)
    print(f"  ✓ Total pages: {pdf_result['total_pages']}")
    print(f"  ✓ Non-empty pages: {pdf_result.get('non_empty_pages', pdf_result['total_pages'])}")
    print(f"  ✓ Has tables: {pdf_result.get('has_tables', False)}")
    print(f"  ✓ Total tables: {pdf_result.get('total_tables', 0)}")
    print()

    # ========================================
    # STEP 4: Extract date from filename
    # ========================================
    print("STEP 4: Extract temporal information from filename")
    print("-" * 100)

    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    extracted_date = handler.extract_date_from_filename(gcs_file_info['filename'])
    normalized_date = handler._normalize_date(extracted_date) if extracted_date else None

    print(f"  Filename: {gcs_file_info['filename']}")
    print(f"  ✓ Extracted: {extracted_date}")
    print(f"  ✓ Normalized: {normalized_date}")

    if not normalized_date or len(normalized_date) != 10:
        print(f"  ⚠️  WARNING: Date extraction failed or invalid format")
    print()

    # ========================================
    # STEP 5: Create base metadata
    # ========================================
    print("STEP 5: Create base metadata structure")
    print("-" * 100)

    base_metadata = {
        'filename': gcs_file_info['filename'],
        'source': gcs_file_info['filename'],
        'title': gcs_file_info['filename'].rsplit('.', 1)[0],
        'original_file_url': gcs_file_info['public_url'],
        'source_url': gcs_file_info['public_url'],
        'gcs_source_path': gcs_file_info['gcs_path'],
        'imported_from_gcs': True,
        'uploaded_at': datetime.now().isoformat(),
        'document_type': 'pdf',
        'total_pages': pdf_result['total_pages'],
        'non_empty_pages': pdf_result.get('non_empty_pages', pdf_result['total_pages']),
        'has_tables': pdf_result.get('has_tables', False),
        'total_tables': pdf_result.get('total_tables', 0),
        'document_date': normalized_date
    }

    print(f"  ✓ Created base metadata with {len(base_metadata)} fields")
    for key, value in base_metadata.items():
        display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        print(f"    - {key}: {display_value}")
    print()

    # ========================================
    # STEP 6: Chunk the document
    # ========================================
    print("STEP 6: Chunk document with proper metadata propagation")
    print("-" * 100)

    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    document_id = f"{gcs_file_info['filename'].replace('.', '_').replace(' ', '_')}_{int(datetime.now().timestamp())}"

    chunks = chunker.chunk_pdf_by_pages(
        page_texts=pdf_result['page_texts'],
        metadata=base_metadata,
        document_id=document_id
    )

    print(f"  ✓ Created {len(chunks)} chunks")
    print(f"  ✓ Chunk size: 1000 characters")
    print(f"  ✓ Chunk overlap: 200 characters")
    print()

    # Analyze chunk metadata
    if chunks:
        chunk = chunks[0]
        chunk_metadata = chunk.get('metadata', {})
        print(f"  Sample chunk metadata (Chunk 1):")
        print(f"    - Metadata fields: {len(chunk_metadata)}")
        print(f"    - Quality score: {chunk_metadata.get('quality_score', 'N/A')}")
        print(f"    - Page number: {chunk_metadata.get('page_number', 'N/A')}")
        print(f"    - Chunk index: {chunk_metadata.get('chunk_index', 'N/A')}")
        print(f"    - Has table: {chunk_metadata.get('has_table', 'N/A')}")
    print()

    # ========================================
    # STEP 7: Generate embeddings with temporal context
    # ========================================
    print("STEP 7: Generate embeddings with temporal context enhancement")
    print("-" * 100)

    if chunks:
        sample_chunk = chunks[0]
        content = sample_chunk['content']
        metadata = sample_chunk.get('metadata', {})

        # Extract temporal info from content
        temporal_entities = handler.extract_temporal_info(content)
        print(f"  ✓ Temporal entities extracted from content:")

        # Group entities by type for display
        entity_types = {}
        for entity in temporal_entities:
            etype = entity['type']
            if etype not in entity_types:
                entity_types[etype] = []
            entity_types[etype].append(entity['value'])

        for key, values in entity_types.items():
            if values:
                print(f"    - {key}: {values}")

        # Enhance text with temporal context
        enhanced_text = handler.enhance_text_with_temporal_context(content, metadata)

        # Check if temporal context was added
        has_temporal_prefix = enhanced_text.startswith("[TEMPORAL_CONTEXT:")
        print(f"  ✓ Temporal enhancement applied: {has_temporal_prefix}")

        if has_temporal_prefix:
            # Extract and show prefix
            prefix_end = enhanced_text.find("]", 18) + 1
            if prefix_end > 18:
                prefix = enhanced_text[:prefix_end]
                print(f"  ✓ Temporal prefix:")
                print(f"    {prefix[:100]}...")
        print()

        # Note: We're not actually generating embeddings here to avoid API calls
        print("  ℹ️  Skipping actual embedding generation (would require API call)")
        print("  ℹ️  In production, this would call textembedding-gecko model")
        print()

    # ========================================
    # STEP 8: Simulate citation generation
    # ========================================
    print("STEP 8: Simulate citation generation")
    print("-" * 100)

    if chunks:
        chunk = chunks[0]
        doc_id = chunk.get('id', 'unknown')
        metadata = chunk.get('metadata', {})

        # Simulate citation format (from vector_search_manager._format_citation)
        citation = {
            'document_id': doc_id,
            'title': metadata.get('title', 'Unknown'),
            'source': metadata.get('source', metadata.get('filename', 'Unknown')),
            'original_file_url': metadata.get('original_file_url', ''),
            'clickable_link': metadata.get('original_file_url', ''),
            'date': metadata.get('document_date', ''),
            'page_number': metadata.get('page_number'),
            'chunk_index': metadata.get('chunk_index'),
            'page_chunk_index': metadata.get('page_chunk_index'),
            'quality_score': metadata.get('quality_score'),
        }

        # Format citation string
        location_parts = []
        if citation.get('page_number'):
            location_parts.append(f"Page {citation['page_number']}")
        if citation.get('page_chunk_index') is not None:
            location_parts.append(f"Chunk {citation['page_chunk_index']}")
        elif citation.get('chunk_index') is not None:
            location_parts.append(f"Chunk {citation['chunk_index']}")

        location_str = ", ".join(location_parts) if location_parts else ""
        formatted = f"{citation['title']}"
        if location_str:
            formatted += f" ({location_str})"
        if citation.get('date'):
            formatted += f" | Date: {citation['date']}"
        if citation.get('quality_score') is not None:
            formatted += f" | Quality: {citation['quality_score']:.2f}"
        formatted += f" | Source: {citation['source']}"

        print(f"  ✓ Citation generated:")
        print(f"    {formatted}")
        if citation.get('clickable_link'):
            print(f"    View Document: {citation['clickable_link']}")
        print()

    # ========================================
    # STEP 9: Validation Summary
    # ========================================
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)

    validations = [
        ("GCS file info parsed", gcs_file_info is not None),
        ("File bytes downloaded", len(file_bytes) > 0),
        ("PDF parsed successfully", parsed is not None),
        ("Date extracted from filename", normalized_date is not None and len(normalized_date) == 10),
        ("Base metadata created", len(base_metadata) >= 13),
        ("Chunks created", len(chunks) > 0),
        ("Chunk metadata complete", len(chunk_metadata) >= 15 if chunks else False),
        ("Temporal context extracted", bool(temporal_entities) if chunks else False),
        ("Citation generated", citation is not None if chunks else False)
    ]

    passed = sum(1 for _, result in validations if result)
    total = len(validations)

    print()
    for check, result in validations:
        status = "✅" if result else "❌"
        print(f"  {status} {check}")

    print()
    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("✅ ALL VALIDATION CHECKS PASSED!")
        print("   End-to-end GCS import flow is working correctly.")
    else:
        print(f"❌ {total - passed} VALIDATION CHECK(S) FAILED!")
        print("   Review the output above for details.")

    print("=" * 100)

    return passed == total


if __name__ == "__main__":
    success = test_end_to_end_gcs_import()
    sys.exit(0 if success else 1)
