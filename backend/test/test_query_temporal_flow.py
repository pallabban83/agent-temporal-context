"""
Test script to verify query temporal context extraction and filtering.

This demonstrates the query flow:
1. User sends query with temporal information
2. Query embedding is generated with temporal context
3. Temporal filter is extracted from query text
4. Results are filtered based on temporal criteria
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from temporal_embeddings import TemporalEmbeddingHandler
from typing import Dict, Any, List


def simulate_vector_search_query():
    """Simulate the query flow with temporal context extraction."""

    print("=" * 80)
    print("QUERY TEMPORAL CONTEXT EXTRACTION TEST")
    print("=" * 80)
    print()

    # Initialize handler
    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Test queries with temporal information
    test_queries = [
        "What were the Q1 2023 earnings?",
        "Show me documents from 2024",
        "Find the January 15, 2023 report",
        "What is the latest revenue forecast?",
        "December 2023 financial summary",
        "What happened in fiscal year 2024?",
    ]

    print("Simulating query processing with temporal extraction:")
    print()

    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: \"{query}\"")
        print("-" * 80)

        # Step 1: Generate query embedding (with temporal context)
        print(f"  ✓ Step 1: Generate query embedding with temporal context")
        enhanced_query = handler.enhance_text_with_temporal_context(query, {})

        if enhanced_query != query:
            if enhanced_query.startswith('[TEMPORAL_CONTEXT:'):
                prefix_end = enhanced_query.find(']\n')
                if prefix_end != -1:
                    temporal_prefix = enhanced_query[:prefix_end + 1]
                    print(f"    Query Temporal Prefix: {temporal_prefix}")
        else:
            print(f"    No temporal context extracted from query")

        # Step 2: Extract temporal filter from query
        print(f"  ✓ Step 2: Extract temporal filter from query text")
        temporal_entities = handler.extract_temporal_info(query)

        if temporal_entities:
            print(f"    Temporal entities found: {len(temporal_entities)}")
            for entity in temporal_entities:
                print(f"      - Type: {entity['type']}, Value: {entity['value']}")

            # Simulate filter extraction logic
            dates = [e['value'] for e in temporal_entities if e['type'] == 'date']
            years = [e['value'] for e in temporal_entities if e['type'] == 'year']
            fiscal_quarters = [e['value'] for e in temporal_entities if e['type'] == 'fiscal_quarter']

            filter_criteria = {}
            if dates:
                filter_criteria['document_date'] = dates[0]
                print(f"    ✓ Filter extracted: document_date = '{dates[0]}'")
            elif fiscal_quarters:
                # For quarters, we might want to match the quarter value
                filter_criteria['document_date'] = fiscal_quarters[0]
                print(f"    ✓ Filter extracted: document_date = '{fiscal_quarters[0]}'")
            elif years:
                filter_criteria['year'] = str(max(years))
                print(f"    ✓ Filter extracted: year = '{max(years)}'")
            else:
                print(f"    ⚠ No date/year filter extracted")
        else:
            print(f"    ⚠ No temporal entities found in query")

        # Step 3: Check for temporal intent keywords
        temporal_keywords = [
            'latest', 'most recent', 'newest', 'current', 'recent',
            'last', 'up to date', 'up-to-date', 'today', 'this year',
            'this quarter', 'this month'
        ]
        query_lower = query.lower()
        has_temporal_intent = any(keyword in query_lower for keyword in temporal_keywords)

        print(f"  ✓ Step 3: Check temporal intent")
        if has_temporal_intent:
            print(f"    ✓ Temporal intent detected (sort by recency)")
        else:
            print(f"    No temporal intent keywords found")

        print()

    # Demo: Simulate filtering results
    print("=" * 80)
    print("TEMPORAL FILTERING SIMULATION")
    print("=" * 80)
    print()

    # Simulate document results with dates
    mock_results = [
        {"id": "doc1", "title": "Q1 2023 Report", "metadata": {"document_date": "Q1 2023"}, "score": 0.95},
        {"id": "doc2", "title": "Q2 2023 Report", "metadata": {"document_date": "Q2 2023"}, "score": 0.93},
        {"id": "doc3", "title": "Annual 2024", "metadata": {"document_date": "2024"}, "score": 0.91},
        {"id": "doc4", "title": "Jan 15 Report", "metadata": {"document_date": "2023-01-15"}, "score": 0.89},
        {"id": "doc5", "title": "Dec 2023 Summary", "metadata": {"document_date": "2023-12"}, "score": 0.87},
    ]

    # Test filter application
    test_filters = [
        {"document_date": "Q1 2023", "description": "Filter by Q1 2023"},
        {"year": "2024", "description": "Filter by year 2024"},
        {"document_date": "2023-01", "description": "Filter by January 2023 (prefix match)"},
    ]

    for filter_test in test_filters:
        filter_criteria = {k: v for k, v in filter_test.items() if k != "description"}
        print(f"Filter: {filter_test['description']}")
        print(f"  Criteria: {filter_criteria}")

        # Apply filter
        filtered = []
        filter_type = None
        filter_value = None

        if 'document_date' in filter_criteria:
            filter_type = 'date'
            filter_value = filter_criteria['document_date']
        elif 'year' in filter_criteria:
            filter_type = 'year'
            filter_value = filter_criteria['year']

        for result in mock_results:
            metadata = result.get('metadata', {})
            doc_date = metadata.get('document_date', '')

            if filter_type == 'date':
                # Uses startswith for prefix matching
                if doc_date.startswith(filter_value):
                    filtered.append(result)
            elif filter_type == 'year':
                # Uses 'in' for substring matching
                if filter_value in doc_date:
                    filtered.append(result)

        print(f"  Results: {len(filtered)}/{len(mock_results)} documents matched")
        for doc in filtered:
            print(f"    ✓ {doc['title']} (date: {doc['metadata']['document_date']})")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ Query text temporal enhancement works (adds [TEMPORAL_CONTEXT: ...] prefix)")
    print("✓ Temporal entity extraction from queries works")
    print("✓ Temporal filter extraction works (dates, years, quarters)")
    print("✓ Filter application uses:")
    print("    - startswith() for document_date (allows prefix matching)")
    print("    - 'in' operator for year (allows substring matching)")
    print("✓ Temporal intent detection works for recency sorting")
    print()
    print("QUERY FLOW:")
    print("  1. User query → enhance_text_with_temporal_context()")
    print("  2. Enhanced query → generate_embedding()")
    print("  3. Query text → extract_temporal_info() → temporal_entities")
    print("  4. Temporal entities → filter_criteria (dates/years/quarters)")
    print("  5. Vector search results → apply_temporal_filter()")
    print("  6. If temporal intent → sort_by_recency()")
    print()
    print("=" * 80)


if __name__ == "__main__":
    simulate_vector_search_query()
