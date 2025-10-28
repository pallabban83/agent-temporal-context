# Sample Queries for Testing

Use these sample queries to test the Temporal Context RAG Agent.

## Example Documents

First, import the sample document in `examples/sample_document.txt` or use these sample documents:

### Document 1: Q4 2023 Report
```
Content: "Q4 2023 revenue was $15.2M, up 23% from Q4 2022's $12.4M. We launched our AI platform on November 15, 2023."
Metadata: {"document_date": "2023-12-31", "type": "financial_report"}
```

### Document 2: Q1 2024 Forecast
```
Content: "For Q1 2024, we project revenue between $16-17M based on strong Q4 2023 performance and new customer acquisition."
Metadata: {"document_date": "2024-01-15", "type": "forecast"}
```

### Document 3: Historical Data
```
Content: "In Q2 2022, we achieved our previous peak at $14.8M revenue before the Q3 2022 market downturn."
Metadata: {"document_date": "2022-06-30", "type": "historical_report"}
```

## Sample Queries

### Basic Queries

1. **Revenue in Q4 2023**
   ```
   Query: "What was the revenue in Q4 2023?"
   Expected: Should find Document 1 with $15.2M
   ```

2. **Recent launches**
   ```
   Query: "Tell me about product launches in November 2023"
   Expected: Should find AI platform launch on November 15, 2023
   ```

3. **Growth rate**
   ```
   Query: "What was the year-over-year growth rate?"
   Expected: Should find 23% growth from Document 1
   ```

### Temporal-Specific Queries

4. **Date range query**
   ```
   Query: "What happened between November and December 2023?"
   Temporal Filter: {"start_date": "2023-11-01", "end_date": "2023-12-31"}
   Expected: Should find platform launch and Q4 results
   ```

5. **Year-specific query**
   ```
   Query: "Financial performance"
   Temporal Filter: {"year": "2023"}
   Expected: Should prioritize 2023 documents
   ```

6. **Comparative query**
   ```
   Query: "Compare Q4 2023 with Q4 2022"
   Expected: Should find both revenue figures ($15.2M vs $12.4M)
   ```

### Complex Queries

7. **Trend analysis**
   ```
   Query: "How has revenue changed from 2022 to 2023?"
   Expected: Should find Q2 2022 ($14.8M), Q4 2022 ($12.4M), and Q4 2023 ($15.2M)
   ```

8. **Future projections**
   ```
   Query: "What is expected for 2024?"
   Expected: Should find Q1 2024 forecast ($16-17M)
   ```

9. **Event-based query**
   ```
   Query: "When did the company acquire DataFlow Systems?"
   Expected: Should find December 1, 2023
   ```

### Temporal Context Extraction

Test the temporal extraction endpoint with these texts:

1. **Extract dates from financial text**
   ```
   Text: "The merger was completed on March 15, 2024, with Q1 2024 results showing $18M revenue."
   Expected: Dates: March 15, 2024; Years: 2024
   ```

2. **Extract from news article**
   ```
   Text: "In January 2023, the company announced restructuring. By December 2023, performance improved significantly."
   Expected: Dates: January 2023, December 2023; Years: 2023
   ```

## Chat Interface Examples

Use these conversational prompts in the chat interface:

1. "Create a corpus for financial reports"
2. "Import the Q4 2023 financial report with revenue data"
3. "What was our revenue in the last quarter of 2023?"
4. "Show me all documents from November 2023"
5. "Compare our performance between 2022 and 2023"
6. "What products did we launch in 2023?"
7. "Extract temporal information from: 'Revenue grew 25% in Q1 2024 compared to Q1 2023'"

## Expected Behavior

### Temporal Context Enhancement

When importing documents, the system should:
1. Extract date entities (November 15, 2023, December 31, 2023, etc.)
2. Enhance the embedding with temporal markers
3. Store temporal metadata for filtering

### Query Processing

When querying, the system should:
1. Detect temporal context in the query ("Q4 2023", "November 2023")
2. Generate temporally-aware embeddings
3. Apply temporal filters if specified
4. Return results ranked by semantic similarity and temporal relevance

### Agent Behavior

The chat agent should:
1. Understand natural language requests for corpus operations
2. Execute appropriate tools (create_corpus, import_documents, query_corpus)
3. Provide clear responses with tool execution results
4. Handle multi-turn conversations with context
