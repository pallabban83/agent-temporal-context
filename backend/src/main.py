"""
FastAPI Web Service for Temporal Context RAG Agent
"""

# Initialize logging FIRST before any other imports
from config import settings
from logging_config import setup_logging, get_logger

# Setup centralized logging
setup_logging(
    log_format=settings.log_format,
    log_level=settings.log_level,
    enable_colors=settings.log_colors
)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from agent import TemporalRAGAgent
from document_parser import DocumentParser
from text_chunker import TextChunker

# Get logger for this module
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="RAG Agent with Temporal Context awareness using Vertex AI"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = TemporalRAGAgent()


# Pydantic models for request/response
class CreateVectorSearchRequest(BaseModel):
    description: str = Field("Vector Search for Temporal RAG", description="Description of the index")
    dimensions: int = Field(768, description="Embedding dimensions (768 for text-embedding-005)")
    index_algorithm: str = Field("brute_force", description="Index algorithm: brute_force or tree_ah")




class Document(BaseModel):
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")
    id: Optional[str] = Field(None, description="Document ID")


class ImportDocumentsRequest(BaseModel):
    documents: List[Document] = Field(..., description="List of documents to import")
    bucket_name: Optional[str] = Field(None, description="Optional GCS bucket name")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: Optional[int] = Field(None, description="Number of results to return (default: from settings)")
    temporal_filter: Optional[Dict[str, Any]] = Field(None, description="Temporal filtering criteria")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history")
    session_id: Optional[str] = Field(None, description="Session ID for maintaining conversation context")
    user_id: str = Field("default_user", description="User identifier")


class ExtractTemporalRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/index/create")
async def create_index(request: CreateVectorSearchRequest):
    """Create Vector Search index and endpoint from scratch.

    This creates the Vector Search infrastructure for storing and querying documents.
    After creation, the resource names are automatically saved to .env file.

    Args:
        request: Vector Search creation parameters

    Returns:
        Index and endpoint resource names
    """
    try:
        logger.info(f"Creating Vector Search infrastructure: {request.description}")
        result = await agent.vector_search_manager.create_vector_search_infrastructure(
            description=request.description,
            dimensions=request.dimensions,
            index_algorithm=request.index_algorithm
        )
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error creating Vector Search infrastructure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index/info")
async def get_index_info():
    """Get information about the current Vector Search index.

    Returns:
        Index information
    """
    try:
        info = await agent.vector_search_manager.get_index_info()
        return {"success": True, "data": info}

    except Exception as e:
        logger.error(f"Error getting index info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/index/clear")
async def clear_index_datapoints():
    """Clear all datapoints from the index without deleting the index/endpoint.

    This is much faster than recreating the entire index infrastructure.

    Returns:
        Clear operation status
    """
    try:
        logger.info("Clearing all datapoints via API")
        result = await agent.vector_search_manager.clear_all_datapoints()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error clearing datapoints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/index/delete")
async def delete_index():
    """Delete Vector Search index and endpoint infrastructure.

    Use this to clean up infrastructure before creating new.

    Returns:
        Deletion status
    """
    try:
        logger.info("Deleting Vector Search infrastructure via API")
        result = await agent.vector_search_manager.delete_index_infrastructure()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error deleting Vector Search infrastructure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/import")
async def import_documents(request: ImportDocumentsRequest):
    """Import documents into Vector Search.

    Args:
        request: Document import parameters

    Returns:
        Import result
    """
    try:
        logger.info(f"Importing {len(request.documents)} documents")

        # Convert Pydantic models to dicts
        documents = [doc.model_dump() for doc in request.documents]

        result = await agent.vector_search_manager.import_documents(
            documents=documents,
            bucket_name=request.bucket_name
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error importing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_date: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    chunk_size: int = Form(300),
    chunk_overlap: int = Form(60)
):
    """Upload and import a document file (PDF, DOCX, TXT).

    Args:
        file: Document file to upload (PDF, DOCX, TXT, MD)
        document_date: Optional date associated with the document
        title: Optional custom title for the document
        chunk_size: Size of each text chunk in characters (default: 300)
        chunk_overlap: Overlap between consecutive chunks in characters (default: 60)

    Returns:
        Import result with parsing statistics
    """
    try:
        logger.info(f"Uploading file: {file.filename} ({file.content_type})")

        # Read file content
        content = await file.read()

        # Store original file in GCS and get authenticated URL
        original_file_url = agent.vector_search_manager.store_original_file(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type or 'application/octet-stream'
        )

        # Base metadata
        base_metadata = {
            "filename": file.filename,
            "title": title or file.filename,
            "content_type": file.content_type,
            "uploaded_at": datetime.now().isoformat(),
            "original_file_url": original_file_url  # Add authenticated URL for viewing
        }

        # Determine document date (user-provided takes priority)
        final_document_date = document_date

        # If not provided, extract from filename
        if not final_document_date:
            extracted_date = agent.embedding_handler.extract_date_from_filename(file.filename)
            if extracted_date:
                final_document_date = extracted_date
                logger.info(
                    "Extracted date from filename",
                    extra={
                        'document_filename': file.filename,
                        'extracted_date': extracted_date
                    }
                )

        # Add to metadata if we have a date (user-provided or extracted)
        if final_document_date:
            base_metadata["document_date"] = final_document_date

        # Validate chunk parameters
        if chunk_overlap >= chunk_size:
            raise HTTPException(
                status_code=400,
                detail=f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
            )

        # Initialize chunker with custom parameters
        logger.info(f"Using chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        document_id = f"{file.filename.replace('.', '_').replace(' ', '_')}_{int(datetime.now().timestamp())}"

        # Handle PDF files with page-aware chunking
        if file.filename.lower().endswith('.pdf') or file.content_type == 'application/pdf':
            logger.info("Processing PDF (text-only)...")

            # Parse PDF text by pages
            pdf_data = DocumentParser.parse_pdf_by_pages(content)

            base_metadata.update({
                "document_type": "pdf",
                "total_pages": pdf_data['total_pages'],
                "non_empty_pages": pdf_data.get('non_empty_pages', pdf_data['total_pages']),
                "char_count": pdf_data['total_chars'],
                "has_tables": pdf_data.get('has_tables', False),
                "total_tables": pdf_data.get('total_tables', 0),
            })

            # Chunk by pages (text + tables)
            chunks = chunker.chunk_pdf_by_pages(
                page_texts=pdf_data['page_texts'],
                metadata=base_metadata,
                document_id=document_id
            )

            parsing_info = {
                'type': 'pdf',
                'total_pages': pdf_data['total_pages'],
                'non_empty_pages': pdf_data.get('non_empty_pages', pdf_data['total_pages']),
                'char_count': pdf_data['total_chars'],
                'total_tables': pdf_data.get('total_tables', 0),
                'has_tables': pdf_data.get('has_tables', False),
                'pages_with_tables': pdf_data.get('pages_with_tables', []),
                'chunks_created': len(chunks)
            }
        else:
            # Parse other document types
            parsed_doc = DocumentParser.parse_document(
                file_bytes=content,
                filename=file.filename,
                content_type=file.content_type
            )

            base_metadata.update({
                "document_type": parsed_doc['type'],
                "char_count": parsed_doc['char_count'],
                "word_count": parsed_doc['word_count']
            })

            # Chunk the text
            chunks = chunker.chunk_text(
                text=parsed_doc['text'],
                metadata=base_metadata,
                document_id=document_id
            )

            parsing_info = {
                'type': parsed_doc['type'],
                'char_count': parsed_doc['char_count'],
                'word_count': parsed_doc['word_count'],
                'chunks_created': len(chunks)
            }

        logger.info(f"Created {len(chunks)} chunks from document")

        # Import chunks as separate documents
        result = await agent.vector_search_manager.import_documents(documents=chunks)

        # Add parsing info to result
        result['parsing_info'] = parsing_info

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/import_from_gcs")
async def import_from_gcs(
    gcs_path: str = Form(...),
    document_date: Optional[str] = Form(None),
    recursive: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """Import documents from GCS path (file or folder).

    Args:
        gcs_path: GCS path (gs://bucket/path/to/folder/ or gs://bucket/file.pdf)
        document_date: Optional date associated with all documents
        recursive: If True and path is folder, import all files recursively (default: True)
        chunk_size: Size of each text chunk in characters (default: 1000)
        chunk_overlap: Overlap between consecutive chunks in characters (default: 200)

    Returns:
        Import result with file counts and status

    Example paths:
        - Single file: gs://my-bucket/documents/report.pdf
        - Folder: gs://my-bucket/documents/
        - Subfolder: gs://my-bucket/documents/financial/2023/
    """
    try:
        logger.info(
            "GCS import requested",
            extra={
                'gcs_path': gcs_path,
                'document_date': document_date,
                'recursive': recursive,
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap
            }
        )

        # Validate GCS path format
        if not gcs_path.startswith('gs://'):
            raise HTTPException(
                status_code=400,
                detail="Invalid GCS path. Must start with 'gs://'"
            )

        # Validate chunk parameters
        if chunk_overlap >= chunk_size:
            raise HTTPException(
                status_code=400,
                detail=f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
            )

        # Import from GCS
        result = await agent.vector_search_manager.import_from_gcs(
            gcs_path=gcs_path,
            document_date=document_date,
            recursive=recursive,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        return {"success": True, "data": result}

    except ValueError as e:
        logger.error(
            "GCS import validation error",
            extra={'gcs_path': gcs_path, 'error': str(e)}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error importing from GCS",
            exc_info=True,
            extra={'gcs_path': gcs_path}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_index(request: QueryRequest):
    """Query Vector Search index with citations.

    Args:
        request: Query parameters

    Returns:
        Query results with document citations and clickable links
    """
    try:
        logger.info(f"Querying: {request.query}")

        result = await agent.vector_search_manager.query(
            query_text=request.query,
            top_k=request.top_k,
            temporal_filter=request.temporal_filter
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error querying index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Retrieve a specific document by ID.

    Args:
        document_id: Document ID

    Returns:
        Document with citation information
    """
    try:
        document = agent.vector_search_manager.get_document(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"success": True, "data": document}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the agent using natural language.

    Args:
        request: Chat message, session_id, and user_id

    Returns:
        Agent response with session_id
    """
    try:
        logger.info(f"Processing chat message: {request.message} (session: {request.session_id})")

        result = await agent.chat(
            user_message=request.message,
            conversation_history=request.conversation_history,
            session_id=request.session_id,
            user_id=request.user_id
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/temporal/extract")
async def extract_temporal_context(request: ExtractTemporalRequest):
    """Extract temporal information from text.

    Args:
        request: Text to analyze

    Returns:
        Extracted temporal entities
    """
    try:
        temporal_info = agent.embedding_handler.extract_temporal_info(request.text)

        return {
            "success": True,
            "data": {
                "text": request.text,
                "temporal_entities": temporal_info,
                "entity_count": len(temporal_info)
            }
        }

    except Exception as e:
        logger.error(f"Error extracting temporal context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Run server with auto-reload
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
