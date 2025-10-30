# Temporal Context RAG Agent

A production-ready Retrieval-Augmented Generation (RAG) system with temporal context awareness, table-aware chunking, and comprehensive citation tracking. Built with Google Cloud Vertex AI and FastAPI.

## Overview

This system provides advanced document processing and semantic search with:
- **Temporal Context Awareness**: Automatic date extraction and temporal enhancement of embeddings
- **Table-Aware Chunking**: Intelligent text chunking that preserves table integrity
- **GCS Import**: Directly import documents from Google Cloud Storage without re-uploading
- **Citation Tracking**: Comprehensive citations with clickable links and metadata
- **Production-Ready**: Vector Search with configurable algorithms (BruteForce/TreeAH)

---

## Quick Start

### Prerequisites
- Python 3.9+, Node.js 16+
- Google Cloud Project with enabled APIs: Vertex AI, Vector Search, Cloud Storage

### 1. Backend Setup

```bash
cd backend

# Setup environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit with your credentials
```

**Required `.env` variables:**
```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_AI_CORPUS_NAME=temporal-rag-corpus
GCS_BUCKET_NAME=your-bucket-name
EMBEDDING_MODEL_NAME=text-embedding-005
```

### 2. Start Services

```bash
# Authenticate
gcloud auth application-default login

# Start backend
python main.py  # http://localhost:8000

# Start frontend (new terminal)
cd frontend
npm install
npm start  # http://localhost:3000
```

### 3. Quick Test

**Chat Interface:**
```
1. Create a corpus for financial documents
2. Upload a PDF about Q4 2023
3. Query: "What was the revenue in Q4 2023?"
```

**API:**
```bash
# Create index
curl -X POST http://localhost:8000/index/create \
  -H "Content-Type: application/json" \
  -d '{"description": "Test index", "dimensions": 768}'

# Upload document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@report.pdf" \
  -F "document_date=2023-12-31"

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Q4 2023 revenue", "top_k": 5}'
```

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React + Material-UI)                              │
│  Chat | Query | Corpus Manager | Document Importer           │
└────────────────────┬─────────────────────────────────────────┘
                     │ REST API
┌────────────────────▼─────────────────────────────────────────┐
│  FastAPI Backend                                              │
│  • Document upload/GCS import • Text processing               │
└──┬────────────┬──────────────┬───────────────┬───────────────┘
   │            │              │               │
   ▼            ▼              ▼               ▼
┌──────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐
│Parser│  │ Chunker  │  │Embeddings│  │ Vector Search    │
│ PDF  │  │Table-    │  │Temporal  │  │BruteForce/TreeAH │
│DOCX  │  │Aware     │  │Enhanced  │  │DOT_PRODUCT       │
└──────┘  └──────────┘  └──────────┘  └──────────────────┘
```

### Core Components

**Backend Components:**
- `main.py`: FastAPI REST API with CORS
- `vector_search_manager.py`: Vector Search operations, GCS import, citation generation
- `temporal_embeddings.py`: Date extraction, temporal context enhancement
- `text_chunker.py`: Table-aware chunking with quality scoring
- `document_parser.py`: Multi-format text extraction (PDF, DOCX, TXT, MD)

**Frontend Components:**
- `ChatInterface.js`: Conversational UI with citations
- `QueryInterface.js`: Search UI with rich result cards
- `DocumentImporter.js`: File upload and GCS import UI
- `CorpusManager.js`: Index/endpoint management

---

## Pipeline Flow Diagrams

### Complete Document Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DOCUMENT INGESTION                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
         ┌──────────▼──────────┐       ┌───────────▼──────────┐
         │   File Upload       │       │   GCS Import         │
         │   (Frontend)        │       │   (gs://bucket/...)  │
         └──────────┬──────────┘       └───────────┬──────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT PARSING                                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐             │
│  │    PDF      │    DOCX     │    TXT      │     MD      │             │
│  │ pdfplumber  │  python-    │   UTF-8     │  Markdown   │             │
│  │ + pypdf     │   docx      │  Decode     │  Preserved  │             │
│  └─────┬───────┴─────┬───────┴─────┬───────┴─────┬───────┘             │
│        │             │             │             │                       │
│   ┌────▼─────────────▼─────────────▼─────────────▼────┐                │
│   │   TABLE DETECTION & EXTRACTION (PDF Only)          │                │
│   │   • Find tables using pdfplumber.find_tables()     │                │
│   │   • Validate: ≥2 rows, ≥2 columns, valid bbox     │                │
│   │   • Convert to markdown: [TABLE N]...[END TABLE]   │                │
│   │   • Extract text OUTSIDE table regions (anti-dup)  │                │
│   │   • Maintain document order by y-position          │                │
│   └─────────────────────┬──────────────────────────────┘                │
└─────────────────────────┼────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TEMPORAL CONTEXT EXTRACTION                           │
│  • Extract dates: YYYY-MM-DD, MM/DD/YYYY, Month Day Year               │
│  • Extract fiscal periods: Q1 2023, FY2023, H1 2024                    │
│  • Extract from filenames: "July 1st. 2025.PDF" → 2025-07-01          │
│  • Table-aware: Detect temporal data in tables (with column context)   │
│  • Deduplicate: Remove overlapping temporal references                 │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TABLE-AWARE CHUNKING                                │
│  1. Extract table positions: [TABLE N] markers                         │
│  2. Segment text: [text] [table] [text] [table] ...                    │
│  3. Chunk text segments: Hierarchical (headers → paragraphs → sentences)│
│  4. Keep tables ATOMIC: Never split mid-table                          │
│  5. Table-aware overlap: No overlap across table boundaries            │
│  6. Quality scoring: Different criteria for text vs table chunks       │
│                                                                          │
│  Output: List of chunks with metadata                                   │
│    • content, page_number, chunk_index, page_chunk_index               │
│    • has_table, table_count, has_complete_table                        │
│    • quality_score (0-1), sentence_count, word_count                   │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   TEMPORAL EMBEDDING ENHANCEMENT                         │
│  For each chunk:                                                        │
│    1. Extract temporal entities from chunk text                        │
│    2. Build temporal context prefix (max 200 chars):                   │
│       "[TEMPORAL_CONTEXT: Document Date: 2023-12-31 |                  │
│        Contains Table Data | Fiscal Quarters (Tabular): Q1 2023 |      │
│        Dates: 2023-01-15 | Years: 2023]"                               │
│    3. Prepend to chunk text                                            │
│    4. Generate embedding using Vertex AI (text-embedding-005)          │
│    5. Rate limit: 60 req/min, retry with exponential backoff           │
│                                                                          │
│  Output: 768-dimensional vectors with temporal awareness               │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   STORAGE & INDEXING                                     │
│  ┌──────────────────────────┐      ┌─────────────────────────────────┐ │
│  │  Google Cloud Storage    │      │  Vertex AI Vector Search        │ │
│  │  ──────────────────────  │      │  ─────────────────────────────  │ │
│  │  Original File (optional)│      │  • Upsert embeddings + metadata │ │
│  │  Chunk JSON (required)   │      │  • DOT_PRODUCT_DISTANCE         │ │
│  │  └─ Enhanced chunks      │      │  • BruteForce or TreeAH index   │ │
│  │  └─ Metadata             │      │  • Deployed on e2-standard-2    │ │
│  │  └─ Quality scores       │      │  • find_neighbors API           │ │
│  └──────────────────────────┘      └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘


                             QUERY PIPELINE
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                         USER QUERY                                       │
│  "What was the Q4 2023 revenue?" + optional temporal filters            │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  QUERY TEMPORAL ENHANCEMENT                              │
│  1. Extract temporal entities from query                                │
│  2. Build temporal context (same as document processing)                │
│  3. Generate query embedding (768-dim)                                  │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   VECTOR SIMILARITY SEARCH                               │
│  1. Call index_endpoint.find_neighbors(query_embedding)                │
│  2. Apply temporal filters (post-retrieval) if specified               │
│  3. Sort by DOT_PRODUCT score (higher = more similar)                  │
│  4. Return top_k results (default: 10)                                 │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CITATION GENERATION                                 │
│  For each result:                                                       │
│    • document_id, title, source (filename)                             │
│    • score, relevance (0.0-1.0+)                                       │
│    • page_number, chunk_index, page_chunk_index                        │
│    • quality_score (from chunking)                                     │
│    • original_file_url, clickable_link                                 │
│    • document_date (YYYY-MM-DD)                                        │
│    • formatted citation with all metadata                              │
│                                                                          │
│  Format: "Title (Page N, Chunk M) | Date: YYYY-MM-DD |                 │
│           Relevance: 0.XX | Source: filename.pdf"                      │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        RESULTS DISPLAY                                   │
│  Rich cards with:                                                       │
│    • Content snippet                                                    │
│    • Citation with clickable link                                      │
│    • Metadata chips (page, quality, date)                              │
│    • Relevance score badge                                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Table Extraction Detailed Flow (PDF Only)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PDF PAGE PROCESSING                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    ▼                                ▼
      ┌─────────────────────────┐      ┌────────────────────────┐
      │  1. TABLE DETECTION     │      │  2. TEXT EXTRACTION    │
      │  pdfplumber.find_tables │      │  (Done in parallel)    │
      └────────┬────────────────┘      └────────┬───────────────┘
               │                                 │
               ▼                                 │
      ┌─────────────────────────┐               │
      │  For each table_obj:    │               │
      │  • Validate bbox        │               │
      │    (not None, len≥4)    │               │
      │  • Extract table data   │               │
      │  • Filter empty rows    │               │
      │  • Validate structure:  │               │
      │    - ≥2 rows            │               │
      │    - ≥2 columns         │               │
      │  • Normalize columns    │               │
      │  • Convert to markdown  │               │
      └────────┬────────────────┘               │
               │                                 │
               ▼                                 │
      ┌─────────────────────────┐               │
      │  Valid tables ONLY:     │               │
      │  • [TABLE N] marker     │               │
      │  • Markdown table       │               │
      │  • [END TABLE] marker   │               │
      │  • Store bbox for       │               │
      │    text filtering       │               │
      └────────┬────────────────┘               │
               │                                 │
               └─────────────┬───────────────────┘
                             ▼
               ┌──────────────────────────────┐
               │  3. ANTI-DUPLICATION FILTER  │
               │  • Extract text in bands:    │
               │    - Before first table      │
               │    - Between tables          │
               │    - After last table        │
               │  • Filter chars by position: │
               │    EXCLUDE if inside bbox    │
               │  • Prevents text duplication │
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │  4. POSITION-BASED ASSEMBLY  │
               │  • Sort by y-coordinate      │
               │  • Interleave text & tables  │
               │  • Join with \n\n            │
               │  • Preserve document order   │
               └──────────────┬───────────────┘
                              ▼
                    ┌──────────────────┐
                    │  PAGE TEXT       │
                    │  (Order preserved│
                    │   No duplication)│
                    └──────────────────┘
```

### GCS Import vs File Upload Comparison

```
┌────────────────────────────────────┬────────────────────────────────────┐
│         FILE UPLOAD                │         GCS IMPORT                 │
├────────────────────────────────────┼────────────────────────────────────┤
│                                    │                                    │
│  User selects file from computer   │  User provides GCS path            │
│         ↓                          │         ↓                          │
│  Frontend uploads to backend       │  Backend reads from GCS            │
│         ↓                          │         ↓                          │
│  Backend receives bytes            │  Backend downloads bytes           │
│         ↓                          │         ↓                          │
│  Parse → Chunk → Embed             │  Parse → Chunk → Embed             │
│         ↓                          │         ↓                          │
│  STORE ORIGINAL FILE TO GCS ✗      │  SKIP STORING ORIGINAL ✓           │
│  (Duplicate storage ~50MB)         │  (Use existing file)               │
│         ↓                          │         ↓                          │
│  Store chunk JSON to GCS ✓         │  Store chunk JSON to GCS ✓         │
│  (~1.25MB for 125 chunks)          │  (~1.25MB for 125 chunks)          │
│         ↓                          │         ↓                          │
│  Upsert vectors to index ✓         │  Upsert vectors to index ✓         │
│         ↓                          │         ↓                          │
│  Metadata includes:                │  Metadata includes:                │
│    • gcs_chunk_url                 │    • original_file_url ✓           │
│    • source_url                    │    • gcs_source_path ✓             │
│    • uploaded_via: "upload"        │    • gcs_chunk_url                 │
│                                    │    • imported_from_gcs: true       │
│                                    │                                    │
│  Storage: ~51.25MB per doc         │  Storage: ~1.25MB per doc          │
│  Efficiency: ⭐⭐                   │  Efficiency: ⭐⭐⭐⭐⭐              │
│  Best for: Small batches           │  Best for: Bulk import             │
│                                    │           Existing GCS files       │
└────────────────────────────────────┴────────────────────────────────────┘

                        STORAGE SAVINGS EXAMPLE
        ┌─────────────────────────────────────────────────────┐
        │  100 PDFs @ 50MB each                               │
        │                                                      │
        │  File Upload:   5,125 MB (5.0 GB)                   │
        │  GCS Import:      125 MB (0.12 GB)                  │
        │                                                      │
        │  Savings:       5,000 MB (4.88 GB) - 97.6% less!   │
        └─────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. GCS Import (No Duplicate Storage)

Import documents directly from Google Cloud Storage:

```javascript
// Frontend API call
import { importFromGCS } from './api';

await importFromGCS(
  'gs://my-bucket/documents/',
  '2023-12-31',  // Optional document_date
  true           // recursive
);
```

**Storage Optimization:**
- ✅ Original files NOT re-uploaded (uses existing GCS URLs)
- ✅ Chunk JSON created (processed output with metadata)
- ✅ **Savings**: ~5GB per 100 large files

**Process Flow:**
```
gs://bucket/file.pdf (50MB)
  ↓ Download bytes
  ↓ Parse (page-by-page for PDFs, table detection)
  ↓ Chunk (1000 chars, 200 overlap, table-aware)
  ↓ Enhance with temporal context
  ↓ Generate embeddings (768-dim, batched)
  ↓ Store chunk JSON (~1.25MB for 125 chunks) ✅
  ↓ Upsert vectors to index ✅
  ↓ Save metadata ✅
```

**Metadata for GCS Imports:**
```json
{
  "original_file_url": "https://storage.cloud.google.com/existing-bucket/file.pdf",
  "gcs_source_path": "gs://existing-bucket/documents/file.pdf",
  "imported_from_gcs": true,
  "chunk_json_url": "https://storage.cloud.google.com/my-bucket/vector_search/.../chunk.json",
  "page_number": 2,
  "chunk_index": 42,
  "quality_score": 0.85
}
```

### 2. Temporal Context Enhancement

Automatic date extraction and embedding enhancement:

```python
# Original text
"Q4 2023 revenue was $10M in December"

# Enhanced text (before embedding)
"[TEMPORAL_CONTEXT: Document Date: 2023-12-31 | Contains dates: December 2023 | Years: 2023]
Q4 2023 revenue was $10M in December"
```

**Supported Date Formats:**
- ISO: `2023-12-31`
- US: `12/31/2023`
- Natural: `December 2023`, `Q4 2023`, `FY2023`
- Fiscal periods, quarters

### 3. Table-Aware Chunking

Intelligent chunking that preserves table integrity:

```
[TABLE 1]
| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q4 2023 | $10M    | 15%    |
[END TABLE]

Standard text continues here...
```

**Features:**
- Tables kept intact (not split mid-content)
- Large tables get dedicated chunks
- Quality scoring: 0-1 based on completeness, sentence boundaries
- Page tracking for PDFs
- Metadata: `has_table`, `table_count`, `has_complete_table`

### 4. Citation System

Comprehensive citations with all query results:

```json
{
  "content": "Q4 2023 revenue increased...",
  "score": 0.8756,
  "citation": {
    "title": "Q4 2023 Report",
    "filename": "report.pdf",
    "original_file_url": "https://storage.cloud.google.com/.../report.pdf",
    "page_number": 2,
    "chunk_index": 42,
    "page_chunk_index": 6,
    "quality_score": 0.85,
    "document_date": "2023-12-31",
    "imported_from_gcs": true
  }
}
```

**Frontend Display:**
```
┌────────────────────────────────────────────┐
│ 📄 Q4 2023 Report         [Relevance: 87.56%]│
│                                             │
│ "Q4 2023 revenue increased by 15%..."     │
│                                             │
│ 📍 Page 2, Chunk 6  ⭐ Quality: 85%        │
│ 📅 2023-12-31      📎 report.pdf           │
│                                             │
│ [🔗 View Source]                            │
└────────────────────────────────────────────┘
```

---

## API Reference

### Index Management

```bash
# Create index
POST /index/create
{
  "description": "Financial documents index",
  "dimensions": 768,
  "index_algorithm": "brute_force"  # or "tree_ah"
}

# Get index info
GET /index/info

# Clear datapoints
POST /index/clear

# Delete infrastructure
DELETE /index/delete
```

### Document Operations

```bash
# Upload file
POST /documents/upload
Content-Type: multipart/form-data
- file: PDF/DOCX/TXT/MD
- document_date: 2023-12-31 (optional)
- chunk_size: 1000 (optional)
- chunk_overlap: 200 (optional)

# Import from GCS
POST /documents/import_from_gcs
Content-Type: multipart/form-data
- gcs_path: gs://bucket/path/ or gs://bucket/file.pdf
- document_date: 2023-12-31 (optional)
- recursive: true (optional)

# Manual import
POST /documents/import
{
  "documents": [{
    "content": "Text content",
    "metadata": {
      "title": "Document Title",
      "document_date": "2023-12-31",
      "source_url": "https://example.com/doc.pdf"
    }
  }],
  "bucket_name": "optional-gcs-bucket"
}

# Get document by ID
GET /documents/{document_id}
```

### Querying

```bash
# Semantic search
POST /query
{
  "query": "What was Q4 2023 revenue?",
  "top_k": 5,
  "temporal_filter": {
    "document_date": "2023-12-31"
  }
}

# Chat
POST /chat
{
  "message": "User message",
  "conversation_history": [...],
  "session_id": "optional-session-id",
  "user_id": "default_user"
}

# Extract temporal entities
POST /temporal/extract
{
  "text": "Revenue was $10M in Q4 2023"
}
```

---

## Development

### Project Structure

```
agent-temporal-context/
├── backend/
│   ├── main.py                     # FastAPI REST API
│   ├── agent.py                    # AI agent orchestration and query processing
│   ├── vector_search_manager.py    # Vector Search + GCS import
│   ├── temporal_embeddings.py      # Temporal enhancement
│   ├── text_chunker.py             # Table-aware chunking
│   ├── document_parser.py          # Multi-format parsing
│   ├── config.py                   # Settings (pydantic-settings)
│   ├── logging_config.py           # Centralized logging
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.js        # Chat UI
│   │   │   ├── QueryInterface.js       # Search UI
│   │   │   ├── DocumentImporter.js     # Upload + GCS import
│   │   │   └── CorpusManager.js        # Index management
│   │   ├── App.js                      # Main app
│   │   └── api.js                      # API client
│   └── package.json
└── README.md
```

### Adding New API Endpoints

1. Add method to `vector_search_manager.py`:
```python
async def new_method(self, params):
    # Implementation
    return {"success": True, "data": result}
```

2. Add API endpoint in `main.py`:
```python
@app.post("/new_endpoint")
async def new_endpoint(request: NewRequest):
    result = await vector_search_manager.new_method(...)
    return {"success": True, "data": result}
```

3. Update frontend API client in `api.js`:
```javascript
export const newMethod = async (params) => {
  const response = await api.post('/new_endpoint', params);
  return response.data;
};
```

### Testing

```bash
# Backend
cd backend
pytest tests/

# Frontend
cd frontend
npm test
npm build  # Production build
```

### Docker Deployment

```bash
# Create .env with credentials
docker-compose up --build

# Access
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## Configuration

### Embedding Models

Supported Vertex AI models:

| Model | Dimensions | Use Case |
|-------|-----------|----------|
| `text-embedding-005` | 768 | Latest, best quality (default) |
| `text-embedding-004` | 768 | Previous generation |
| `textembedding-gecko@003` | 768 | Legacy/stable |

Configure via `EMBEDDING_MODEL_NAME` in `.env`.

### Index Algorithms

| Algorithm | Best For | Characteristics |
|-----------|----------|-----------------|
| `brute_force` | <10K docs | Fast queries, exact results |
| `tree_ah` | >10K docs | Approximate results, production scale |

### Chunking Configuration

```python
# Configurable per upload
chunk_size = 1000       # Characters per chunk
chunk_overlap = 200     # Overlap between chunks

# Default in TextChunker
TextChunker(
    chunk_size=1000,
    chunk_overlap=200,
    respect_structure=True  # Respect markdown/structure
)
```

---

## Troubleshooting

### Backend Issues

**Authentication:**
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Vector Search Errors:**
- Enable APIs: Vertex AI, Vector Search, Cloud Storage
- Index deployment takes 5-10 minutes
- Check quotas in GCP Console

**Embedding Errors:**
- Verify model name in `.env`
- Check Vertex AI API quota
- Ensure project has access to embedding models

### Frontend Issues

**CORS Errors:**
- Check `main.py` CORS configuration
- Verify `REACT_APP_API_URL` in frontend `.env`

**Citation Links Not Working:**
- Ensure documents have proper metadata
- Check GCS bucket permissions (public read or authenticated)
- Verify bucket name matches `.env`

### GCS Import Issues

**Path Not Found:**
- Verify `gs://bucket/path` format
- Check GCS bucket exists and is accessible
- Ensure files are supported types: pdf, docx, txt, md

**Import Fails:**
- Check file parsing errors in backend logs
- Verify sufficient GCS permissions (read access)
- Ensure embedding API quota available

---

## Best Practices

### Document Import
1. **Always provide metadata**: `title`, `document_date`, `source_url`
2. **Use GCS import for bulk**: Import entire folders recursively
3. **Add document dates**: Enables temporal filtering
4. **Descriptive titles**: Improves citation display

### Querying
1. **Natural language**: Write queries as questions
2. **Temporal filters**: Use for time-sensitive searches
3. **Adjust top_k**: 5-10 results recommended
4. **Review scores**: >0.7 = strong match, 0.5-0.7 = moderate

### Citations
1. **Include source_url**: For external documents
2. **Check clickable_link**: Before displaying in UI
3. **Open in new tab**: Better UX for source viewing
4. **Show metadata**: Page numbers, quality scores add context

### Performance
1. **Batch operations**: Import multiple documents together
2. **Use tree_ah**: For >10K documents
3. **Monitor quotas**: Embedding API, Vector Search
4. **Cache results**: Frontend caching for repeated queries

---

## Technologies

**Backend:**
- Python 3.9+, FastAPI
- Google Cloud Vertex AI (Embeddings, Vector Search)
- Google Cloud Storage
- Pydantic Settings

**Frontend:**
- React 18
- Material-UI (MUI)
- Axios

**AI Models:**
- text-embedding-005 (768 dimensions)

---

## License

MIT

## Support

- **API Docs**: http://localhost:8000/docs (Swagger/OpenAPI)
- **Logs**: Backend terminal + Browser DevTools Console
- **Issues**: Check GitHub repository
- **GCP Console**: Monitor Vector Search, quotas, storage

---

## Summary

This system provides a complete RAG solution with:
- ✅ **Temporal awareness** via date extraction and enhanced embeddings
- ✅ **Text processing** from PDF, DOCX, TXT, and Markdown files
- ✅ **GCS import** for efficient bulk document loading without re-uploading
- ✅ **Table-aware chunking** preserving data integrity
- ✅ **Comprehensive citations** with page numbers, quality scores, and metadata
- ✅ **Production-ready** Vector Search with configurable algorithms (BruteForce/TreeAH)
- ✅ **Modern React UI** with rich result display

Perfect for building intelligent document search systems with time-sensitive information, structured data (tables), and comprehensive source tracking.
