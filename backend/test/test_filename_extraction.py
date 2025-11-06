"""Test filename date extraction for problematic formats"""

from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Init
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
handler = TemporalEmbeddingHandler(project_id, location)

print("Testing filename date extraction:")
print("=" * 80)

test_filenames = [
    "Aug 27, 2024.pdf",          # The failing one
    "Jul 31, 2024.pdf",          # Abbreviated month
    "Jun 07, 2024.pdf",          # Abbreviated month
    "1st of November, 2024.pdf",
    "5th of October, 2024.pdf",
    "7th of January, 2025.pdf",
    "12th of August, 2024.pdf",
    "JUNE 01ST, 2024.pdf",
    "June 04th.2024.pdf",
    "2024-06-10.pdf",
]

for filename in test_filenames:
    extracted = handler.extract_date_from_filename(filename)
    status = "✓" if extracted and extracted.startswith("202") and len(extracted) == 10 else "✗"
    print(f"{status} {filename:40} -> {extracted}")

print("=" * 80)
