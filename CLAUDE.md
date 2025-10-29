# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Temporal Context Vector Search Agent** system that combines:
- **Anthropic's Agent Development Kit (ADK)** for conversational AI capabilities
- **Vertex AI Vector Search** for direct vector similarity search
- **FastAPI** for the REST API backend
- **React** for the web UI frontend

The agent specializes in handling documents with temporal context (date-specific information), creating embeddings that maintain temporal awareness, and enabling time-sensitive semantic search using direct Vector Search without RAG Corpus abstraction.

## Development Commands

### Backend Setup and Running

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Authenticate with Google Cloud
gcloud auth application-default login

# Run the server (development)
python main.py

# Or use the run script
./run.sh

# Run with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup and Running

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm build

# Run tests
npm test
```

### Docker Setup

```bash
# Run both backend and frontend
docker-compose up

# Rebuild containers
docker-compose up --build

# Run in detached mode
docker-compose up -d
```

## Architecture Overview

### Backend Architecture

1. **Agent Layer** (`agent.py`)
   - Implements ADK-based conversational agent using Claude
   - Defines tools for document import and querying
   - Handles multi-turn conversations with tool execution
   - Main class: `TemporalRAGAgent`

2. **Temporal Embeddings** (`temporal_embeddings.py`)
   - Extracts temporal information from text (dates, years)
   - Enhances text with temporal context markers before embedding
   - Generates embeddings using Vertex AI textembedding-gecko model
   - Key class: `TemporalEmbeddingHandler`
   - Pattern: Text → Extract temporal info → Add context markers → Generate embedding

3. **Vector Search Management** (`vector_search_manager.py`)
   - Creates and manages Vertex AI Vector Search indices directly
   - Handles document import with temporal metadata
   - Performs semantic search with optional temporal filtering using find_neighbors API
   - Stores documents in Google Cloud Storage
   - Key class: `VectorSearchManager`

4. **API Layer** (`main.py`)
   - FastAPI application with REST endpoints
   - CORS-enabled for frontend integration
   - Endpoints for index creation, document import, querying, and chat
   - File upload support with multipart/form-data

### Frontend Architecture

1. **Main App** (`App.js`)
   - Tab-based interface with 4 main views
   - Material-UI theming and layout
   - State management for active tab

2. **Components**
   - `ChatInterface`: Conversational UI for natural language interaction with the agent
   - `IndexManager`: Create and manage Vector Search index and endpoint
   - `DocumentImporter`: Upload files or manually add documents with temporal metadata
   - `QueryInterface`: Search with temporal filtering and analyze temporal context

3. **API Client** (`api.js`)
   - Axios-based HTTP client
   - Centralized API calls to backend
   - Base URL configuration via environment variable

### Data Flow

1. **Document Import Flow**
   - User uploads document → Extract temporal info → Add metadata → Generate embedding → Upsert to Vector Search index + Store in GCS

2. **Query Flow**
   - User query → Extract temporal context → Generate query embedding → find_neighbors API with temporal filters → Return results

3. **Chat Flow**
   - User message → Agent with tools → Tool execution (import/query) → Agent response

## Key Implementation Details

### Temporal Context Handling

The system enhances embeddings with comprehensive temporal awareness:

**Temporal Entity Extraction:**
1. **Date Formats**: YYYY-MM-DD, MM/DD/YYYY, M/D/YYYY, natural language dates
2. **Fiscal Periods**: Q1 2023, FY2023, Fiscal Year 23, H1 2023
3. **Month-Year**: January 2023, December 2024
4. **Relative Dates**: "last quarter", "three months ago", "this year"
5. **Years**: 2023, 2024, etc.

**Embedding Enhancement:**
Text is enhanced with temporal context before embedding, with table awareness and length limits:
```
[TEMPORAL_CONTEXT: Document Date: 2023-12-31 | Contains Table Data | Fiscal Quarters (Tabular): Q1 2023, Q2 2023 | Dates: 2023-01-15 | Years: 2023]
<original text>
```

**Temporal Context Length Management:**
- Maximum prefix length: 200 characters
- If context exceeds limit, it's intelligently truncated:
  - Finds last complete item (separated by `|`)
  - Adds `...` indicator to show truncation
  - Logs truncation for monitoring
- Prevents temporal context from dominating chunk content
- Ensures consistent embedding model input sizes

**Table-Aware Temporal Extraction:**
When temporal entities are found inside tables:
- System detects entity position within table structure
- Extracts column header context (e.g., "Quarter" column)
- Marks temporal data as tabular in context prefix
- Example: "Q1 2023" in a Revenue table → "Fiscal Quarters (Tabular): Q1 2023"

This allows the embedding model to:
- Capture temporal relationships AND structural context
- Understand fiscal periods and quarters IN TABLES
- Improve retrieval for time-sensitive queries with tabular data
- Handle business-specific temporal references in structured formats
- Distinguish between narrative mentions and tabular data
- Maintain reasonable embedding sizes (context limited to 20% of chunk max)

### ADK Agent Tools

The agent exposes 3 tools:
1. `import_documents` - Batch import with temporal enhancement and direct upsert to Vector Search
2. `query_index` - Semantic search using find_neighbors API with temporal filtering
3. `extract_temporal_context` - Analyze text for temporal entities

### Table Extraction & Handling

The system intelligently extracts, preserves, and handles tabular data from PDFs with comprehensive table-aware chunking:

**Table Detection & Extraction:**
- Uses `pdfplumber` for accurate table boundary detection
- Automatically identifies tables in PDFs (no configuration needed)
- **Anti-Duplication**: Extracts text OUTSIDE table regions to prevent duplication
- **Global Table Numbering**: Tables numbered consecutively across all pages (not per-page)
- **Validation**: Tables must have ≥2 rows and ≥2 columns
- Preserves table structure and relationships

**Table Conversion:**
Tables are converted to well-formed markdown format for LLM comprehension:
- **Row Alignment**: All rows padded to match maximum column count
- **Empty Row Filtering**: Rows with all empty cells are skipped
- **Consistent Formatting**: Proper markdown table structure guaranteed
```markdown
[TABLE 1]
| Quarter | Revenue | Profit |
| ------- | ------- | ------ |
| Q1 2023 | $100M   | $20M   |
| Q2 2023 | $120M   | $25M   |
[END TABLE]
```

**Table-Aware Chunking (CRITICAL):**
The chunker now protects table integrity during splitting:

1. **Atomic Table Preservation**: Tables are NEVER split mid-table
   - `[TABLE N]...[END TABLE]` blocks are treated as atomic units
   - If a table exceeds chunk_size, it's kept intact in a single chunk
   - Prevents broken markdown table formatting

2. **Smart Overlap Logic**: Overlap avoids table boundaries
   - No overlap when chunks end/start with tables
   - Minimal overlap (100 chars max) when tables are nearby
   - Full overlap only for pure text chunks
   - Overlap attempts to start at sentence boundaries

3. **Table-Aware Quality Scoring**: Different criteria for table chunks
   - Complete tables receive high quality scores (0.8-1.0)
   - Partial tables (broken across chunks) are penalized
   - Chunks with tables + text context get bonus points
   - Tables don't get penalized for lacking sentence punctuation

4. **Enhanced Table Detection**: Robust table metadata
   - `has_table`: Any table markers present
   - `table_count`: Number of tables in chunk
   - `has_complete_table`: Complete table with both markers

**Temporal Extraction from Tables:**
The system now extracts temporal context FROM tables:
- Detects when temporal entities are inside table cells
- Extracts column header context (e.g., "Q1 2023" is in "Quarter" column)
- Marks fiscal quarters in tables as "Fiscal Quarters (Tabular)"
- Enhanced embedding context for table-based temporal data

**Benefits:**
- **Structure Preserved**: Tables never broken mid-table
- **LLM-Friendly**: Markdown tables are easily understood by embeddings
- **Searchable**: Can query "Q1 2023 revenue" and find correct table data
- **Context-Aware**: Temporal extraction knows when data is tabular
- **High Quality**: Table chunks receive appropriate quality scores

**Document Metadata:**
- `has_tables`: Boolean indicating if PDF contains tables
- `total_tables`: Count of tables in document
- `pages_with_tables`: List of page numbers with tables

**Chunk Metadata:**
- `has_table`: Boolean if chunk contains ANY table markers
- `table_count`: Number of `[TABLE` markers in chunk
- `has_complete_table`: Boolean if chunk has complete table(s)
- `quality_score`: 0-1 score with table-aware criteria

### Text Chunking Strategy

The system uses table-aware semantic chunking with intelligent quality metrics:

**Chunking Features:**
- **Table-First Protection**: Extracts table positions BEFORE chunking to prevent mid-table splits
- **Semantic Boundaries**: Respects markdown headers, paragraphs, lists, and table boundaries
- **Structure Preservation**: Keeps structured content (headings, lists, tables) intact
- **Smart Overlapping**: Table-aware overlap logic
  - No overlap across table boundaries (prevents broken tables)
  - Sentence-level overlap for pure text chunks
  - Minimal overlap (100 chars) near tables
  - Full overlap (configurable) for text-only chunks
- **Atomic Table Handling**: Tables treated as indivisible units during chunking
- **Quality Scoring**: Each chunk gets a quality score (0-1) with table-specific criteria:
  - Text chunks: Sentence completeness, capitalization, size variance
  - Table chunks: Complete table markers, contextual text, structural integrity
  - Hybrid chunks: Bonus for having both table and text context

**Chunking Algorithm:**
1. Extract and locate all `[TABLE N]...[END TABLE]` blocks (with validation)
   - Skip empty or malformed tables (< 5 chars)
   - Log warnings for very large tables (> 2x chunk_size)
   - Track table positions and sizes
2. Split text into segments: [text, table, text, table, ...]
   - Preserve minimal whitespace between segments
   - Handle consecutive tables gracefully
3. Chunk each text segment normally using hierarchical separators
4. Keep all table segments intact (atomic units - NEVER split)
5. Merge segments with table-aware overlap logic
   - No overlap across table boundaries
   - Sentence-level overlap for pure text
   - Minimal overlap near tables
6. Score chunks with table-specific quality criteria
   - Empty chunks receive 0.0 score
   - Table chunks use different criteria than text chunks

**Oversized Table Handling:**
When tables exceed 2× chunk_size:
- Table is kept intact (atomic) despite size
- Warning logged for visibility
- Table chunk is NEVER merged with other content
- Prevents creating super-massive merged chunks
- Example: 5000-char table with 1000-char chunk_size stays as single 5000-char chunk

**Edge Cases Handled:**
- Empty or whitespace-only chunks (scored 0.0)
- Malformed tables (missing markers, empty content)
- Very large tables exceeding chunk_size (kept atomic, no merging)
- Oversized chunks (>2× chunk_size, isolated from merging)
- Consecutive tables with minimal spacing
- Tables with no headers or separator lines
- Temporal entities in table separator lines (skipped)
- Empty pages (skipped entirely from output)
- Temporal context exceeding length limits (intelligently truncated)

**Chunk Metadata Includes:**
- `quality_score`: 0-1 quality rating (table-aware)
- `sentence_count`: Number of complete sentences (excluding table content)
- `word_count`: Total word count
- `chunk_size`: Character count
- `page_number`: For PDFs
- `chunk_index`: Position in document
- `has_table`: Boolean if contains ANY table markers
- `table_count`: Number of `[TABLE` markers
- `has_complete_table`: Boolean if all tables are complete

**Default Settings:**
- Chunk size: 1000 characters (configurable, tables can exceed this)
- Overlap: 200 characters (configurable, reduced/disabled near tables)
- Hierarchical separators: Headers → Paragraphs → Lists → Sentences → Words
- Table handling: Atomic (never split)
- PDF chunking: Uses table-aware method (same as TXT/DOCX)

**Implementation Notes:**
- Both `chunk_text()` and `chunk_pdf_by_pages()` use table-aware chunking
- Quality metrics are consistently extracted for all document types
- Logging provides visibility into table detection and large table warnings
- Error handling prevents crashes from malformed tables or edge cases

### Vector Search Configuration

- **Distance Measure**: DOT_PRODUCT_DISTANCE (for normalized embeddings)
- **Index Type**: Tree-AH (Approximate Hierarchical)
- **Embedding Dimensions**: 768 (textembedding-gecko)
- **Approximate Neighbors**: 10
- **Machine Type**: e2-standard-2 (for endpoint)

### Citation System

The citation system provides comprehensive source attribution with relevance scores, page numbers, chunk locations, and clickable document URLs.

**Citation Fields:**
- **Core**: document_id, title, source (filename)
- **Relevance**: score, relevance (from vector search, 0.0-1.0+)
- **Location**: page_number, chunk_index, page_chunk_index
- **Quality**: quality_score (from chunking algorithm)
- **URLs**: original_file_url (prioritized), source_url, gcs_chunk_url, clickable_link
- **Temporal**: date (document date in YYYY-MM-DD)
- **Formatted**: formatted (pipe-separated), formatted_with_link (with URL)

**Citation Format Example:**
```
Q2_2025_Earnings_Release (Page 2, Chunk 6) | Date: 2025-07-15 | Relevance: 0.7523 | Source: earnings.pdf
View Document: https://storage.cloud.google.com/...
```

**Implementation:**
- Method: `VectorSearchManager._format_citation(doc_id, doc_info, score=None)`
- Query results: Include relevance score from vector search
- Document retrieval: No score (direct fetch)
- Location priority: Page + page-level chunk > Page only > Global chunk > No location
- URL priority: Original file > Source URL > Chunk URL

**Use Cases:**
- `formatted_with_link`: Rich text display with clickable URLs (recommended for UI)
- `formatted`: Clean text without URLs (for logging, exports)
- Individual fields: Custom UI components (cards, lists, etc.)

**Documentation:** See `backend/CITATION_FORMAT.md` for detailed examples and best practices.

## Document Parsing Pipeline

### PDF Processing Flow

The document parser (`document_parser.py`) implements a sophisticated multi-stage process:

**Stage 1: Table Extraction (Synchronized)**
1. Find tables using `pdfplumber.page.find_tables()` (returns table objects)
2. For each table object:
   - Extract table data using `table_obj.extract()`
   - Validate table (minimum 2 rows × 2 columns)
   - Filter empty rows from table data
   - Normalize row lengths by padding short rows
   - Convert to markdown format
   - **Only if validation passes**: Add both markdown AND bbox
3. Assign global table numbers (sequential across all pages)
4. **Synchronization**: Table markdown and bboxes are from the SAME table objects

**Stage 2: Text Extraction (Anti-Duplication)**
1. Use bboxes from validated tables ONLY
2. Filter page characters to exclude those inside table bounding boxes
3. Extract only text OUTSIDE table regions
4. This prevents duplicate data (text already in tables)

**Stage 3: Page Assembly**
1. Combine non-table text with table markdown
2. Use global table numbering: `[TABLE 1]`, `[TABLE 2]`, etc.
3. Skip completely empty pages (don't add to page_texts)
4. Build page_texts array for chunking

**Critical Fixes Implemented (Reviews 1-3):**
- ✅ **Synchronized Table Detection**: Data and bboxes from same source (no mismatch)
- ✅ **No Text Duplication**: Text inside tables is NOT duplicated in regular text
- ✅ **Global Table IDs**: Tables numbered 1, 2, 3... across entire document
- ✅ **Valid Markdown**: All table rows have consistent column counts
- ✅ **Clean Tables**: Empty rows filtered, minimum size enforced
- ✅ **Proper Structure**: Tables validated before conversion
- ✅ **No Invalid Bboxes**: Only validated tables contribute to text filtering
- ✅ **Empty Page Handling**: Empty pages skipped entirely

**Critical Fixes Implemented (4th Review):**
- ✅ **Table Position Preservation**: Tables maintain original document order (not moved to end)
  - Implemented band-based text extraction between tables
  - Added `_extract_text_in_band()` method for precise text segmentation
  - Text and tables interleaved based on y-coordinates
- ✅ **Validation Timing Fix**: `pages_with_tables` populated only AFTER table validation
  - Prevents incorrect page numbers for failed validation cases
- ✅ **Accurate Page Count**: `total_pages` returns actual PDF page count
  - Added `non_empty_pages` for content-bearing page count
  - Properly tracks empty pages vs total pages
- ✅ **Year Duplication Prevention**: Years not duplicated in temporal context
  - Years excluded when already captured in dates, month_years, or fiscal_years
  - Prevents "[TEMPORAL_CONTEXT: Periods: December 2023 | Years: 2023]" redundancy
- ✅ **Size Variance Penalty for Tables**: Quality scoring applied to oversized table chunks
  - Moderate penalty (0.15) for tables > 2x chunk_size
  - Significant penalty (0.3) for tables > 3x chunk_size
  - Helps identify problematically large tables
- ✅ **Empty Bbox Edge Case**: Properly handles pages with no validated tables
  - Empty table list → extracts all text correctly
  - Maintains consistent behavior across all scenarios

**Additional Fixes Implemented (5th Review):**
- ✅ **Overlapping Table Validation**: Skip invalid bands when tables overlap vertically
  - Added band height validation (`band_bottom > band_top`) before extraction
  - Prevents inefficient filtering operations on impossible bands
  - Logs debug message when overlapping tables detected
- ✅ **Position-Based Column Detection**: Accurate table column identification for duplicate values
  - Replaced substring matching with character position-based detection
  - Correctly identifies column even when same value appears multiple times
  - Example: "2023-01-01" in both "Date" and "End Date" columns now correctly distinguished
- ✅ **non_empty_pages Metadata**: Expose content-bearing page count to users
  - Added `non_empty_pages` field to chunk metadata
  - Users can now distinguish total pages from pages with actual content
  - Example: 10-page PDF with 2 blank pages shows total_pages=10, non_empty_pages=8
- ✅ **Optimized Spacing**: Reduced excessive whitespace between content blocks
  - Removed redundant newlines from table markers
  - Changed from 4 newlines to 2 newlines between sections
  - Spacing now handled consistently by join operation
- ✅ **Pattern Optimization**: Removed duplicate date pattern for better performance
  - Eliminated redundant `\d{2}/\d{2}/\d{4}` pattern (covered by general pattern)
  - Reduces duplicate matches during temporal extraction
  - Deduplication logic now has less work to do
- ✅ **Code Clarity**: Removed unnecessary capturing groups from regex patterns
  - Changed capturing groups to non-capturing `(?:...)` where appropriate
  - Improves regex performance slightly
  - Makes patterns clearer and less confusing

### Supported Document Types

- **PDF**: Full table extraction with anti-duplication (recommended)
- **DOCX**: Text extraction from paragraphs
- **TXT/MD**: Plain text with markdown preservation

## Important Files

- `backend/agent.py` - ADK agent implementation with tool definitions
- `backend/temporal_embeddings.py` - Temporal context extraction and embedding enhancement
- `backend/vector_search_manager.py` - Direct Vector Search operations using find_neighbors API (includes citation formatting)
- `backend/document_parser.py` - PDF/DOCX parsing with advanced table extraction
- `backend/text_chunker.py` - Semantic chunking with quality metrics and table awareness
- `backend/main.py` - FastAPI application and API endpoints
- `backend/config.py` - Settings management with pydantic-settings
- `backend/logging_config.py` - Centralized logging framework with JSON/LOGFMT support
- `backend/CITATION_FORMAT.md` - Citation system documentation with examples
- `backend/LOGGING.md` - Logging framework usage and best practices
- `frontend/src/api.js` - API client for backend communication
- `frontend/src/components/` - React UI components

## Environment Configuration

Required environment variables (backend):
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - GCP region (e.g., us-central1)
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- `VERTEX_AI_CORPUS_NAME` - Name for the Vector Search index
- `VECTOR_SEARCH_INDEX` - Optional pre-existing index resource name
- `VECTOR_SEARCH_INDEX_ENDPOINT` - Optional pre-existing endpoint resource name

## Working with the Codebase

### Adding New Agent Tools

1. Define tool function in `agent.py` as an async method
2. Add the method to `self.agent` tools list
3. Add corresponding method to `VectorSearchManager` if needed
4. Create API endpoint in `main.py`
5. Update frontend API client in `api.js`

### Modifying Temporal Context Logic

- Edit `TemporalEmbeddingHandler.extract_temporal_info()` for new date patterns
- Modify `enhance_text_with_temporal_context()` for different context formatting
- Update tests to cover new temporal patterns

### Modifying Query Logic

- Query logic is in `VectorSearchManager.query()` method
- Uses `index_endpoint.find_neighbors()` API for similarity search
- Temporal filtering is applied post-retrieval
- Results are sorted by score (DOT_PRODUCT_DISTANCE - higher is better)

### Adding New API Endpoints

1. Create Pydantic request/response models in `main.py`
2. Implement endpoint with proper error handling
3. Add corresponding function in `frontend/src/api.js`
4. Create or update React component to use the endpoint

## Testing

Backend testing approach:
- Use pytest for unit and integration tests
- Mock Google Cloud services for unit tests
- Use test fixtures for sample documents with temporal data

Frontend testing:
- Jest for component tests
- React Testing Library for UI interaction tests
- Mock API responses for isolated component testing
