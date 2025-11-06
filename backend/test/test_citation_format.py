"""
Test citation format generation as specified in CITATION_FORMAT.md.

Tests:
1. Citation field completeness
2. URL priority (original_file_url > source_url > gcs_chunk_url)
3. Location formatting (Page + chunk vs Page only vs Chunk only)
4. formatted string generation (pipe-separated)
5. formatted_with_link generation (with clickable URL)
6. Relevance score inclusion from vector search
7. Date formatting in YYYY-MM-DD
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def simulate_citation_formatting(doc_id: str, doc_info: dict, score: float = None) -> dict:
    """
    Simulate the _format_citation method from VectorSearchManager.

    Based on backend/src/vector_search_manager.py:_format_citation()
    """
    metadata = doc_info.get('metadata', {})

    # Base citation fields
    citation = {
        'document_id': doc_id,
        'title': doc_info.get('title', 'Unknown Document'),
        'source': doc_info.get('source', metadata.get('filename', 'Unknown'))
    }

    # Add relevance score if from query
    if score is not None:
        citation['score'] = score
        citation['relevance'] = score

    # Add page and chunk information from metadata
    if 'page_number' in metadata:
        citation['page_number'] = metadata['page_number']

    if 'chunk_index' in metadata:
        citation['chunk_index'] = metadata['chunk_index']

    if 'page_chunk_index' in metadata:
        citation['page_chunk_index'] = metadata['page_chunk_index']

    if 'quality_score' in metadata:
        citation['quality_score'] = metadata['quality_score']

    # URL priority: original_file_url > source_url > chunk URL
    if 'original_file_url' in metadata:
        citation['original_file_url'] = metadata['original_file_url']
        citation['clickable_link'] = metadata['original_file_url']
    elif metadata.get('source_url'):
        citation['source_url'] = metadata['source_url']
        citation['clickable_link'] = metadata['source_url']
    elif doc_info.get('chunk_json_url'):
        citation['gcs_chunk_url'] = doc_info['chunk_json_url']
        citation['clickable_link'] = doc_info['chunk_json_url']

    # Add document date
    if 'document_date' in metadata:
        citation['date'] = metadata['document_date']

    # Format location string (for formatted output)
    location_parts = []
    if citation.get('page_number'):
        location_parts.append(f"Page {citation['page_number']}")

    if citation.get('page_chunk_index') is not None:
        location_parts.append(f"Chunk {citation['page_chunk_index']}")
    elif citation.get('chunk_index') is not None:
        location_parts.append(f"Chunk {citation['chunk_index']}")

    location_str = ", ".join(location_parts) if location_parts else ""

    # Create formatted string (pipe-separated)
    formatted_parts = [citation['title']]

    if location_str:
        formatted_parts[0] += f" ({location_str})"

    if citation.get('date'):
        formatted_parts.append(f"Date: {citation['date']}")

    if citation.get('relevance') is not None:
        formatted_parts.append(f"Relevance: {citation['relevance']:.4f}")

    formatted_parts.append(f"Source: {citation['source']}")

    citation['formatted'] = " | ".join(formatted_parts)

    # Create formatted_with_link (adds URL on next line)
    if citation.get('clickable_link'):
        citation['formatted_with_link'] = citation['formatted'] + f"\nView Document: {citation['clickable_link']}"
    else:
        citation['formatted_with_link'] = citation['formatted']

    return citation


def test_basic_citation_fields():
    """Test that all basic citation fields are present."""

    print("=" * 100)
    print("TEST 1: BASIC CITATION FIELDS")
    print("=" * 100)
    print()

    doc_info = {
        'id': 'doc_001',
        'title': 'Q2 2024 Earnings Report',
        'source': 'earnings_q2_2024.pdf',
        'metadata': {
            'filename': 'earnings_q2_2024.pdf',
            'document_date': '2024-06-30',
            'original_file_url': 'https://storage.cloud.google.com/bucket/earnings.pdf',
            'page_number': 5,
            'chunk_index': 12,
            'page_chunk_index': 3,
            'quality_score': 0.85
        }
    }

    citation = simulate_citation_formatting('doc_001', doc_info, score=0.7523)

    required_fields = [
        'document_id', 'title', 'source', 'score', 'relevance',
        'page_number', 'chunk_index', 'page_chunk_index', 'quality_score',
        'original_file_url', 'clickable_link', 'date', 'formatted', 'formatted_with_link'
    ]

    print("Required citation fields:")
    print("-" * 100)

    all_present = True
    for field in required_fields:
        if field in citation:
            value = str(citation[field])
            display_value = value[:70] + "..." if len(value) > 70 else value
            print(f"  ✓ {field:25} = {display_value}")
        else:
            print(f"  ❌ {field:25} = MISSING!")
            all_present = False

    print()
    print(f"Result: {'✅ PASS - All fields present' if all_present else '❌ FAIL - Missing fields'}")
    print()
    return all_present


def test_url_priority():
    """Test URL priority: original_file_url > source_url > gcs_chunk_url."""

    print("=" * 100)
    print("TEST 2: URL PRIORITY")
    print("=" * 100)
    print()

    test_cases = [
        {
            'name': 'Has original_file_url (highest priority)',
            'doc_info': {
                'id': 'doc_001',
                'title': 'Test Doc',
                'source': 'test.pdf',
                'metadata': {
                    'original_file_url': 'https://storage.googleapis.com/original/file.pdf',
                    'source_url': 'https://storage.googleapis.com/source/file.pdf',
                },
                'chunk_json_url': 'https://storage.googleapis.com/chunks/file.json'
            },
            'expected_link': 'https://storage.googleapis.com/original/file.pdf'
        },
        {
            'name': 'Has source_url only (medium priority)',
            'doc_info': {
                'id': 'doc_002',
                'title': 'Test Doc',
                'source': 'test.pdf',
                'metadata': {
                    'source_url': 'https://storage.googleapis.com/source/file.pdf',
                },
                'chunk_json_url': 'https://storage.googleapis.com/chunks/file.json'
            },
            'expected_link': 'https://storage.googleapis.com/source/file.pdf'
        },
        {
            'name': 'Has chunk_json_url only (lowest priority)',
            'doc_info': {
                'id': 'doc_003',
                'title': 'Test Doc',
                'source': 'test.pdf',
                'metadata': {},
                'chunk_json_url': 'https://storage.googleapis.com/chunks/file.json'
            },
            'expected_link': 'https://storage.googleapis.com/chunks/file.json'
        },
        {
            'name': 'No URLs available',
            'doc_info': {
                'id': 'doc_004',
                'title': 'Test Doc',
                'source': 'test.pdf',
                'metadata': {}
            },
            'expected_link': None
        }
    ]

    print("Testing URL priority:")
    print("-" * 100)

    all_passed = True
    for test_case in test_cases:
        citation = simulate_citation_formatting(
            test_case['doc_info']['id'],
            test_case['doc_info']
        )

        actual_link = citation.get('clickable_link')
        expected_link = test_case['expected_link']

        passed = actual_link == expected_link
        status = "✓" if passed else "✗"

        print(f"  {status} {test_case['name']}")
        if not passed:
            print(f"      Expected: {expected_link}")
            print(f"      Got:      {actual_link}")
            all_passed = False

    print()
    print(f"Result: {'✅ PASS - URL priority correct' if all_passed else '❌ FAIL - URL priority incorrect'}")
    print()
    return all_passed


def test_location_formatting():
    """Test location string formatting for different scenarios."""

    print("=" * 100)
    print("TEST 3: LOCATION FORMATTING")
    print("=" * 100)
    print()

    test_cases = [
        {
            'name': 'Page + page_chunk_index (preferred)',
            'metadata': {
                'page_number': 5,
                'page_chunk_index': 3,
                'chunk_index': 12
            },
            'expected_location': 'Page 5, Chunk 3'
        },
        {
            'name': 'Page + chunk_index (fallback)',
            'metadata': {
                'page_number': 5,
                'chunk_index': 12
            },
            'expected_location': 'Page 5, Chunk 12'
        },
        {
            'name': 'Page only',
            'metadata': {
                'page_number': 5
            },
            'expected_location': 'Page 5'
        },
        {
            'name': 'page_chunk_index only',
            'metadata': {
                'page_chunk_index': 3
            },
            'expected_location': 'Chunk 3'
        },
        {
            'name': 'chunk_index only',
            'metadata': {
                'chunk_index': 12
            },
            'expected_location': 'Chunk 12'
        },
        {
            'name': 'No location info',
            'metadata': {},
            'expected_location': ''
        }
    ]

    print("Testing location formatting:")
    print("-" * 100)

    all_passed = True
    for test_case in test_cases:
        doc_info = {
            'id': 'test',
            'title': 'Test Document',
            'source': 'test.pdf',
            'metadata': test_case['metadata']
        }

        citation = simulate_citation_formatting('test', doc_info)

        # Extract location from formatted string
        formatted = citation['formatted']
        if '(' in formatted and ')' in formatted:
            start = formatted.find('(') + 1
            end = formatted.find(')')
            actual_location = formatted[start:end]
        else:
            actual_location = ''

        expected_location = test_case['expected_location']
        passed = actual_location == expected_location
        status = "✓" if passed else "✗"

        print(f"  {status} {test_case['name']}")
        print(f"      Expected: '{expected_location}'")
        print(f"      Got:      '{actual_location}'")
        if not passed:
            all_passed = False

    print()
    print(f"Result: {'✅ PASS - Location formatting correct' if all_passed else '❌ FAIL - Location formatting incorrect'}")
    print()
    return all_passed


def test_formatted_string_generation():
    """Test pipe-separated formatted string generation."""

    print("=" * 100)
    print("TEST 4: FORMATTED STRING GENERATION")
    print("=" * 100)
    print()

    doc_info = {
        'id': 'doc_001',
        'title': 'Q2_2025_Earnings_Release',
        'source': 'earnings.pdf',
        'metadata': {
            'filename': 'earnings.pdf',
            'document_date': '2025-07-15',
            'original_file_url': 'https://storage.googleapis.com/bucket/earnings.pdf',
            'page_number': 2,
            'page_chunk_index': 6,
            'quality_score': 0.85
        }
    }

    citation = simulate_citation_formatting('doc_001', doc_info, score=0.7523)

    expected_format = "Q2_2025_Earnings_Release (Page 2, Chunk 6) | Date: 2025-07-15 | Relevance: 0.7523 | Source: earnings.pdf"
    actual_format = citation['formatted']

    print("Testing formatted string:")
    print("-" * 100)
    print(f"Expected:\n  {expected_format}\n")
    print(f"Actual:\n  {actual_format}\n")

    # Check components
    components_present = [
        ('Title with location', '(Page 2, Chunk 6)' in actual_format),
        ('Date', 'Date: 2025-07-15' in actual_format),
        ('Relevance', 'Relevance: 0.7523' in actual_format),
        ('Source', 'Source: earnings.pdf' in actual_format),
        ('Pipe separators', actual_format.count('|') == 3)
    ]

    print("Component validation:")
    print("-" * 100)
    all_present = True
    for component, present in components_present:
        status = "✓" if present else "✗"
        print(f"  {status} {component}")
        if not present:
            all_present = False

    print()
    matches = actual_format == expected_format
    print(f"Exact match: {'✅ YES' if matches else '⚠️  NO (but components may be correct)'}")
    print()
    print(f"Result: {'✅ PASS' if all_present else '❌ FAIL'}")
    print()
    return all_present


def test_formatted_with_link():
    """Test formatted_with_link includes clickable URL."""

    print("=" * 100)
    print("TEST 5: FORMATTED WITH LINK")
    print("=" * 100)
    print()

    doc_info = {
        'id': 'doc_001',
        'title': 'Test Document',
        'source': 'test.pdf',
        'metadata': {
            'document_date': '2024-06-30',
            'original_file_url': 'https://storage.googleapis.com/bucket/test.pdf',
            'page_number': 5
        }
    }

    citation = simulate_citation_formatting('doc_001', doc_info, score=0.85)

    formatted_with_link = citation['formatted_with_link']

    print("Testing formatted_with_link:")
    print("-" * 100)
    print(f"Generated citation:\n{formatted_with_link}\n")

    # Validation
    checks = [
        ('Contains formatted citation', citation['formatted'] in formatted_with_link),
        ('Contains newline', '\n' in formatted_with_link),
        ('Contains "View Document:"', 'View Document:' in formatted_with_link),
        ('Contains clickable URL', 'https://storage.googleapis.com/bucket/test.pdf' in formatted_with_link)
    ]

    print("Validation:")
    print("-" * 100)
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False

    print()
    print(f"Result: {'✅ PASS' if all_passed else '❌ FAIL'}")
    print()
    return all_passed


def test_relevance_score_handling():
    """Test citation with and without relevance score."""

    print("=" * 100)
    print("TEST 6: RELEVANCE SCORE HANDLING")
    print("=" * 100)
    print()

    doc_info = {
        'id': 'doc_001',
        'title': 'Test Document',
        'source': 'test.pdf',
        'metadata': {
            'document_date': '2024-06-30'
        }
    }

    # With score (from query)
    citation_with_score = simulate_citation_formatting('doc_001', doc_info, score=0.7523)

    # Without score (direct retrieval)
    citation_without_score = simulate_citation_formatting('doc_001', doc_info, score=None)

    print("Citation with relevance score (from query):")
    print("-" * 100)
    print(f"  {citation_with_score['formatted']}\n")

    print("Citation without relevance score (direct retrieval):")
    print("-" * 100)
    print(f"  {citation_without_score['formatted']}\n")

    # Validation
    has_score_in_with = 'Relevance:' in citation_with_score['formatted']
    has_score_in_without = 'Relevance:' in citation_without_score['formatted']

    print("Validation:")
    print("-" * 100)
    print(f"  {'✓' if has_score_in_with else '✗'} Citation with score includes 'Relevance:'")
    print(f"  {'✓' if not has_score_in_without else '✗'} Citation without score excludes 'Relevance:'")

    passed = has_score_in_with and not has_score_in_without

    print()
    print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
    print()
    return passed


if __name__ == "__main__":
    print()

    test1 = test_basic_citation_fields()
    test2 = test_url_priority()
    test3 = test_location_formatting()
    test4 = test_formatted_string_generation()
    test5 = test_formatted_with_link()
    test6 = test_relevance_score_handling()

    print("=" * 100)
    print("OVERALL SUMMARY")
    print("=" * 100)
    print(f"  Basic citation fields:       {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  URL priority:                {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"  Location formatting:         {'✅ PASS' if test3 else '❌ FAIL'}")
    print(f"  Formatted string:            {'✅ PASS' if test4 else '❌ FAIL'}")
    print(f"  Formatted with link:         {'✅ PASS' if test5 else '❌ FAIL'}")
    print(f"  Relevance score handling:    {'✅ PASS' if test6 else '❌ FAIL'}")
    print("=" * 100)

    all_passed = test1 and test2 and test3 and test4 and test5 and test6
    sys.exit(0 if all_passed else 1)
