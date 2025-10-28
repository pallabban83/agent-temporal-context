"""
FastAPI Web Service for Temporal Context RAG Agent
"""


from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from agent import TemporalRAGAgent
from config import settings
from document_parser import DocumentParser
from text_chunker import TextChunker
from multimodal_parser import MultimodalDocumentParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Initialize multimodal parser
multimodal_parser = MultimodalDocumentParser(
    project_id=settings.google_cloud_project,
    gcs_bucket=settings.gcs_bucket_name
)


# Pydantic models for request/response
class CreateVectorSearchRequest(BaseModel):
    description: str = Field("Vector Search for Temporal RAG", description="Description of the index")
    dimensions: int = Field(768, description="Embedding dimensions (768 for text-embedding-005)")
    index_algorithm: str = Field("brute_force", description="Index algorithm: brute_force or tree_ah")


class CreateCorpusRequest(BaseModel):
    description: str = Field(..., description="Description of the corpus")
    dimensions: int = Field(768, description="Embedding dimensions")


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


@app.post("/vector-search/create")
async def create_vector_search_infrastructure(request: CreateVectorSearchRequest):
    """Create Vector Search index and endpoint from scratch.

    This is STEP 1: Creates the underlying infrastructure.
    After creation, the resource names are automatically saved to .env file.
    You can then use STEP 2 to create a RAG corpus on top of this infrastructure.

    Args:
        request: Vector Search creation parameters

    Returns:
        Index and endpoint resource names
    """
    try:
        logger.info(f"Creating Vector Search infrastructure: {request.description}")
        result = await agent.rag_manager.create_vector_search_infrastructure(
            description=request.description,
            dimensions=request.dimensions,
            index_algorithm=request.index_algorithm
        )
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error creating Vector Search infrastructure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus/create")
async def create_corpus(request: CreateCorpusRequest):
    """Create a new RAG corpus using existing Vector Search infrastructure.

    This is STEP 2: Creates a RAG corpus that wraps the Vector Search index/endpoint.
    Requires Vector Search infrastructure to be created first (STEP 1) or configured in .env.

    Args:
        request: Corpus creation parameters

    Returns:
        Corpus creation result
    """
    try:
        logger.info(f"Creating corpus: {request.description}")
        result = await agent.rag_manager.create_corpus(
            description=request.description,
            dimensions=request.dimensions
        )
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error creating corpus: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/corpus/info")
async def get_corpus_info():
    """Get information about the current RAG corpus.

    Returns:
        Corpus information
    """
    try:
        info = await agent.rag_manager.get_corpus_info()
        return {"success": True, "data": info}

    except Exception as e:
        logger.error(f"Error getting corpus info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus/clear-datapoints")
async def clear_datapoints():
    """Clear all datapoints from the index without deleting the index/endpoint.

    This is much faster than recreating the entire corpus.

    Returns:
        Clear operation status
    """
    try:
        logger.info("Clearing all datapoints via API")
        result = await agent.rag_manager.clear_all_datapoints()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error clearing datapoints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus/register-existing-documents")
async def register_existing_documents():
    """Register existing GCS documents with RAG Engine.

    This is useful when documents were already upserted to Vector Search
    but need to be registered with RAG Engine for text retrieval.

    Returns:
        Registration status and document count
    """
    try:
        logger.info("Registering existing GCS documents with RAG Engine")
        result = await agent.rag_manager.register_existing_documents_with_rag()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error registering documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/corpus/diagnostics")
async def run_sync_diagnostics():
    """Run sync diagnostics to check for inconsistencies.

    Checks:
    - Metadata cache completeness
    - GCS document sync status
    - RAG Engine registration status
    - Citation metadata completeness

    Returns:
        Diagnostic report with sync status and recommendations
    """
    try:
        logger.info("Running sync diagnostics")

        from diagnose_sync import SyncDiagnostics

        diagnostics = SyncDiagnostics()
        report = diagnostics.analyze_sync_status()

        return {
            "success": True,
            "data": report,
            "recommendations": _get_recommendations(report)
        }

    except Exception as e:
        logger.error(f"Error running diagnostics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus/rebuild-metadata")
async def rebuild_metadata_cache():
    """Rebuild metadata cache from GCS documents.

    This is useful when:
    - Metadata cache is out of sync
    - Citations are not working properly
    - After manual GCS operations

    Returns:
        Rebuild status and metadata count
    """
    try:
        logger.info("Rebuilding metadata cache from GCS")

        from repair_sync import SyncRepairer

        repairer = SyncRepairer(dry_run=False)
        metadata = repairer.rebuild_metadata_from_gcs()

        if not metadata:
            raise HTTPException(
                status_code=500,
                detail="Failed to rebuild metadata - no documents found"
            )

        # Validate citations
        validation_report = repairer.validate_citations(metadata)

        # Save metadata
        if not repairer.save_metadata_to_gcs(metadata):
            raise HTTPException(
                status_code=500,
                detail="Failed to save rebuilt metadata"
            )

        # Reload metadata in the running instance
        agent.rag_manager.document_metadata = metadata

        return {
            "success": True,
            "data": {
                "metadata_count": len(metadata),
                "validation": validation_report,
                "message": "Metadata cache successfully rebuilt and reloaded"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rebuilding metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/corpus/full-repair")
async def full_sync_repair():
    """Perform full sync repair.

    This operation will:
    1. Rebuild metadata cache from GCS documents
    2. Re-register all documents with RAG Engine
    3. Validate citation completeness

    Returns:
        Repair status and summary
    """
    try:
        logger.info("Performing full sync repair")

        from repair_sync import SyncRepairer

        repairer = SyncRepairer(dry_run=False)
        success = repairer.full_repair()

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Full repair completed with errors - check logs"
            )

        # Reload metadata in the running instance
        metadata_path = f"rag_corpus/{agent.rag_manager.corpus_name}/metadata/document_metadata.json"
        from google.cloud import storage
        storage_client = storage.Client(project=agent.rag_manager.project_id)
        bucket = storage_client.bucket(agent.rag_manager.gcs_bucket_name)
        blob = bucket.blob(metadata_path)

        if blob.exists():
            metadata_json = blob.download_as_text()
            agent.rag_manager.document_metadata = json.loads(metadata_json)
            logger.info(f"Reloaded metadata for {len(agent.rag_manager.document_metadata)} documents")

        return {
            "success": True,
            "data": {
                "message": "Full repair completed successfully",
                "metadata_count": len(agent.rag_manager.document_metadata),
                "recommendation": "Run GET /corpus/diagnostics to verify sync status"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during full repair: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_recommendations(report: Dict[str, Any]) -> List[str]:
    """Get recommendations based on diagnostic report."""
    recommendations = []

    if report.get('needs_rag_sync'):
        recommendations.append(
            "Run POST /corpus/register-existing-documents to sync documents with RAG Engine"
        )

    if report.get('missing_metadata'):
        recommendations.append(
            "Run POST /corpus/rebuild-metadata to rebuild metadata cache from GCS"
        )

    if report.get('citation_issues_count', 0) > 0:
        recommendations.append(
            "Some documents have incomplete citation metadata - consider re-importing with complete metadata"
        )

    if not recommendations:
        recommendations.append("System is healthy - no action needed")

    return recommendations


@app.delete("/vector-search/delete")
async def delete_vector_search_infrastructure():
    """Delete Vector Search index and endpoint infrastructure.

    Use this to clean up old infrastructure before creating new.

    Returns:
        Deletion status
    """
    try:
        logger.info("Deleting Vector Search infrastructure via API")
        result = await agent.rag_manager.delete_vector_search_infrastructure()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error deleting Vector Search infrastructure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/corpus/delete")
async def delete_corpus():
    """Delete the RAG corpus and all associated resources.

    Returns:
        Deletion status
    """
    try:
        logger.info("Deleting corpus via API")
        result = await agent.rag_manager.delete_corpus()
        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error deleting corpus: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/import")
async def import_documents(request: ImportDocumentsRequest):
    """Import documents into the RAG corpus.

    Args:
        request: Document import parameters

    Returns:
        Import result
    """
    try:
        logger.info(f"Importing {len(request.documents)} documents")

        # Convert Pydantic models to dicts
        documents = [doc.model_dump() for doc in request.documents]

        result = await agent.rag_manager.import_documents(
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
        original_file_url = agent.rag_manager.store_original_file(
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

        if document_date:
            base_metadata["document_date"] = document_date

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

        # Handle PDF files with page-aware chunking (with or without images)
        if file.filename.lower().endswith('.pdf') or file.content_type == 'application/pdf':
            logger.info("Processing PDF...")

            # Try multimodal parsing to check for images
            try:
                multimodal_data = multimodal_parser.parse_multimodal_pdf(content, document_id)

                if multimodal_data['has_images']:
                    logger.info(f"PDF has {multimodal_data['total_images']} images - using multimodal chunking")

                    base_metadata.update({
                        "document_type": "pdf",
                        "total_pages": multimodal_data['total_pages'],
                        "total_images": multimodal_data['total_images'],
                        "has_images": True
                    })

                    # Chunk with image context
                    chunks = chunker.chunk_multimodal_pdf(
                        pages_data=multimodal_data['pages'],
                        metadata=base_metadata,
                        document_id=document_id
                    )

                    parsing_info = {
                        'type': 'pdf',
                        'total_pages': multimodal_data['total_pages'],
                        'total_images': multimodal_data['total_images'],
                        'chunks_created': len(chunks),
                        'multimodal': True
                    }
                else:
                    logger.info("PDF has no images - using text-only chunking")

                    # Extract page texts for regular chunking
                    page_texts = [page['text'] for page in multimodal_data['pages']]

                    base_metadata.update({
                        "document_type": "pdf",
                        "total_pages": multimodal_data['total_pages'],
                        "has_images": False
                    })

                    # Chunk by pages (text only)
                    chunks = chunker.chunk_pdf_by_pages(
                        page_texts=page_texts,
                        metadata=base_metadata,
                        document_id=document_id
                    )

                    parsing_info = {
                        'type': 'pdf',
                        'total_pages': multimodal_data['total_pages'],
                        'chunks_created': len(chunks),
                        'multimodal': False
                    }

            except Exception as e:
                logger.warning(f"Multimodal parsing failed, falling back to text-only: {e}")

                # Fall back to text-only parsing
                pdf_data = DocumentParser.parse_pdf_by_pages(content)

                base_metadata.update({
                    "document_type": "pdf",
                    "total_pages": pdf_data['total_pages'],
                    "char_count": pdf_data['total_chars'],
                })

                chunks = chunker.chunk_pdf_by_pages(
                    page_texts=pdf_data['page_texts'],
                    metadata=base_metadata,
                    document_id=document_id
                )

                parsing_info = {
                    'type': 'pdf',
                    'total_pages': pdf_data['total_pages'],
                    'char_count': pdf_data['total_chars'],
                    'chunks_created': len(chunks),
                    'multimodal': False
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
        result = await agent.rag_manager.import_documents(documents=chunks)

        # Add parsing info to result
        result['parsing_info'] = parsing_info

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_corpus(request: QueryRequest):
    """Query the RAG corpus with citations.

    Args:
        request: Query parameters

    Returns:
        Query results with document citations and clickable links
    """
    try:
        logger.info(f"Querying: {request.query}")

        result = await agent.rag_manager.query(
            query_text=request.query,
            top_k=request.top_k,
            temporal_filter=request.temporal_filter
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error querying corpus: {str(e)}")
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
        document = agent.rag_manager.get_document(document_id)

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
