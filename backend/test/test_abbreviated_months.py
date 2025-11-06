"""Test abbreviated month date normalization"""

from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Init
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
handler = TemporalEmbeddingHandler(project_id, location)

print("Testing abbreviated month normalization:")
print("=" * 80)

test_dates = [
    ("Aug 27, 2024", "2024-08-27"),       # The user's problematic case
    ("Jan 15, 2025", "2025-01-15"),
    ("Feb 20, 2024", "2024-02-20"),
    ("Mar 10, 2024", "2024-03-10"),
    ("Apr 5, 2024", "2024-04-05"),
    ("May 12, 2024", "2024-05-12"),
    ("Jun 7, 2024", "2024-06-07"),
    ("Jul 31, 2024", "2024-07-31"),
    ("Sep 18, 2024", "2024-09-18"),
    ("Oct 22, 2024", "2024-10-22"),
    ("Nov 1, 2024", "2024-11-01"),
    ("Dec 25, 2024", "2024-12-25"),
]

print(f"Testing _normalize_date() with abbreviated months:\n")

all_passed = True
for date_str, expected in test_dates:
    normalized = handler._normalize_date(date_str)
    if normalized == expected:
        print(f"✓ {date_str:20} -> {normalized}")
    else:
        print(f"✗ {date_str:20} -> {normalized or 'FAILED'} (expected: {expected})")
        all_passed = False

print("=" * 80)
if all_passed:
    print("\n✓ All abbreviated month tests PASSED!")
else:
    print("\n✗ Some tests FAILED! Abbreviated months may not be handled correctly.")
    print("\nNote: dateutil.parser should handle abbreviated months automatically,")
    print("but if this fails, we may need to add explicit month abbreviation mapping.")
