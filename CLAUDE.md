# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Temporal Context RAG Agent** system that combines:
- **Anthropic's Agent Development Kit (ADK)** for conversational AI capabilities
- **Vertex AI** for embeddings and Vector Search
- **FastAPI** for the REST API backend
- **React** for the web UI frontend

The agent specializes in handling documents with temporal context (date-specific information), creating embeddings that maintain temporal awareness, and enabling time-sensitive semantic search.

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
   - Defines tools for corpus management, document import, and querying
   - Handles multi-turn conversations with tool execution
   - Main class: `TemporalRAGAgent`

2. **Temporal Embeddings** (`temporal_embeddings.py`)
   - Extracts temporal information from text (dates, years)
   - Enhances text with temporal context markers before embedding
   - Generates embeddings using Vertex AI textembedding-gecko model
   - Key class: `TemporalEmbeddingHandler`
   - Pattern: Text → Extract temporal info → Add context markers → Generate embedding

3. **RAG Management** (`vertex_rag_manager.py`)
   - Creates and manages Vertex AI Vector Search indices
   - Handles document import with temporal metadata
   - Performs semantic search with optional temporal filtering
   - Stores documents in Google Cloud Storage
   - Key class: `VertexRAGManager`

4. **API Layer** (`main.py`)
   - FastAPI application with REST endpoints
   - CORS-enabled for frontend integration
   - Endpoints for corpus creation, document import, querying, and chat
   - File upload support with multipart/form-data

### Frontend Architecture

1. **Main App** (`App.js`)
   - Tab-based interface with 4 main views
   - Material-UI theming and layout
   - State management for active tab

2. **Components**
   - `ChatInterface`: Conversational UI for natural language interaction with the agent
   - `CorpusManager`: Create new corpora and view corpus information
   - `DocumentImporter`: Upload files or manually add documents with temporal metadata
   - `QueryInterface`: Search with temporal filtering and analyze temporal context

3. **API Client** (`api.js`)
   - Axios-based HTTP client
   - Centralized API calls to backend
   - Base URL configuration via environment variable

### Data Flow

1. **Document Import Flow**
   - User uploads document → Extract temporal info → Add metadata → Generate embedding → Store in Vector Search + GCS

2. **Query Flow**
   - User query → Extract temporal context → Generate query embedding → Vector Search with filters → Return results

3. **Chat Flow**
   - User message → Agent with tools → Tool execution (create corpus/import/query) → Agent response

## Key Implementation Details

### Temporal Context Handling

The system enhances embeddings by:
1. Detecting date patterns (YYYY-MM-DD, MM/DD/YYYY, natural language)
2. Extracting years from text
3. Prepending temporal context to text before embedding: `[TEMPORAL_CONTEXT: Document Date: 2023-12-31 | Contains dates: ...] <original text>`

This allows the embedding model to capture temporal relationships and improves retrieval for time-sensitive queries.

### ADK Agent Tools

The agent exposes 5 tools:
1. `create_rag_corpus` - Initialize Vector Search index and endpoint
2. `import_documents` - Batch import with temporal enhancement
3. `query_corpus` - Semantic search with temporal filtering
4. `get_corpus_info` - Retrieve index/endpoint metadata
5. `extract_temporal_context` - Analyze text for temporal entities

### Vector Search Configuration

- **Distance Measure**: DOT_PRODUCT_DISTANCE (for normalized embeddings)
- **Index Type**: Tree-AH (Approximate Hierarchical)
- **Embedding Dimensions**: 768 (textembedding-gecko)
- **Approximate Neighbors**: 10
- **Machine Type**: e2-standard-2 (for endpoint)

## Important Files

- `backend/agent.py` - ADK agent implementation with tool definitions
- `backend/temporal_embeddings.py` - Temporal context extraction and embedding enhancement
- `backend/vertex_rag_manager.py` - Vector Search operations
- `backend/main.py` - FastAPI application and API endpoints
- `backend/config.py` - Settings management with pydantic-settings
- `frontend/src/api.js` - API client for backend communication
- `frontend/src/components/` - React UI components

## Environment Configuration

Required environment variables (backend):
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - GCP region (e.g., us-central1)
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- `VERTEX_AI_CORPUS_NAME` - Name for the RAG corpus
- `VECTOR_SEARCH_INDEX_ENDPOINT` - Optional pre-existing endpoint

## Working with the Codebase

### Adding New Agent Tools

1. Define tool schema in `agent.py` in the `self.tools` list
2. Implement handler in `execute_tool()` method
3. Add corresponding method to `VertexRAGManager` if needed
4. Create API endpoint in `main.py`
5. Update frontend API client in `api.js`

### Modifying Temporal Context Logic

- Edit `TemporalEmbeddingHandler.extract_temporal_info()` for new date patterns
- Modify `enhance_text_with_temporal_context()` for different context formatting
- Update tests to cover new temporal patterns

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
