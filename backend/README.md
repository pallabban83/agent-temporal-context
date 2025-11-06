# Temporal Context RAG Agent - Backend

FastAPI-based backend service for the Temporal Context RAG Agent system, providing AI-powered document processing and semantic search with temporal awareness.

> For the complete project overview, see the [main README](../README.md) at the project root.

## Overview

This backend provides:
- **FastAPI REST API** for document management and querying
- **Temporal Context Processing** for date-aware embeddings
- **Vector Search Management** using Vertex AI
- **Table-Aware Document Parsing** for PDFs and DOCX files
- **AI Agent** for natural language interaction
- **GCS Integration** for cloud document import

---

## Quick Start

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Authenticate with Google Cloud
gcloud auth application-default login
```

### Run Application

```bash
# Method 1: Using the launcher (recommended)
./run.sh

# Method 2: Direct uvicorn command
cd src
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Method 3: Using Docker
docker build -t temporal-rag-agent .
docker run -p 8000:8000 temporal-rag-agent
```

**Access the API:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json

### Run Tests

```bash
# Comprehensive test suite (recommended)
python3 run_all_tests.py

# Simple test runners
./run_tests.sh
python3 run_tests.py

# With pytest directly
python3 -m pytest test/
```

---

## Directory Organization

The backend follows Python best practices with clear separation of concerns:

```
backend/
├── src/                          # Source code (production)
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application entry point
│   ├── agent.py                 # AI agent implementation
│   ├── config.py                # Configuration management
│   ├── logging_config.py        # Logging framework
│   ├── temporal_embeddings.py   # Temporal context handling
│   ├── vector_search_manager.py # Vector Search operations
│   ├── document_parser.py       # PDF/DOCX parsing
│   └── text_chunker.py         # Text chunking logic
│
├── test/                         # Test suite (automated tests only)
│   ├── __init__.py              # Test package initialization
│   ├── conftest.py              # Pytest configuration
│   └── test_*.py                # Test files (11 files)
│
├── scripts/                      # Utility scripts
│   ├── check_aug27_metadata.py  # Check specific document metadata
│   ├── test_current_dates.py    # Check date distribution in index
│   ├── clear_index.py           # Clear all documents from index
│   ├── cleanup_old_index.py     # Cleanup old data
│   └── generate_test_pdfs.py    # Generate test PDF files
│
├── test_pdfs/                    # Test data (55 PDF files)
│
├── run.sh                        # Application launcher
├── run_tests.sh                  # Simple test runner (bash)
├── run_tests.py                  # Simple test runner (Python)
├── run_all_tests.py              # Comprehensive test suite
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker configuration
└── .env                          # Environment variables
```

---

## Test Suite

### Test Categories

The test suite is organized into categories for clear organization:

#### 1. Date Normalization Tests
Tests for temporal date extraction and normalization:
- `test_ordinal_fix.py` - Ordinal suffix handling ("1st", "2nd", etc.)
- `test_abbreviated_months.py` - Abbreviated month parsing ("Aug", "Sep", etc.)
- `test_temporal_normalization.py` - Date format normalization (YYYY-MM-DD)
- `test_filename_extraction.py` - Extracting dates from filenames

#### 2. GCS Import Tests
Tests for Google Cloud Storage import:
- `test_gcs_import_dates.py` - GCS import date extraction
- `test_metadata_creation.py` - Metadata generation

#### 3. Integration Tests
End-to-end workflow tests:
- `test_temporal_embedding_integration.py` - Embedding workflow
- `test_query_temporal_flow.py` - Query processing flow

#### 4. Validation Tests
Data validation and edge cases:
- `test_bbox_validation.py` - Bounding box validation

### Utility Scripts (scripts/)

These are NOT tests but utility scripts for development and debugging:

#### Data Inspection Scripts
- `check_aug27_metadata.py` - Check specific document metadata in the index
- `test_current_dates.py` - Analyze date distribution across all indexed documents

#### Data Management Scripts
- `clear_index.py` - Delete ALL documents from Vector Search index (with confirmation)
- `cleanup_old_index.py` - Clean up old/stale data from index

#### Test Data Generation
- `generate_test_pdfs.py` - Generate 55 test PDFs with various date formats

**Running utility scripts:**
```bash
# Set Python path
export PYTHONPATH=src

# Check document dates in index
python3 scripts/test_current_dates.py

# Check specific document
python3 scripts/check_aug27_metadata.py

# Generate test PDFs (outputs to test_pdfs/)
python3 scripts/generate_test_pdfs.py

# Clear index (requires confirmation)
python3 scripts/clear_index.py
```

### Running Tests

**Comprehensive test suite with organized output:**
```bash
python3 run_all_tests.py
```

Output includes:
- Real-time test execution
- Categorized summary
- Pass/fail statistics

**Run specific tests:**
```bash
# Using pytest
python3 -m pytest test/test_ordinal_fix.py -v

# Direct execution
export PYTHONPATH=src
python3 test/test_ordinal_fix.py
```

**Run by category using markers:**
```bash
python3 -m pytest -m unit          # Unit tests only
python3 -m pytest -m integration   # Integration tests only
python3 -m pytest -m requires_gcp  # GCP tests only
```

---

## Development Workflow

### 1. Initial Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Authenticate with Google Cloud
gcloud auth application-default login
```

### 2. Make Changes

Edit files in `src/` directory:
- Source code files are all in `src/`
- Import statements work within the same directory
- Tests automatically find source files via `conftest.py`

Example:
```python
# In src/agent.py
from temporal_embeddings import TemporalEmbeddingHandler
from vector_search_manager import VectorSearchManager
from config import settings
```

### 3. Run Tests

```bash
# Run all tests
python3 run_all_tests.py

# Or run specific test
export PYTHONPATH=src
python3 test/test_ordinal_fix.py
```

### 4. Run Application

```bash
# Start the server
./run.sh

# Or with hot reload
cd src
uvicorn main:app --reload
```

### 5. Verify Changes

Access the API:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json

---

## Import Structure

### Within Source Code (src/)

Files in `src/` import from each other directly:

```python
# In src/agent.py
from temporal_embeddings import TemporalEmbeddingHandler
from vector_search_manager import VectorSearchManager
from config import settings
```

### Within Tests (test/)

Tests import from src using the automatic path setup:

```python
# In test/test_*.py
from temporal_embeddings import TemporalEmbeddingHandler
# This works because conftest.py adds src/ to Python path
```

### Running Standalone Scripts

When running test scripts directly (not via pytest):

```bash
export PYTHONPATH=src
python3 test/test_ordinal_fix.py
```

---

## Configuration

### Environment Variables

Required environment variables in `.env`:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Vector Search
VERTEX_AI_CORPUS_NAME=temporal-rag-corpus
VECTOR_SEARCH_INDEX=your-index-id
VECTOR_SEARCH_INDEX_ENDPOINT=your-endpoint-id

# Storage
GCS_BUCKET_NAME=your-bucket-name

# Embedding Configuration
EMBEDDING_MODEL_NAME=text-embedding-005
EMBEDDING_REQUESTS_PER_MINUTE=300

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or logfmt
LOG_COLORS=true
```

### pytest.ini

Pytest configuration:
- Test discovery patterns
- Output formatting
- Markers for categorizing tests
- Coverage settings (if pytest-cov is installed)

### conftest.py

Pytest automatic setup:
- Adds `src/` to Python path
- Runs automatically before any pytest tests
- Ensures tests can import source modules

### Dockerfile

Updated for new structure:
- Sets `PYTHONPATH=/app/src`
- Changes `WORKDIR` to `/app/src` before running
- Runs `uvicorn main:app` from src directory

---

## Adding New Components

### Adding New Tests

1. **Create test file:**

```python
# test/test_my_feature.py
"""Test description"""

from my_module import MyClass

def test_my_feature():
    obj = MyClass()
    assert obj.method() == expected_value
```

2. **Add to test suite:**

Edit `run_all_tests.py`:

```python
test_categories = {
    'My Category': [
        'test_my_feature.py',
    ],
}
```

3. **Run tests:**

```bash
python3 run_all_tests.py
```

### Adding New Source Modules

1. Create file in `src/` directory
2. Import from other src modules directly
3. No path manipulation needed

```python
# src/new_module.py
from existing_module import ExistingClass
from config import settings

class NewClass:
    pass
```

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'temporal_embeddings'`

**Solution:**
```bash
# For pytest
python3 -m pytest test/

# For direct script execution
export PYTHONPATH=src
python3 test/test_script.py

# Or use the test runner
python3 run_all_tests.py
```

### Missing Dependencies

**Problem:** `ModuleNotFoundError: No module named 'pypdf'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Docker Build Issues

**Problem:** Docker can't find main.py

**Solution:** Ensure Dockerfile has:
```dockerfile
ENV PYTHONPATH=/app/src
WORKDIR /app/src
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### GCP Authentication Issues

**Problem:** `google.auth.exceptions.DefaultCredentialsError`

**Solution:**
```bash
gcloud auth application-default login
```

---

## API Documentation

### Key Endpoints

- **POST /index/create** - Create Vector Search index
- **POST /documents/upload** - Upload and process document
- **POST /documents/import-gcs** - Import documents from GCS
- **POST /query** - Semantic search with temporal filtering
- **POST /chat** - Natural language interaction with agent
- **GET /index/info** - Get index information
- **GET /health** - Health check

See interactive API docs at http://localhost:8000/docs when server is running.

---

## Best Practices

1. **Keep source code in `src/`** - All production code goes here
2. **Keep tests in `test/`** - All test files and utilities
3. **Use the test runners** - Don't run tests manually
4. **Use `./run.sh`** - Easiest way to start the application
5. **Import directly in src** - No need for complex imports within source
6. **Use markers for tests** - Categorize with `@pytest.mark.unit`, etc.
7. **Update test suite** - Add new tests to `run_all_tests.py` categories
8. **Run tests before commits** - Ensure nothing breaks
9. **Use type hints** - Improve code clarity and IDE support
10. **Follow logging standards** - Use structured logging (JSON/LOGFMT)

---

## Key Features

### Temporal Context Processing

The system enhances embeddings with temporal awareness:
- Extracts dates from filenames and content
- Normalizes dates to YYYY-MM-DD format
- Adds temporal context to embeddings
- Enables time-based filtering in queries

See: `src/temporal_embeddings.py`

### Table-Aware Chunking

Intelligent text chunking that preserves table structure:
- Detects tables in PDFs
- Converts to markdown format
- Never splits tables mid-table
- Smart overlap logic around tables
- Quality scoring for chunks

See: `src/text_chunker.py` and `src/document_parser.py`

### Citation System

Comprehensive source attribution:
- Relevance scores from vector search
- Page numbers and chunk locations
- Clickable document URLs
- Quality scores from chunking

See: `src/vector_search_manager.py:_format_citation()`

---

## Architecture

### Component Overview

- **`main.py`** - FastAPI application and API endpoints
- **`agent.py`** - AI agent using Google ADK
- **`temporal_embeddings.py`** - Temporal extraction and embedding enhancement
- **`vector_search_manager.py`** - Vector Search operations and querying
- **`document_parser.py`** - PDF/DOCX parsing with table extraction
- **`text_chunker.py`** - Semantic chunking with quality metrics
- **`config.py`** - Settings management with pydantic-settings
- **`logging_config.py`** - Centralized logging framework

### Data Flow

1. **Document Import:**
   - User uploads document → Extract temporal info → Add metadata → Generate embedding → Upsert to Vector Search + Store in GCS

2. **Query:**
   - User query → Extract temporal context → Generate query embedding → find_neighbors API with filters → Return results

3. **Chat:**
   - User message → Agent with tools → Tool execution (import/query) → Agent response

---

## Summary

✅ **Clean organization** - Source and tests separated
✅ **Easy to run** - Simple scripts for all operations
✅ **Pytest integration** - Professional test framework
✅ **Comprehensive testing** - Organized test suite with categories
✅ **Docker ready** - Updated for new structure
✅ **Import simplicity** - No complex path manipulation needed
✅ **Production-ready** - Logging, configuration, error handling
✅ **Well documented** - Inline docs and comprehensive README

---

## Additional Documentation

- **Main Project README**: [../README.md](../README.md)
- **CLAUDE.md**: Project-specific guidance for AI assistants
- **Citation Format**: `CITATION_FORMAT.md`
- **Logging Guide**: `LOGGING.md`

---

## Support

For issues, feature requests, or questions:
1. Check this README and related documentation
2. Review API docs at http://localhost:8000/docs
3. Check test suite for usage examples
4. Review logs for detailed error messages
