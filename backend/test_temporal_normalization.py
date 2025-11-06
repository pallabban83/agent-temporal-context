"""
Test script to verify temporal date normalization works correctly.

This tests that documents and queries use consistent date formats in their
temporal context, ensuring good embedding similarity.
"""

import os
import sys
from temporal_embeddings import TemporalEmbeddingHandler

# Test configuration
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')

print("=" * 80)
print("Testing Temporal Date Normalization")
print("=" * 80)

# Initialize handler
handler = TemporalEmbeddingHandler(project_id=project_id, location=location)

# Test 1: Filename date extraction
print("\n--- Test 1: Filename Date Extraction ---")
filename = "JANUARY 7TH, 2025.pdf"
extracted_date = handler.extract_date_from_filename(filename)
print(f"Filename: {filename}")
print(f"Extracted date: {extracted_date}")
print(f"Expected: 2025-01-07")
print(f"✓ PASS" if extracted_date == "2025-01-07" else "✗ FAIL")

# Test 2: Query temporal extraction and normalization
print("\n--- Test 2: Query Temporal Extraction ---")
query = "What was the safety tip on January 07,2025?"
temporal_info = handler.extract_temporal_info(query)
print(f"Query: {query}")
print(f"Extracted temporal entities: {temporal_info}")
if temporal_info:
    dates = [e['value'] for e in temporal_info if e['type'] == 'date']
    print(f"Extracted dates: {dates}")

# Test 3: Document temporal context (simulating a chunk from the file)
print("\n--- Test 3: Document Temporal Context ---")
doc_content = "Safety tip: Always wear protective equipment when operating machinery."
doc_metadata = {
    'document_date': extracted_date,  # From filename
    'filename': filename
}
enhanced_doc = handler.enhance_text_with_temporal_context(doc_content, doc_metadata)
print(f"Original content: {doc_content}")
print(f"Enhanced content:\n{enhanced_doc}")

# Test 4: Query temporal context
print("\n--- Test 4: Query Temporal Context ---")
query_metadata = {}  # Queries don't have document_date in metadata
enhanced_query = handler.enhance_text_with_temporal_context(query, query_metadata)
print(f"Original query: {query}")
print(f"Enhanced query:\n{enhanced_query}")

# Test 5: Compare temporal context prefixes
print("\n--- Test 5: Temporal Context Comparison ---")
doc_prefix = enhanced_doc.split('\n')[0] if '\n' in enhanced_doc else enhanced_doc[:100]
query_prefix = enhanced_query.split('\n')[0] if '\n' in enhanced_query else enhanced_query[:100]

print(f"Document prefix: {doc_prefix}")
print(f"Query prefix: {query_prefix}")

# Check if both contain the normalized date format
if "2025-01-07" in doc_prefix and "2025-01-07" in query_prefix:
    print("\n✓ SUCCESS: Both document and query use normalized date format (2025-01-07)")
    print("✓ Embeddings should now have good similarity!")
else:
    print("\n✗ FAIL: Date formats don't match")
    if "2025-01-07" not in doc_prefix:
        print(f"  Document missing normalized date")
    if "2025-01-07" not in query_prefix:
        print(f"  Query missing normalized date")

# Test 6: Additional date format variations
print("\n--- Test 6: Additional Date Format Variations ---")
test_queries = [
    "safety tip on Jan 7, 2025",
    "safety tip on 01/07/2025",
    "safety tip on 2025-01-07",
    "safety tip on January 7th, 2025",
    "safety tip on 7th of January, 2025",
    "safety tip on January 7th.2025",  # Period instead of comma (no space)
    "safety tip on January 7TH. 2025"  # Period with space after
]

for test_query in test_queries:
    enhanced = handler.enhance_text_with_temporal_context(test_query, {})
    prefix = enhanced.split('\n')[0] if '\n' in enhanced else enhanced[:100]
    has_normalized = "2025-01-07" in prefix
    status = "✓" if has_normalized else "✗"
    print(f"{status} {test_query[:40]:45} -> {prefix[:60]}")

print("\n" + "=" * 80)
print("Test completed!")
print("=" * 80)
