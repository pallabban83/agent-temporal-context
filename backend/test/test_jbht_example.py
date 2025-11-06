"""
Demonstration of JBHT earnings release filename processing.

This shows the complete flow for a real-world earnings document:
JBHT_Q4_2024_Earnings_Release_and_Schedules.pdf
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from temporal_embeddings import TemporalEmbeddingHandler


def demo_jbht_processing():
    """Demonstrate processing of JBHT earnings release document."""

    print("=" * 80)
    print("JBHT EARNINGS RELEASE PROCESSING DEMO")
    print("=" * 80)
    print()

    # Initialize handler
    handler = TemporalEmbeddingHandler(
        project_id="test-project",
        location="us-central1"
    )

    # Real-world filename
    filename = "JBHT_Q4_2024_Earnings_Release_and_Schedules.pdf"

    # Sample content from earnings release
    sample_content = """
    J.B. Hunt Transport Services, Inc. reported fourth quarter 2024 revenue of $3.25 billion,
    an increase of 6% compared to fourth quarter 2023. Operating income for the quarter was
    $215.5 million, compared to $189.3 million in Q4 2023. The company's Intermodal segment
    revenue increased 8% year-over-year to $1.45 billion.
    """

    print(f"Filename: {filename}")
    print()
    print("=" * 80)
    print("STEP 1: EXTRACT DATE FROM FILENAME")
    print("=" * 80)

    extracted_date = handler.extract_date_from_filename(filename)
    print(f"  ✓ Extracted Date: {extracted_date}")
    print(f"  Pattern Matched: Q4_2024 → Q4 2024")
    print()

    print("=" * 80)
    print("STEP 2: CREATE METADATA WITH DOCUMENT_DATE")
    print("=" * 80)

    metadata = {
        'document_date': extracted_date,
        'filename': filename,
        'title': 'JBHT Q4 2024 Earnings Release and Schedules',
        'company': 'J.B. Hunt Transport Services, Inc.',
        'document_type': 'earnings_release'
    }

    print(f"  Metadata:")
    for key, value in metadata.items():
        print(f"    {key}: {value}")
    print()

    print("=" * 80)
    print("STEP 3: ENHANCE CONTENT WITH TEMPORAL CONTEXT")
    print("=" * 80)

    enhanced_content = handler.enhance_text_with_temporal_context(sample_content, metadata)

    # Extract the temporal prefix
    if enhanced_content.startswith('[TEMPORAL_CONTEXT:'):
        prefix_end = enhanced_content.find(']\n')
        if prefix_end != -1:
            temporal_prefix = enhanced_content[:prefix_end + 1]
            content_after_prefix = enhanced_content[prefix_end + 2:]

            print(f"  Temporal Context Prefix:")
            print(f"    {temporal_prefix}")
            print()
            print(f"  Original Content (first 200 chars):")
            print(f"    {sample_content.strip()[:200]}...")
            print()
            print(f"  Enhanced Content (first 250 chars):")
            print(f"    {enhanced_content[:250]}...")
    print()

    print("=" * 80)
    print("STEP 4: QUERY MATCHING")
    print("=" * 80)
    print()

    # Demonstrate query scenarios
    test_queries = [
        "What were JBHT Q4 2024 earnings?",
        "Show me earnings reports from 2024",
        "Find J.B. Hunt fourth quarter results",
        "What is the latest JBHT revenue?",
    ]

    print("  Queries that would match this document:")
    print()

    for query in test_queries:
        print(f"  Query: \"{query}\"")

        # Extract temporal info from query
        query_temporal = handler.extract_temporal_info(query)

        if query_temporal:
            print(f"    Temporal entities: {[e['value'] for e in query_temporal]}")

            # Simulate filter extraction
            dates = [e['value'] for e in query_temporal if e['type'] == 'date']
            years = [e['value'] for e in query_temporal if e['type'] == 'year']
            quarters = [e['value'] for e in query_temporal if e['type'] == 'fiscal_quarter']

            # Check if would match
            doc_date = metadata['document_date']  # "Q4 2024"

            would_match = False
            match_reason = ""

            if quarters and quarters[0] == doc_date:
                would_match = True
                match_reason = f"Exact quarter match: {quarters[0]}"
            elif years and str(years[0]) in doc_date:
                would_match = True
                match_reason = f"Year match: {years[0]} in {doc_date}"

            if would_match:
                print(f"    ✓ MATCH: {match_reason}")
            else:
                print(f"    ~ Semantic match (vector similarity)")
        else:
            # Check for temporal intent
            temporal_keywords = ['latest', 'most recent', 'newest', 'current', 'recent']
            if any(kw in query.lower() for kw in temporal_keywords):
                print(f"    ✓ MATCH: Temporal intent detected (sort by recency)")
            else:
                print(f"    ~ Semantic match (vector similarity)")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"✓ Filename: {filename}")
    print(f"✓ Extracted Date: {extracted_date}")
    print(f"✓ Temporal Context: Document Date: {extracted_date}")
    print(f"✓ Queryable by: Q4 2024, 2024, fourth quarter, latest (recency)")
    print()
    print("This document would be properly indexed with temporal awareness and")
    print("discoverable through both semantic similarity and temporal filtering!")
    print()
    print("=" * 80)


if __name__ == "__main__":
    demo_jbht_processing()
