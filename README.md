# Temporal Context RAG Agent

A production-ready Retrieval-Augmented Generation (RAG) system with temporal context awareness, table-aware chunking, and comprehensive citation tracking. Built with Anthropic's Claude, Google Cloud Vertex AI, and FastAPI.

## Overview

This system provides advanced document processing and semantic search with:
- **Temporal Context Awareness**: Automatic date extraction and temporal enhancement of embeddings
- **Table-Aware Chunking**: Intelligent text chunking that preserves table integrity
- **GCS Import**: Directly import documents from Google Cloud Storage without re-uploading
- **Citation Tracking**: Comprehensive citations with clickable links and metadata
- **Conversational Interface**: Natural language interaction via Claude 3.5 Sonnet
- **Production-Ready**: Vector Search with configurable algorithms (BruteForce/TreeAH)

---

## Quick Start

### Prerequisites
- Python 3.9+, Node.js 16+
- Google Cloud Project with enabled APIs: Vertex AI, Vector Search, Cloud Storage
- Anthropic API key

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
ANTHROPIC_API_KEY=sk-ant-xxxxx
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
- `agent.py`: Claude 3.5 Sonnet agent with tool execution
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
│   ├── agent.py                    # Claude agent with tools
│   ├── main.py                     # FastAPI REST API
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

### Adding Agent Tools

1. Define tool schema in `agent.py`:
```python
self.tools.append({
    "name": "new_tool",
    "description": "Tool description",
    "input_schema": {...}
})
```

2. Implement in `execute_tool()`:
```python
if tool_name == "new_tool":
    result = self.vector_search_manager.new_method(...)
    return {"success": True, "data": result}
```

3. Add API endpoint in `main.py`:
```python
@app.post("/new_endpoint")
async def new_endpoint(request: NewRequest):
    result = await agent.vector_search_manager.new_method(...)
    return {"success": True, "data": result}
```

4. Update frontend API client in `api.js`:
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
- Anthropic Claude 3.5 Sonnet (ADK)
- Google Cloud Vertex AI (Embeddings, Vector Search)
- Google Cloud Storage
- Pydantic Settings

**Frontend:**
- React 18
- Material-UI (MUI)
- Axios

**AI Models:**
- Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
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
- ✅ **Conversational interface** via Claude 3.5 Sonnet agent
- ✅ **Modern React UI** with rich result display

Perfect for building intelligent document search systems with time-sensitive information, structured data (tables), and comprehensive source tracking.
