"""
Test that metadata is created correctly for GCS import
Simulates the exact metadata that would be stored in Vector Search
"""

from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Init
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
handler = TemporalEmbeddingHandler(project_id, location)

print("=" * 100)
print("METADATA CREATION TEST - Simulating GCS import metadata")
print("=" * 100)

# Test critical filenames
test_cases = [
    "Aug 27, 2024.pdf",           # User's problematic case
    "August 09,2024.pdf",          # No space after comma
    "1st of November, 2024.pdf",   # Day-first
    "AUGUST 21ST, 2024.pdf",       # All caps
    "2024-06-10.pdf",              # ISO format
]

print("\nSimulating metadata that would be stored in Vector Search:\n")

for filename in test_cases:
    # Simulate the GCS import metadata creation logic
    extracted_date = handler.extract_date_from_filename(filename)

    if extracted_date:
        document_date = handler._normalize_date(extracted_date)
    else:
        document_date = None

    # This is what gets stored in metadata
    metadata = {
        'filename': filename,
        'document_date': document_date if document_date else 'UNKNOWN',
        'uploaded_at': datetime.utcnow().isoformat(),
        'imported_from_gcs': True
    }

    # Validate
    is_valid = metadata['document_date'] != 'UNKNOWN' and len(metadata['document_date']) == 10
    status = "✓" if is_valid else "✗"

    print(f"{status} File: {filename:35}")
    print(f"   Metadata: {{")
    print(f"     'filename': '{metadata['filename']}',")
    print(f"     'document_date': '{metadata['document_date']}',  {'<-- CORRECT!' if is_valid else '<-- WRONG!'}")
    print(f"     'uploaded_at': '{metadata['uploaded_at'][:19]}',")
    print(f"     'imported_from_gcs': True")
    print(f"   }}\n")

print("=" * 100)
print("KEY POINT: document_date should be YYYY-MM-DD format, NOT just year!")
print("           This allows temporal filtering to work correctly in queries.")
print("=" * 100)
