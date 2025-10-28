# Temporal Context RAG Agent

A Retrieval-Augmented Generation (RAG) agent with temporal context awareness and citation tracking, built using Anthropic's Agent Development Kit (ADK), Vertex AI, and FastAPI.

## Overview

This project implements a RAG agent that:
- Creates and manages RAG corpora using Vertex AI Vector Search
- Handles documents with temporal context (date-specific information)
- Generates embeddings with temporal awareness using the latest Vertex AI models
- Provides comprehensive citation tracking with clickable links to source documents
- Offers a conversational interface through ADK
- Exposes functionality via FastAPI REST API
- Includes a React-based web UI with rich citation display

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Citation System](#citation-system)
- [Setup](#detailed-setup)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Frontend UI](#frontend-ui)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- Google Cloud Project with Vertex AI, Vector Search, and Cloud Storage APIs enabled
- Anthropic API key

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

Required `.env` variables:
```env
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
ANTHROPIC_API_KEY=sk-ant-xxxxx
VERTEX_AI_CORPUS_NAME=temporal-context-corpus
GCS_BUCKET_NAME=your-bucket-name
EMBEDDING_MODEL_NAME=text-embedding-004
```

### 2. Authenticate & Start Backend

```bash
gcloud auth application-default login
python main.py
```

API available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

UI available at `http://localhost:3000`

### 4. Quick Test

**Via Chat Interface:**
1. Go to "Chat" tab
2. "Create a new corpus for financial documents"
3. "Import a document about Q4 2023 earnings with revenue of $10M"
4. "What was the revenue in Q4 2023?"

**Via API:**
```bash
# Create corpus
curl -X POST http://localhost:8000/corpus/create \
  -H "Content-Type: application/json" \
  -d '{"description": "Test corpus", "dimensions": 768}'

# Import document
curl -X POST http://localhost:8000/documents/import \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "Q4 2023 revenue was $10M",
      "metadata": {
        "document_date": "2023-12-31",
        "title": "Q4 2023 Report"
      }
    }]
  }'

# Query with citations
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the revenue?", "top_k": 5}'
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface (React)                      │
│  ChatInterface | QueryInterface | CorpusManager | DocumentImporter│
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (main.py)                     │
│  • Document Upload • Query Processing • Corpus Management       │
└────────────┬──────────────────┬─────────────────────────────────┘
             │                  │
             ▼                  ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│  Multimodal Parser   │  │  TemporalRAGAgent (agent.py)         │
│  • Extract images    │  │  • Claude 3.5 Sonnet                 │
│  • Vision API OCR    │  │  • Tool execution                    │
│  • GCS upload        │  │  • Conversation management           │
└──────────┬───────────┘  └──────────┬───────────────────────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│   Text Chunker       │  │  Vertex RAG Manager                  │
│  • Smart chunking    │  │  • Vector Search operations          │
│  • Image context     │  │  • Document storage (GCS)            │
│  • Page tracking     │  │  • Citation generation               │
└──────────┬───────────┘  └──────────┬───────────────────────────┘
           │                         │
           └─────────┬───────────────┘
                     ▼
           ┌──────────────────────┐
           │ Temporal Embeddings  │
           │  • Extract dates     │
           │  • Enhance context   │
           │  • Generate vectors  │
           └──────────┬───────────┘
                      │
                      ▼
           ┌─────────────────────────────────────┐
           │  Vertex AI Services                 │
           │  • text-embedding-004 (768-dim)     │
           │  • Vision API (label/OCR/objects)   │
           │  • Vector Search (BruteForce/TreeAH)│
           └─────────────────────────────────────┘
```

### Backend Components

#### 1. Multimodal Document Parser (`multimodal_parser.py`)
- **Image Extraction**: Extracts images from PDF and DOCX files
- **Vision API Integration**:
  - Label detection (what's in the image)
  - OCR text detection (text within images)
  - Object detection (specific objects)
- **GCS Storage**: Uploads images with public URLs
- **Description Generation**: Creates searchable descriptions for images

#### 2. Text Chunker (`text_chunker.py`)
- **Smart Chunking**: 1000 characters per chunk, 200 character overlap
- **Hierarchical Splitting**: Paragraphs → Sentences → Words → Characters
- **Page-Aware**: Tracks page numbers for PDFs
- **Image Context Embedding**: Includes image descriptions in chunk text
- **Metadata Preservation**: Maintains all document metadata per chunk

Example chunk with image:
```
Content: "[IMAGE 1: Screenshot showing database settings dialog | OCR: Database Configuration Host: localhost Port: 5432]\n\nStep 1: Open database settings..."
Images: [{"url": "https://storage.googleapis.com/.../image.png", "description": "Screenshot showing..."}]
Metadata: {"page_number": 3, "has_images": true, "image_count": 1}
```

#### 3. Temporal Embedding Handler (`temporal_embeddings.py`)
- **Temporal Extraction**: Detects dates (YYYY-MM-DD, MM/DD/YYYY, natural language)
- **Context Enhancement**: Prepends temporal markers to text before embedding
- **Vertex AI Integration**: Uses `text-embedding-004` (768 dimensions)
- **Batch Processing**: Efficient batch embedding generation

Example temporal enhancement:
```
Original: "Revenue was $10M in December 2023"
Enhanced: "[TEMPORAL_CONTEXT: Contains dates: December 2023 | Relevant years: 2023] Revenue was $10M in December 2023"
```

Combined with image context:
```
"[TEMPORAL: 2024-01-15] [IMAGE: Setup wizard screenshot | OCR: Step 1] Click the settings button..."
```

#### 4. Vertex RAG Manager (`vertex_rag_manager.py`)
- **Vector Search Management**: Creates BruteForce or TreeAH indices with StreamUpdate
- **Document Storage**: Individual document storage in GCS for citations
- **Citation Generation**: Automatic GCS Console URL generation
- **Metadata Tracking**: Full document metadata cache with images
- **Temporal Filtering**: Date-based query filtering
- **Image Preservation**: Maintains image URLs and descriptions in results

#### 5. ADK Agent (`agent.py`)
- **Claude Integration**: Uses `claude-3-5-sonnet-20241022`
- **Tool Execution**: 5 specialized tools for RAG operations
- **Conversation Management**: Multi-turn conversation support
- **Result Formatting**: Rich response with citations and images
- **Component Initialization**: Connects all backend components

#### 6. FastAPI Service (`main.py`)
- **REST API**: Full CRUD operations
- **File Upload**: Multipart form-data for PDF/DOCX/TXT
- **Multimodal Processing**: Automatic image detection and processing
- **CORS**: Configured for frontend integration
- **Error Handling**: Comprehensive error responses with fallbacks

### Frontend Components

- **ChatInterface**: Conversational UI with expandable tool results, citations, and **image display**
- **QueryInterface**: Search interface with rich result cards and **inline images**
- **CorpusManager**: Corpus creation, information display, and **delete functionality**
- **DocumentImporter**: File upload and manual document entry
- **API Client**: Centralized Axios-based API calls

### Component Connections & Data Flow

#### Component Initialization

All components are connected through the `TemporalRAGAgent` class in `agent.py`:

```python
class TemporalRAGAgent:
    def __init__(self):
        # 1. Create temporal embedding handler
        self.embedding_handler = TemporalEmbeddingHandler(
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            model_name=settings.embedding_model_name
        )

        # 2. Create RAG manager with embedding handler
        self.rag_manager = VertexRAGManager(
            project_id=settings.google_cloud_project,
            location=settings.google_cloud_location,
            corpus_name=settings.vertex_ai_corpus_name,
            embedding_handler=self.embedding_handler,  # ✅ CONNECTED
            gcs_bucket_name=settings.gcs_bucket_name,
            index_algorithm=settings.index_algorithm
        )
```

#### Component Connection Map

| Component | Calls | Purpose |
|-----------|-------|---------|
| main.py | multimodal_parser.parse_multimodal_pdf() | Extract images + text from PDF |
| main.py | chunker.chunk_multimodal_pdf() | Create chunks with image context |
| main.py | agent.rag_manager.import_documents() | Import chunks |
| agent.py | Creates TemporalEmbeddingHandler | Temporal-aware embeddings |
| agent.py | Creates VertexRAGManager with embedding_handler | RAG operations |
| VertexRAGManager | embedding_handler.generate_batch_embeddings() | Embed chunks |
| VertexRAGManager | Stores chunks in document_metadata | Preserve images |
| VertexRAGManager | index.upsert_datapoints() | Index in Vector Search |
| VertexRAGManager.query() | embedding_handler.generate_embedding() | Embed query |
| VertexRAGManager.query() | document_metadata[chunk_id] | Retrieve images |

#### Upload Flow (PDF with Images)

```
1. User uploads PDF
   ↓
2. main.py: upload_document()
   ↓
3. MultimodalDocumentParser.parse_multimodal_pdf()
   ├─ Extract images from PDF pages
   ├─ Vision API: Label detection, OCR, Object detection
   ├─ Upload images to GCS → Public URLs
   └─ Returns: {pages: [{text, images: [{url, description, ocr_text}]}]}
   ↓
4. TextChunker.chunk_multimodal_pdf()
   ├─ For each page: Combine text + image descriptions
   ├─ Create chunks: "[IMAGE: ...]\n\nPage text..."
   └─ Returns: chunks with images array preserved
   ↓
5. VertexRAGManager.import_documents(chunks)
   ├─ TemporalEmbeddingHandler.generate_batch_embeddings()
   │  ├─ Extract temporal info
   │  ├─ Enhance: "[TEMPORAL: ...] [IMAGE: ...] text"
   │  └─ Call Vertex AI text-embedding-004
   ├─ Store in document_metadata (with images)
   ├─ Create Vector Search datapoints
   └─ index.upsert_datapoints() → Indexed ✅
```

#### Query Flow

```
1. User query: "Show me database setup steps"
   ↓
2. VertexRAGManager.query()
   ├─ TemporalEmbeddingHandler.generate_embedding(query)
   ├─ index_endpoint.find_neighbors() → Vector Search
   ├─ Retrieve matching chunks from document_metadata
   └─ Format results with images array
   ↓
3. Return to frontend: {
     results: [{
       content_preview: "Step 1: Open settings...",
       images: [{url: "...", description: "..."}],
       metadata: {page_number: 3},
       citation: {...}
     }]
   }
   ↓
4. UI displays:
   - Text preview
   - Clickable images (thumbnails)
   - Page number
   - Citation link
```

#### Complete Integration Flow

**All components work together seamlessly:**

```
PDF with Images
    ↓
multimodal_parser (extracts images, Vision API descriptions)
    ↓
text_chunker (creates chunks with image context)
    ↓
temporal_embeddings (enhances with temporal + image context)
    ↓
Vector Search (indexes enhanced embeddings)
    ↓
Query → Vector Search → Results with images → Frontend Display
```

**Critical Features:**
- ✅ Images extracted and analyzed with Vision API
- ✅ Image descriptions embedded alongside text
- ✅ Images preserved in document_metadata (vertex_rag_manager.py:212)
- ✅ Images included in query results (vertex_rag_manager.py:436)
- ✅ Images displayed in UI (ChatInterface.js, QueryInterface.js)

### Key Features

#### Multimodal RAG (Images + Text)
- ✅ Extract images from PDFs and DOCX
- ✅ Vision API describes images (labels, OCR, objects)
- ✅ Image descriptions embedded with text for semantic search
- ✅ Images stored in GCS with public URLs
- ✅ Query results include relevant images
- ✅ UI displays images inline with text

#### Intelligent Chunking
- ✅ Hierarchical splitting (paragraphs → sentences → words)
- ✅ Configurable chunk size (default 1000 chars)
- ✅ Overlap between chunks (default 200 chars)
- ✅ Page-aware for PDFs (tracks page numbers)
- ✅ Metadata preserved per chunk

#### Temporal Context Awareness
- ✅ Automatic date extraction
- ✅ Temporal context enhancement before embedding
- ✅ Date-based filtering in queries
- ✅ Timeline visualization support

#### Citation System
- ✅ Automatic GCS Console URLs
- ✅ Optional source URLs
- ✅ Document metadata tracking
- ✅ Clickable links in UI

#### Vector Search
- ✅ BruteForce (fast, <10K docs) or TreeAH (production, >10K docs)
- ✅ StreamUpdate enabled for real-time indexing
- ✅ e2-standard-16 machine type
- ✅ DOT_PRODUCT distance measure

## Citation System

### Features

Every query result includes comprehensive citation information:

```json
{
  "id": "doc_123_456789",
  "score": 0.92,
  "title": "Q4 2023 Financial Report",
  "content_preview": "Revenue increased by 15%...",
  "citation": {
    "document_id": "doc_123_456789",
    "title": "Q4 2023 Financial Report",
    "source": "financial_report_q4.pdf",
    "clickable_link": "https://console.cloud.google.com/storage/browser/...",
    "gcs_console_url": "https://console.cloud.google.com/storage/browser/...",
    "source_url": "https://example.com/doc.pdf",
    "date": "2023-12-31",
    "formatted": "Q4 2023 Financial Report (2023-12-31). Source: q4_report.pdf"
  }
}
```

### Citation Types

1. **GCS Console Links** (Always Available)
   - Auto-generated for all documents
   - Direct link to GCS Console
   - Format: `https://console.cloud.google.com/storage/browser/_details/{bucket}/{path}`

2. **Source URLs** (Optional)
   - Provided in document metadata
   - Links to original source
   - Takes precedence for `clickable_link`

### Importing Documents with Citations

```python
documents = [
    {
        "content": "Document text...",
        "metadata": {
            "title": "My Document",
            "source_url": "https://example.com/doc.pdf",  # Optional
            "document_date": "2024-01-15",
            "filename": "doc.pdf"
        }
    }
]
```

### Retrieving Documents

```bash
# Get document by ID
curl http://localhost:8000/documents/doc_123_456789
```

Returns full document with citation information.

## Detailed Setup

### Environment Configuration

Create `backend/.env`:

```env
# Google Cloud Settings
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Vertex AI RAG
VERTEX_AI_CORPUS_NAME=temporal-context-corpus
VECTOR_SEARCH_INDEX_ENDPOINT=  # Optional, auto-created if not provided

# GCS Bucket (defaults to {project-id}-vector-search if not specified)
GCS_BUCKET_NAME=your-bucket-name

# Embedding Model (options: text-embedding-004, textembedding-gecko@003, text-multilingual-embedding-002)
EMBEDDING_MODEL_NAME=text-embedding-004
```

### Docker Setup

```bash
# Create .env file with credentials, then:
docker-compose up
```

Access:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

### Chat Interface

Natural language interaction:

```
User: "Create a corpus for financial reports"
Agent: [Creates corpus and returns details]

User: "Import documents about Q4 2023"
Agent: [Imports documents with temporal context]

User: "Query for revenue information"
Agent: [Returns results with citations]
```

### Query Interface

1. Enter search query
2. Set number of results (1-20)
3. Optional: Add temporal filter (date or JSON)
4. View results with:
   - Document titles and similarity scores
   - Content previews
   - Formatted citations
   - Clickable "View Source" buttons

### Document Import

**Option 1: File Upload**
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@document.txt" \
  -F "document_date=2024-01-15"
```

**Option 2: Manual Entry**
```bash
curl -X POST http://localhost:8000/documents/import \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "Your document text",
      "metadata": {
        "title": "Document Title",
        "document_date": "2024-01-15",
        "source_url": "https://example.com/doc.pdf"
      }
    }]
  }'
```

## API Reference

### Corpus Management

**POST /corpus/create**
```json
{
  "description": "Corpus description",
  "dimensions": 768
}
```

**GET /corpus/info**
Returns corpus details, index, and endpoint information.

### Document Operations

**POST /documents/import**
```json
{
  "documents": [
    {
      "content": "Document content",
      "metadata": {
        "title": "Document Title",
        "document_date": "2024-01-15",
        "source_url": "https://example.com/doc.pdf"
      },
      "id": "optional-custom-id"
    }
  ],
  "bucket_name": "optional-gcs-bucket"
}
```

**POST /documents/upload**
- Form data with `file` and optional `document_date`

**GET /documents/{document_id}**
Returns full document with citation.

### Querying

**POST /query**
```json
{
  "query": "Search query",
  "top_k": 5,
  "temporal_filter": {
    "document_date": "2023-12-31"
  }
}
```

Response includes citations with clickable links.

**POST /chat**
```json
{
  "message": "User message",
  "conversation_history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

### Temporal Analysis

**POST /temporal/extract**
```json
{
  "text": "Text to analyze for temporal entities"
}
```

Returns detected dates and years.

## Frontend UI

### Query Results Display

Each result shows:

```
┌─────────────────────────────────────────────┐
│ 📄 Q4 2023 Financial Report    [92.5% match]│
│                                             │
│ "Revenue increased by 15% compared to..."   │
│                                             │
│ Citation:                                   │
│ Q4 2023 Financial Report (2023-12-31).      │
│ Source: q4_report.pdf                       │
│                                             │
│ [🔗 View Source] ← Opens in new tab         │
│                                             │
│ [🕐 2023-12-31] [q4_report.pdf]             │
└─────────────────────────────────────────────┘
```

### Chat Interface Citations

Tool results appear in expandable accordions with the same rich citation display.

### UI Features

- **Color Coding**: User messages (blue), Agent messages (white), Result cards (gray)
- **Interactive Elements**: Clickable chips, expandable accordions, "View Source" buttons
- **Responsive Design**: Adapts to desktop, tablet, and mobile
- **Icons**: Material-UI icons for documents, dates, links, etc.
- **Accessibility**: Keyboard navigation, proper link handling

## Development

### Backend Testing

```bash
cd backend
pytest tests/
```

### Frontend Development

```bash
cd frontend
npm start   # Development with hot reload
npm build   # Production build
npm test    # Run tests
```

### Project Structure

```
agent-temporal-context/
├── backend/
│   ├── agent.py                      # ADK agent with tool definitions
│   ├── main.py                       # FastAPI app with multimodal upload
│   ├── vertex_rag_manager.py         # Vector Search operations
│   ├── temporal_embeddings.py        # Temporal context handling
│   ├── multimodal_parser.py          # PDF/DOCX image extraction + Vision API
│   ├── text_chunker.py               # Intelligent chunking with image context
│   ├── document_parser.py            # Text extraction from various formats
│   ├── config.py                     # Settings management
│   ├── requirements.txt              # Python dependencies
│   ├── .env.example                  # Environment variables template
│   ├── cleanup_old_index.py          # Utility to delete old indices
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.js         # Chat UI with image display
│   │   │   ├── QueryInterface.js        # Query UI with image results
│   │   │   ├── CorpusManager.js         # Corpus CRUD operations
│   │   │   └── DocumentImporter.js      # File upload interface
│   │   ├── App.js                       # Main app with modern UI
│   │   ├── api.js                       # API client
│   │   └── index.js
│   └── package.json
├── CLAUDE.md                          # Claude Code guidance
├── README.md                          # This file
├── CHUNKING_IMPLEMENTATION.md         # Chunking strategy details
├── MULTIMODAL_PDF_GUIDE.md            # Multimodal implementation guide
├── MULTIMODAL_FLOW_VERIFICATION.md    # End-to-end flow verification
└── COMPONENT_CONNECTIONS.md           # Complete component flow diagram
```

## Troubleshooting

### Backend Issues

**Authentication Errors**
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Vector Search Errors**
- Verify APIs enabled in GCP Console
- Check index deployment status (can take 5-10 minutes)
- Ensure sufficient GCP quotas

**Machine Type Errors**
- System uses `e2-standard-16` for SHARD_SIZE_MEDIUM
- Adjust in `vertex_rag_manager.py` if needed

**Embedding Model Errors**
- Verify model name in `.env`
- Supported: `text-embedding-004`, `textembedding-gecko@003`, `text-multilingual-embedding-002`

### Frontend Issues

**CORS Errors**
- Check backend CORS configuration in `main.py`
- Verify `REACT_APP_API_URL` in frontend `.env`

**Citation Links Not Working**
- Ensure documents imported with metadata
- Check GCS bucket permissions
- Verify bucket name in backend `.env`

### Common Solutions

1. **Restart Services**: Stop and restart both backend and frontend
2. **Clear Cache**: Delete `node_modules` and reinstall
3. **Check Logs**: Backend terminal and browser DevTools console
4. **Verify Permissions**: GCP IAM roles for Vertex AI and Storage

## Technologies

**Backend:**
- Python 3.9+
- FastAPI
- Anthropic Claude (ADK)
- Google Cloud Vertex AI
- Vertex AI Vector Search
- Google Cloud Storage
- Pydantic Settings

**Frontend:**
- React 18
- Material-UI (MUI)
- Axios

**AI Models:**
- Claude 3.5 Sonnet (Agent)
- text-embedding-004 (Embeddings, configurable)

## Embedding Models

The system supports multiple Vertex AI embedding models:

| Model | Dimensions | Best For |
|-------|-----------|----------|
| text-embedding-004 | 768 | General purpose (default) |
| textembedding-gecko@003 | 768 | Legacy/stable |
| text-multilingual-embedding-002 | 768 | Multilingual content |

Configure via `EMBEDDING_MODEL_NAME` in `.env`.

## Best Practices

### Document Import
1. Always provide `title` in metadata
2. Include `document_date` for temporal awareness
3. Add `source_url` for external documents
4. Use descriptive filenames

### Querying
1. Use natural language queries
2. Leverage temporal filters for time-sensitive searches
3. Adjust `top_k` based on needs (5-10 recommended)
4. Review similarity scores in results

### Citations
1. Check `clickable_link` availability before displaying
2. Use `formatted` citation for display
3. Provide fallback if citation data missing
4. Open links in new tabs for better UX

## License

MIT

## Contributing

Contributions welcome! Please submit Pull Requests.

## Support

- API Documentation: http://localhost:8000/docs
- Backend Logs: Terminal running `python main.py`
- Frontend Logs: Browser DevTools Console
- Issues: Check GitHub repository
