"""
Comprehensive test that simulates GCS import date extraction logic
Tests all files in test_pdfs/ folder
"""

from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Init
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
handler = TemporalEmbeddingHandler(project_id, location)

print("=" * 100)
print("GCS IMPORT DATE EXTRACTION TEST - All test_pdfs files")
print("=" * 100)

# Get all PDF files from test_pdfs directory
test_pdfs_dir = Path("/Users/Pallab documents/agent-temporal-context/backend/test_pdfs")
pdf_files = sorted(test_pdfs_dir.glob("*.pdf"))

print(f"\nFound {len(pdf_files)} PDF files to test\n")

# Track results
results = {
    'success': [],
    'failed': [],
    'invalid_date': []
}

# Test each file through the GCS import logic
for pdf_file in pdf_files:
    filename = pdf_file.name

    # Step 1: Extract date from filename (same as GCS import)
    extracted_date = handler.extract_date_from_filename(filename)

    # Step 2: Normalize the extracted date
    if extracted_date:
        normalized_date = handler._normalize_date(extracted_date)
    else:
        normalized_date = None

    # Validate result
    is_valid = normalized_date and len(normalized_date) == 10 and normalized_date.startswith("20")

    # Display result
    status = "✓" if is_valid else "✗"

    if is_valid:
        print(f"{status} {filename:45} | Extracted: {extracted_date:20} | Final: {normalized_date}")
        results['success'].append(filename)
    elif extracted_date and not normalized_date:
        print(f"{status} {filename:45} | Extracted: {extracted_date:20} | Normalization FAILED")
        results['invalid_date'].append((filename, extracted_date))
    else:
        print(f"{status} {filename:45} | No date extracted from filename")
        results['failed'].append(filename)

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"✓ Successfully extracted & normalized: {len(results['success'])}/{len(pdf_files)}")
print(f"✗ Extraction failed (no date found):   {len(results['failed'])}/{len(pdf_files)}")
print(f"✗ Normalization failed:                {len(results['invalid_date'])}/{len(pdf_files)}")

if results['failed']:
    print("\n" + "-" * 100)
    print("FILES WITH FAILED DATE EXTRACTION:")
    for filename in results['failed']:
        print(f"  - {filename}")

if results['invalid_date']:
    print("\n" + "-" * 100)
    print("FILES WITH FAILED NORMALIZATION:")
    for filename, extracted in results['invalid_date']:
        print(f"  - {filename} (extracted: '{extracted}')")

print("\n" + "=" * 100)

if len(results['success']) == len(pdf_files):
    print("✓ ALL TESTS PASSED! All dates extracted and normalized correctly.")
    print("  GCS import should work perfectly for all test files.")
else:
    print("✗ SOME TESTS FAILED! Date parsing issues detected.")
    print(f"  {len(results['success'])}/{len(pdf_files)} files will import correctly.")
    print(f"  {len(results['failed']) + len(results['invalid_date'])} files will have issues.")

print("=" * 100)
