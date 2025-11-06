"""Test that ordinal suffix removal doesn't break month names"""

from temporal_embeddings import TemporalEmbeddingHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Init
project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'test-project')
location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
handler = TemporalEmbeddingHandler(project_id, location)

print("Testing ordinal suffix fix:")
print("=" * 80)

test_dates = [
    "August 18, 2024",          # Was failing - "August" became "Augu"
    "August 1st, 2024",         # Should work
    "January 21st, 2025",       # Should work
    "November 3rd, 2024",       # Should work
    "December 12th, 2024",      # Should work
    "August 27, 2024",          # The user's problematic date
    "1st of August, 2024",      # Day-first format
    "21st of November, 2024",   # Day-first format
]

print(f"Testing _normalize_date() with {len(test_dates)} dates:\n")

all_passed = True
for date_str in test_dates:
    normalized = handler._normalize_date(date_str)
    if normalized and len(normalized) == 10 and normalized.startswith("20"):
        print(f"✓ {date_str:30} -> {normalized}")
    else:
        print(f"✗ {date_str:30} -> {normalized or 'FAILED'}")
        all_passed = False

print("=" * 80)
if all_passed:
    print("\n✓ All tests PASSED! The ordinal suffix fix is working correctly.")
else:
    print("\n✗ Some tests FAILED! There may still be issues with date normalization.")
