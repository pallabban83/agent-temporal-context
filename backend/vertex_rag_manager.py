"""
Vertex AI RAG Manager

This module manages RAG corpus creation, document import, and querying
using Vertex AI RAG Engine with Vector Search backend.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import traceback
from google.cloud import aiplatform
from google.cloud import storage
import vertexai
from vertexai import rag
import logging

from temporal_embeddings import TemporalEmbeddingHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VertexRAGManager:
    """Manages Vertex AI RAG corpus operations."""

    def __init__(
        self,
        project_id: str,
        location: str,
        corpus_name: str,
        embedding_handler: TemporalEmbeddingHandler,
        gcs_bucket_name: Optional[str] = None,
        vector_search_index: Optional[str] = None,
        vector_search_endpoint: Optional[str] = None
    ):
        """Initialize the RAG manager using RAG Engine with existing Vector Search.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            corpus_name: Display name for the RAG corpus
            embedding_handler: Handler for temporal embeddings
            gcs_bucket_name: Optional GCS bucket for metadata storage
            vector_search_index: Optional existing Vector Search index resource name
                Format: projects/{PROJECT_NUMBER}/locations/{LOCATION}/indexes/{INDEX_ID}
            vector_search_endpoint: Optional existing Vector Search endpoint resource name
                Format: projects/{PROJECT_NUMBER}/locations/{LOCATION}/indexEndpoints/{ENDPOINT_ID}
        """
        self.project_id = project_id
        self.location = location
        self.corpus_name = corpus_name
        self.embedding_handler = embedding_handler
        self.gcs_bucket_name = gcs_bucket_name or f"{project_id}-vector-search"
        self.vector_search_index = vector_search_index
        self.vector_search_endpoint = vector_search_endpoint

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.storage_client = storage.Client(project=project_id)

        # RAG corpus resource (will be populated when corpus is created/loaded)
        self.rag_corpus: Optional[rag.RagCorpus] = None

        # Document metadata cache for temporal context
        self.document_metadata: Dict[str, Dict[str, Any]] = {}

        # Load existing metadata from GCS if available
        self._load_metadata_from_gcs()

        # Try to load existing RAG corpus
        self._load_existing_corpus()

    def _load_existing_corpus(self):
        """Load existing RAG corpus from saved resource name or by display name."""
        try:
            # First, try to load from saved resource name in environment
            corpus_resource_name = os.getenv('RAG_CORPUS_RESOURCE_NAME')
            if corpus_resource_name:
                try:
                    self.rag_corpus = rag.get_corpus(name=corpus_resource_name)
                    logger.info(f"✓ Loaded RAG corpus from saved resource name: {self.rag_corpus.name}")
                    return
                except Exception as e:
                    logger.warning(f"Saved corpus resource name not found, trying by display name: {str(e)}")

            # Fallback: List all corpora and find by display name
            corpora = rag.list_corpora()
            for corpus in corpora:
                if corpus.display_name == self.corpus_name:
                    self.rag_corpus = corpus
                    logger.info(f"✓ Loaded existing RAG corpus by display name: {corpus.name}")
                    # Save for next time
                    self._save_corpus_to_env(corpus.name)
                    return
            logger.info(f"No existing RAG corpus found with name: {self.corpus_name}")
        except Exception as e:
            logger.warning(f"Could not load existing corpus: {str(e)}")

    async def create_vector_search_infrastructure(
        self,
        description: str = "Vector Search for Temporal RAG",
        dimensions: int = 768,
        index_algorithm: str = "brute_force"
    ) -> Dict[str, Any]:
        """Create Vector Search index and endpoint from scratch.

        This creates the underlying infrastructure needed for RAG corpus.
        After creation, the resource names are returned and should be configured
        as VECTOR_SEARCH_INDEX and VECTOR_SEARCH_INDEX_ENDPOINT.

        Args:
            description: Description of the index
            dimensions: Embedding dimensions (768 for text-embedding-005)
            index_algorithm: 'brute_force' (fast) or 'tree_ah' (production)

        Returns:
            Resource names for index and endpoint
        """
        try:
            logger.info(f"Creating Vector Search infrastructure for: {self.corpus_name}")

            # Ensure GCS bucket exists
            self._ensure_bucket_exists()

            # GCS path for index storage
            contents_delta_uri = f"gs://{self.gcs_bucket_name}/vector_search_indices/{self.corpus_name}"

            # Create Vector Search index based on algorithm
            from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint

            if index_algorithm == "brute_force":
                logger.info(f"Creating BruteForce index with StreamUpdate enabled (fast deployment, exact search)")
                index = MatchingEngineIndex.create_brute_force_index(
                    display_name=self.corpus_name,
                    contents_delta_uri=contents_delta_uri,
                    description=description,
                    dimensions=dimensions,
                    distance_measure_type="DOT_PRODUCT_DISTANCE",
                    # REQUIRED: Enable streaming updates for RAG Engine compatibility
                    index_update_method="STREAM_UPDATE",
                )
                machine_type = "e2-standard-16"
            else:  # tree_ah
                logger.info(f"Creating TreeAH index with StreamUpdate enabled (slower deployment, approximate search)")
                index = MatchingEngineIndex.create_tree_ah_index(
                    display_name=self.corpus_name,
                    contents_delta_uri=contents_delta_uri,
                    description=description,
                    dimensions=dimensions,
                    approximate_neighbors_count=10,
                    distance_measure_type="DOT_PRODUCT_DISTANCE",
                    leaf_node_embedding_count=500,
                    leaf_nodes_to_search_percent=7,
                    # REQUIRED: Enable streaming updates for RAG Engine compatibility
                    index_update_method="STREAM_UPDATE",
                )
                machine_type = "e2-standard-16"

            logger.info(f"✓ Vector Search index created: {index.resource_name}")

            # Create index endpoint
            index_endpoint = MatchingEngineIndexEndpoint.create(
                display_name=f"{self.corpus_name}-endpoint",
                description=f"Endpoint for {description}",
                public_endpoint_enabled=True
            )

            logger.info(f"✓ Index endpoint created: {index_endpoint.resource_name}")

            # Deploy index to endpoint
            logger.info(f"Deploying index with machine type: {machine_type}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            deployed_index_id = f"{self.corpus_name.replace('-', '_')}_{timestamp}"

            index_endpoint.deploy_index(
                index=index,
                deployed_index_id=deployed_index_id,
                display_name=f"{self.corpus_name}-deployed",
                machine_type=machine_type,
                min_replica_count=1,
                max_replica_count=1
            )

            logger.info("✓ Index deployed to endpoint")

            # Update instance variables
            self.vector_search_index = index.resource_name
            self.vector_search_endpoint = index_endpoint.resource_name

            # Update .env file with new resource names
            self._update_env_file(index.resource_name, index_endpoint.resource_name)

            return {
                "index_resource_name": index.resource_name,
                "endpoint_resource_name": index_endpoint.resource_name,
                "deployed_index_id": deployed_index_id,
                "status": "created",
                "created_at": datetime.now().isoformat(),
                "message": "Vector Search infrastructure created successfully. Environment variables updated."
            }

        except Exception as e:
            logger.error(f"Error creating Vector Search infrastructure: {str(e)}")
            raise

    def _save_corpus_to_env(self, corpus_resource_name: str):
        """Save RAG corpus resource name to .env file for persistence.

        Args:
            corpus_resource_name: Full resource name of the RAG corpus
        """
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

            if not os.path.exists(env_path):
                logger.warning(f".env file not found at {env_path}")
                return

            # Read current content
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Check if RAG_CORPUS_RESOURCE_NAME already exists
            corpus_line_exists = False
            updated_lines = []

            for line in lines:
                if line.startswith('RAG_CORPUS_RESOURCE_NAME='):
                    # Update existing line
                    updated_lines.append(f'RAG_CORPUS_RESOURCE_NAME={corpus_resource_name}\n')
                    corpus_line_exists = True
                    logger.info(f"Updated RAG_CORPUS_RESOURCE_NAME in .env")
                else:
                    updated_lines.append(line)

            # Add new line if it doesn't exist
            if not corpus_line_exists:
                # Add after VERTEX_AI_CORPUS_NAME
                final_lines = []
                for line in updated_lines:
                    final_lines.append(line)
                    if line.startswith('VERTEX_AI_CORPUS_NAME='):
                        final_lines.append(f'RAG_CORPUS_RESOURCE_NAME={corpus_resource_name}\n')
                updated_lines = final_lines
                logger.info(f"Added RAG_CORPUS_RESOURCE_NAME to .env")

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(updated_lines)

            logger.info(f"✓ Saved RAG corpus resource name to .env")

            # Update environment variable in current process
            os.environ['RAG_CORPUS_RESOURCE_NAME'] = corpus_resource_name

        except Exception as e:
            logger.warning(f"Could not update .env file: {str(e)}")

    def _clear_corpus_from_env(self):
        """Clear RAG corpus resource name from .env file after deletion."""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

            if not os.path.exists(env_path):
                logger.warning(f".env file not found at {env_path}")
                return

            # Read current content
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Remove RAG_CORPUS_RESOURCE_NAME line
            updated_lines = []
            for line in lines:
                if not line.startswith('RAG_CORPUS_RESOURCE_NAME='):
                    updated_lines.append(line)
                else:
                    logger.info(f"Removed: {line.strip()}")

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(updated_lines)

            logger.info("✓ Cleared RAG corpus configuration from .env file")

            # Update environment variable in current process
            if 'RAG_CORPUS_RESOURCE_NAME' in os.environ:
                del os.environ['RAG_CORPUS_RESOURCE_NAME']

        except Exception as e:
            logger.warning(f"Could not update .env file: {str(e)}")

    def _clear_vector_search_from_env(self):
        """Clear Vector Search resource names from .env file after deletion."""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

            if not os.path.exists(env_path):
                logger.warning(f".env file not found at {env_path}")
                return

            # Read current content
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Update lines - comment out or remove Vector Search entries
            updated_lines = []
            for line in lines:
                # Skip or comment out Vector Search lines
                if line.startswith('VECTOR_SEARCH_INDEX=') or line.startswith('VECTOR_SEARCH_INDEX_ENDPOINT='):
                    # Comment out instead of removing to preserve history
                    updated_lines.append(f"# {line}")
                    logger.info(f"Commented out: {line.strip()}")
                else:
                    updated_lines.append(line)

            # Write back
            with open(env_path, 'w') as f:
                f.writelines(updated_lines)

            logger.info("✓ Cleared Vector Search configuration from .env file")

            # Update environment variables in current process
            if 'VECTOR_SEARCH_INDEX' in os.environ:
                del os.environ['VECTOR_SEARCH_INDEX']
            if 'VECTOR_SEARCH_INDEX_ENDPOINT' in os.environ:
                del os.environ['VECTOR_SEARCH_INDEX_ENDPOINT']

        except Exception as e:
            logger.warning(f"Could not update .env file: {str(e)}")

    def _update_env_file(self, index_resource_name: str, endpoint_resource_name: str):
        """Update .env file with Vector Search resource names.

        Args:
            index_resource_name: Full resource name of the index
            endpoint_resource_name: Full resource name of the endpoint
        """
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

            if not os.path.exists(env_path):
                logger.warning(f".env file not found at {env_path}")
                return

            # Read current .env content
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Update or add Vector Search variables
            updated = False
            index_updated = False
            endpoint_updated = False

            for i, line in enumerate(lines):
                if line.startswith('VECTOR_SEARCH_INDEX='):
                    lines[i] = f'VECTOR_SEARCH_INDEX={index_resource_name}\n'
                    index_updated = True
                elif line.startswith('VECTOR_SEARCH_INDEX_ENDPOINT='):
                    lines[i] = f'VECTOR_SEARCH_INDEX_ENDPOINT={endpoint_resource_name}\n'
                    endpoint_updated = True

            # Add if not found
            if not index_updated:
                # Find position after VERTEX_AI_CORPUS_NAME
                for i, line in enumerate(lines):
                    if line.startswith('VERTEX_AI_CORPUS_NAME='):
                        lines.insert(i + 1, f'\n# Vector Search Backend (auto-generated)\n')
                        lines.insert(i + 2, f'VECTOR_SEARCH_INDEX={index_resource_name}\n')
                        break

            if not endpoint_updated:
                # Find position after VECTOR_SEARCH_INDEX
                for i, line in enumerate(lines):
                    if line.startswith('VECTOR_SEARCH_INDEX='):
                        lines.insert(i + 1, f'VECTOR_SEARCH_INDEX_ENDPOINT={endpoint_resource_name}\n')
                        break

            # Write updated content
            with open(env_path, 'w') as f:
                f.writelines(lines)

            logger.info(f"✓ Updated .env file with Vector Search resource names")

            # Update environment variables in current process
            os.environ['VECTOR_SEARCH_INDEX'] = index_resource_name
            os.environ['VECTOR_SEARCH_INDEX_ENDPOINT'] = endpoint_resource_name

        except Exception as e:
            logger.error(f"Error updating .env file: {str(e)}")

    async def create_corpus(
        self,
        description: str = "Temporal context RAG corpus",
        dimensions: int = 768
    ) -> Dict[str, Any]:
        """Create a new RAG corpus using existing Vector Search index/endpoint.

        This uses Vertex AI RAG Engine to wrap an existing Vector Search backend.
        The index must have STREAM_UPDATE enabled and DOT_PRODUCT_DISTANCE measure.

        Args:
            description: Description of the corpus
            dimensions: Embedding dimensions (768 for text-embedding-005)

        Returns:
            Corpus creation details
        """
        try:
            logger.info(f"Creating RAG corpus: {self.corpus_name}")

            # Ensure GCS bucket exists for metadata storage
            self._ensure_bucket_exists()

            # Configure embedding model
            embedding_model_config = rag.RagEmbeddingModelConfig(
                vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                    publisher_model="publishers/google/models/text-embedding-005"
                )
            )

            # Configure Vector Search backend
            if self.vector_search_index and self.vector_search_endpoint:
                logger.info(f"Using existing Vector Search index: {self.vector_search_index}")
                logger.info(f"Using existing Vector Search endpoint: {self.vector_search_endpoint}")

                vector_db = rag.VertexVectorSearch(
                    index=self.vector_search_index,
                    index_endpoint=self.vector_search_endpoint
                )
            else:
                raise ValueError(
                    "vector_search_index and vector_search_endpoint must be provided. "
                    "Create a Vector Search index with STREAM_UPDATE enabled first."
                )

            # Create RAG corpus
            corpus = rag.create_corpus(
                display_name=self.corpus_name,
                description=description,
                backend_config=rag.RagVectorDbConfig(
                    rag_embedding_model_config=embedding_model_config,
                    vector_db=vector_db,
                ),
            )

            self.rag_corpus = corpus
            logger.info(f"✓ RAG corpus created: {corpus.name}")

            # Save corpus resource name to .env for persistence
            self._save_corpus_to_env(corpus.name)

            return {
                "corpus_name": self.corpus_name,
                "corpus_resource_name": corpus.name,
                "index_resource_name": self.vector_search_index,
                "endpoint_resource_name": self.vector_search_endpoint,
                "status": "created",
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating corpus: {error_msg}")

            # Provide helpful error message for common issues
            if "Only empty index is supported" in error_msg:
                raise ValueError(
                    "RAG Engine requires an empty Vector Search index. "
                    "Your index currently contains documents. Options: "
                    "1) Clear all documents from the index first, then create corpus. "
                    "2) Use STEP 1 to create new Vector Search infrastructure."
                )
            raise

    async def import_documents(
        self,
        documents: List[Dict[str, Any]],
        bucket_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Import documents into the RAG corpus.

        Args:
            documents: List of documents with 'content', 'metadata', and optional 'id'
            bucket_name: Optional GCS bucket for storing documents

        Returns:
            Import operation details
        """
        # Ensure RAG corpus exists
        if not self.rag_corpus:
            self._load_existing_corpus()

        if not self.rag_corpus:
            raise ValueError("Corpus not found. Please create a corpus first using /corpus/create")

        # Ensure Vector Search infrastructure is configured
        if not self.vector_search_index or not self.vector_search_endpoint:
            raise ValueError("Vector Search infrastructure not configured. Please run STEP 1 to create Vector Search infrastructure.")

        try:
            logger.info(f"Importing {len(documents)} documents")

            # Generate embeddings for all documents
            contents = [doc['content'] for doc in documents]
            metadata_list = [doc.get('metadata', {}) for doc in documents]

            embeddings = self.embedding_handler.generate_batch_embeddings(
                contents,
                metadata_list
            )

            # Prepare data points for Vector Search
            datapoints = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")

                # Create metadata with temporal info
                metadata = doc.get('metadata', {})
                metadata['content_preview'] = doc['content'][:200]
                metadata['indexed_at'] = datetime.now().isoformat()

                # Store full document metadata for citations
                self.document_metadata[doc_id] = {
                    'id': doc_id,
                    'content': doc['content'],
                    'metadata': metadata,
                    'source': metadata.get('source_url') or metadata.get('filename', 'Unknown'),
                    'title': metadata.get('title', metadata.get('filename', f'Document {i+1}')),
                    'images': doc.get('images', [])  # Preserve images for multimodal chunks
                }

                # Create datapoint for upsert
                # Convert embedding to list format
                vector = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

                datapoints.append({
                    "datapoint_id": doc_id,
                    "feature_vector": vector
                })

            # Store documents in GCS if bucket provided (or use default bucket)
            storage_bucket = bucket_name or self.gcs_bucket_name
            gcs_paths = self._store_documents_in_gcs(storage_bucket, documents, datapoints)

            # Update metadata with GCS paths for citations
            for doc_id, gcs_path in gcs_paths.items():
                if doc_id in self.document_metadata:
                    self.document_metadata[doc_id]['gcs_path'] = gcs_path
                    # Generate authenticated URL for direct document access
                    object_path = gcs_path.replace(f'gs://{storage_bucket}/', '')
                    self.document_metadata[doc_id]['gcs_url'] = f"https://storage.cloud.google.com/{storage_bucket}/{object_path}"
                    # Also store console URL for reference
                    self.document_metadata[doc_id]['gcs_console_url'] = f"https://console.cloud.google.com/storage/browser/_details/{storage_bucket}/{object_path}"

            # Update index with new embeddings using streaming update
            if self.vector_search_index:
                logger.info(f"Upserting {len(datapoints)} datapoints to index...")
                try:
                    # Use the index service client directly for upsert operations
                    from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
                    from google.cloud.aiplatform_v1.types import UpsertDatapointsRequest, IndexDatapoint

                    # Create index service client
                    client = IndexServiceClient(client_options={"api_endpoint": f"{self.location}-aiplatform.googleapis.com"})

                    # Build IndexDatapoint objects
                    index_datapoints = []
                    for dp in datapoints:
                        # Create IndexDatapoint using dict format for protobuf compatibility
                        datapoint = IndexDatapoint({
                            "datapoint_id": dp["datapoint_id"],
                            "feature_vector": dp["feature_vector"]
                        })
                        index_datapoints.append(datapoint)
                        logger.info(f"  - Datapoint: {dp['datapoint_id']} (vector dim: {len(dp['feature_vector'])})")

                    # Create and send upsert request
                    request = UpsertDatapointsRequest(
                        index=self.vector_search_index,
                        datapoints=index_datapoints
                    )

                    logger.info(f"Sending upsert request for {len(index_datapoints)} datapoints...")
                    response = client.upsert_datapoints(request=request)
                    logger.info(f"✓ Successfully upserted {len(datapoints)} vectors to index!")
                    logger.info(f"✓ Vectors are now searchable in the corpus")
                except Exception as e:
                    logger.error(f"✗ Error upserting datapoints: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue anyway - documents are stored in GCS
                    logger.warning("⚠ Documents stored in GCS but NOT searchable - vectors failed to upload")

            # Save metadata to GCS for persistence
            self._save_metadata_to_gcs()

            # HYBRID APPROACH: Register GCS documents with RAG Engine
            # This tells RAG Engine where to fetch text content when retrieving vectors
            # RAG Engine will use our manually-upserted temporal embeddings (already in index)
            rag_import_status = None
            if self.rag_corpus:
                try:
                    logger.info("Registering GCS documents with RAG Engine...")
                    logger.info(f"GCS paths to import: {list(gcs_paths.values())}")

                    # Import files from GCS into RAG corpus
                    # RAG Engine will read the JSON files and associate them with vectors
                    import_response = rag.import_files(
                        corpus_name=self.rag_corpus.name,
                        paths=list(gcs_paths.values()),  # GCS URIs: gs://bucket/path/doc_id.json
                    )

                    logger.info(f"✓ Documents registered with RAG Engine")
                    logger.info(f"  Import response: {import_response}")
                    rag_import_status = "success"

                except Exception as e:
                    logger.error(f"✗ Failed to register documents with RAG Engine: {str(e)}")
                    logger.error(f"  Full error: {traceback.format_exc()}")
                    logger.warning("Vectors are searchable but RAG retrieval won't return text content")
                    rag_import_status = f"failed: {str(e)}"

            return {
                "status": "imported",
                "document_count": len(documents),
                "imported_at": datetime.now().isoformat(),
                "datapoints_created": len(datapoints),
                "rag_import_status": rag_import_status,
                "hybrid_mode": True  # Manual temporal embeddings + RAG Engine text retrieval
            }

        except Exception as e:
            logger.error(f"Error importing documents: {str(e)}")
            raise

    async def register_existing_documents_with_rag(self, bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """Register existing GCS documents with RAG Engine.

        This is useful when documents were already upserted to Vector Search
        but need to be registered with RAG Engine for text retrieval.

        Args:
            bucket_name: Optional GCS bucket name (uses default if not provided)

        Returns:
            Registration status and details
        """
        # Ensure RAG corpus exists
        if not self.rag_corpus:
            self._load_existing_corpus()

        if not self.rag_corpus:
            raise ValueError("Corpus not found. Please create a corpus first using /corpus/create")

        try:
            storage_bucket = bucket_name or self.gcs_bucket_name
            bucket = self.storage_client.bucket(storage_bucket)

            # List all document JSON files in GCS
            prefix = f"rag_corpus/{self.corpus_name}/documents/"
            blobs = bucket.list_blobs(prefix=prefix)

            gcs_paths = []
            for blob in blobs:
                if blob.name.endswith('.json'):
                    gcs_path = f"gs://{storage_bucket}/{blob.name}"
                    gcs_paths.append(gcs_path)

            if not gcs_paths:
                return {
                    "status": "no_documents",
                    "message": f"No documents found in GCS path: gs://{storage_bucket}/{prefix}"
                }

            logger.info(f"Found {len(gcs_paths)} documents in GCS to register")
            logger.info(f"First few paths: {gcs_paths[:5]}")

            # Register GCS documents with RAG Engine in batches
            # RAG Engine has a limit of 25 GCS URIs per import_files call
            batch_size = 25
            total_batches = (len(gcs_paths) + batch_size - 1) // batch_size
            logger.info(f"Registering {len(gcs_paths)} documents in {total_batches} batches of {batch_size}...")

            import_responses = []
            for i in range(0, len(gcs_paths), batch_size):
                batch = gcs_paths[i:i + batch_size]
                batch_num = (i // batch_size) + 1

                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} documents)...")

                try:
                    import_response = rag.import_files(
                        corpus_name=self.rag_corpus.name,
                        paths=batch,
                    )
                    import_responses.append(import_response)
                    logger.info(f"✓ Batch {batch_num}/{total_batches} completed")
                except Exception as batch_error:
                    logger.error(f"✗ Batch {batch_num}/{total_batches} failed: {str(batch_error)}")
                    # Continue with next batch even if this one fails

            logger.info(f"✓ Successfully registered {len(gcs_paths)} documents with RAG Engine")
            logger.info(f"Completed {len(import_responses)}/{total_batches} batches")

            return {
                "status": "success",
                "documents_registered": len(gcs_paths),
                "batches_processed": len(import_responses),
                "total_batches": total_batches,
                "corpus_name": self.rag_corpus.name,
                "gcs_bucket": storage_bucket,
            }

        except Exception as e:
            logger.error(f"Error registering documents with RAG Engine: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _format_citation(self, doc_id: str, doc_info: Dict[str, Any]) -> Dict[str, str]:
        """Format citation information for a document.

        Args:
            doc_id: Document ID
            doc_info: Document metadata

        Returns:
            Formatted citation with clickable links
        """
        citation = {
            "document_id": doc_id,
            "title": doc_info.get('title', 'Unknown Document'),
            "source": doc_info.get('source', 'Unknown'),
        }

        # Priority 1: Original file URL (the actual uploaded document)
        metadata = doc_info.get('metadata', {})
        if 'original_file_url' in metadata:
            citation['original_file_url'] = metadata['original_file_url']
            citation['clickable_link'] = metadata['original_file_url']

        # Priority 2: External source URL if provided
        elif metadata.get('source_url'):
            citation['source_url'] = metadata['source_url']
            citation['clickable_link'] = metadata['source_url']

        # Priority 3: GCS chunk JSON (fallback)
        elif 'gcs_url' in doc_info:
            citation['gcs_chunk_url'] = doc_info['gcs_url']
            citation['clickable_link'] = doc_info['gcs_url']

        # Also add console URL if available
        if 'gcs_console_url' in doc_info:
            citation['gcs_console_url'] = doc_info['gcs_console_url']

        # Add temporal information
        metadata = doc_info.get('metadata', {})
        if 'document_date' in metadata:
            citation['date'] = metadata['document_date']
        if 'indexed_at' in metadata:
            citation['indexed_at'] = metadata['indexed_at']

        # Format as a readable citation string
        citation_parts = [citation['title']]
        if citation.get('date'):
            citation_parts.append(f"({citation['date']})")
        if citation.get('source') != 'Unknown':
            citation_parts.append(f"Source: {citation['source']}")

        citation['formatted'] = '. '.join(citation_parts)

        return citation

    def _ensure_bucket_exists(self):
        """Ensure the GCS bucket exists, create if it doesn't."""
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            if not bucket.exists():
                logger.info(f"Creating GCS bucket: {self.gcs_bucket_name}")
                bucket = self.storage_client.create_bucket(
                    self.gcs_bucket_name,
                    location=self.location
                )
                logger.info(f"Bucket created: {self.gcs_bucket_name}")
            else:
                logger.info(f"Using existing bucket: {self.gcs_bucket_name}")
        except Exception as e:
            logger.warning(f"Bucket check/creation failed: {str(e)}")
            # Continue anyway - the bucket might exist but we don't have list permissions

    def store_original_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """Store original uploaded file in GCS.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            content_type: MIME type
            bucket_name: Optional bucket name

        Returns:
            Authenticated GCS URL for the file
        """
        try:
            bucket = self.storage_client.bucket(bucket_name or self.gcs_bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Store with timestamp to avoid overwrites
            blob_name = f"rag_corpus/{self.corpus_name}/original_files/{timestamp}_{filename}"
            blob = bucket.blob(blob_name)

            blob.upload_from_string(
                file_content,
                content_type=content_type
            )

            # Return authenticated URL
            authenticated_url = f"https://storage.cloud.google.com/{bucket.name}/{blob_name}"
            logger.info(f"Stored original file: {authenticated_url}")
            return authenticated_url

        except Exception as e:
            logger.error(f"Error storing original file: {str(e)}")
            raise

    def _store_documents_in_gcs(
        self,
        bucket_name: str,
        documents: List[Dict[str, Any]],
        datapoints: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Store documents and embeddings in GCS.

        Args:
            bucket_name: GCS bucket name
            documents: Original documents
            datapoints: Embedding datapoints

        Returns:
            Dict mapping document IDs to GCS paths
        """
        gcs_paths = {}
        try:
            bucket = self.storage_client.bucket(bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Store individual documents for easy retrieval
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{timestamp}")
                doc_blob_name = f"rag_corpus/{self.corpus_name}/documents/{doc_id}.json"
                doc_blob = bucket.blob(doc_blob_name)

                doc_blob.upload_from_string(
                    json.dumps(doc, indent=2),
                    content_type='application/json'
                )

                gcs_paths[doc_id] = f"gs://{bucket_name}/{doc_blob_name}"

            # Also store batch for backup
            batch_blob_name = f"rag_corpus/{self.corpus_name}/batches/documents_{timestamp}.json"
            batch_blob = bucket.blob(batch_blob_name)

            batch_blob.upload_from_string(
                json.dumps(documents, indent=2),
                content_type='application/json'
            )

            # Store embeddings
            embeddings_blob_name = f"rag_corpus/{self.corpus_name}/batches/embeddings_{timestamp}.json"
            embeddings_blob = bucket.blob(embeddings_blob_name)

            embeddings_blob.upload_from_string(
                json.dumps(datapoints, indent=2),
                content_type='application/json'
            )

            logger.info(f"Stored {len(documents)} documents in GCS: {batch_blob_name}")
            return gcs_paths

        except Exception as e:
            logger.error(f"Error storing in GCS: {str(e)}")
            raise

    def _detect_temporal_intent(self, query_text: str) -> bool:
        """Detect if query has temporal intent (latest, most recent, etc.).

        Args:
            query_text: The query text

        Returns:
            True if temporal keywords detected
        """
        temporal_keywords = [
            'latest', 'most recent', 'newest', 'current', 'recent',
            'last', 'up to date', 'up-to-date', 'today', 'this year',
            'this quarter', 'this month'
        ]

        query_lower = query_text.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)

    def _extract_temporal_filter_from_query(self, query_text: str) -> Optional[Dict[str, Any]]:
        """Extract temporal filter criteria from query text.

        Analyzes the query to find dates, years, quarters, and creates a filter.

        Args:
            query_text: The query text

        Returns:
            Temporal filter dict or None if no temporal info found
        """
        # Extract temporal information using the embedding handler
        # Returns a list of entities: [{'type': 'date', 'value': '2024-10-21', 'position': (0, 10)}, ...]
        temporal_entities = self.embedding_handler.extract_temporal_info(query_text)

        if not temporal_entities:
            return None

        # Separate dates and years
        dates = [e['value'] for e in temporal_entities if e['type'] == 'date']
        years = [e['value'] for e in temporal_entities if e['type'] == 'year']

        # Build filter based on extracted info
        filter_criteria = {}

        # If specific dates found, use the first one as reference
        if dates:
            # Use the first date found as filter
            filter_criteria['document_date'] = dates[0]
            logger.info(f"Extracted date filter from query: {dates[0]}")

        # If years found but no specific dates
        elif years:
            # Use the most recent year
            year = max(years)
            filter_criteria['year'] = str(year)
            logger.info(f"Extracted year filter from query: {year}")

        return filter_criteria if filter_criteria else None

    def _apply_temporal_filter(self, results: List[Dict[str, Any]], temporal_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results based on temporal criteria.

        Args:
            results: List of search results
            temporal_filter: Filter criteria (e.g., {'document_date': '2024-10-01'} or {'year': '2024'})

        Returns:
            Filtered results
        """
        if not temporal_filter or not results:
            return results

        filtered = []
        filter_type = None
        filter_value = None

        # Determine filter type
        if 'document_date' in temporal_filter:
            filter_type = 'date'
            filter_value = temporal_filter['document_date']
        elif 'year' in temporal_filter:
            filter_type = 'year'
            filter_value = temporal_filter['year']

        if not filter_type:
            logger.warning(f"Unrecognized temporal filter format: {temporal_filter}")
            return results

        # Apply filter
        for result in results:
            metadata = result.get('metadata', {})
            doc_date = metadata.get('document_date', '')

            if filter_type == 'date':
                # Match exact date or date prefix (e.g., "2024-10" matches "2024-10-21")
                if doc_date.startswith(filter_value):
                    filtered.append(result)
            elif filter_type == 'year':
                # Match year in document_date
                if filter_value in doc_date:
                    filtered.append(result)

        logger.info(f"Temporal filter applied: {len(filtered)}/{len(results)} results matched {filter_type}={filter_value}")
        return filtered

    def _sort_by_recency(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort results by document date (most recent first).

        Args:
            results: Query results

        Returns:
            Sorted results
        """
        def get_date_key(result):
            # Try to get document_date from metadata
            metadata = result.get('metadata', {})
            doc_date = metadata.get('document_date')

            if doc_date:
                try:
                    # Parse various date formats
                    from dateutil import parser
                    parsed_date = parser.parse(doc_date)
                    return parsed_date
                except:
                    pass

            # Fallback: use uploaded_at or very old date
            uploaded_at = metadata.get('uploaded_at')
            if uploaded_at:
                try:
                    from dateutil import parser
                    return parser.parse(uploaded_at)
                except:
                    pass

            # No date found, use minimum date
            from datetime import datetime
            return datetime.min

        # Sort by date descending (most recent first)
        sorted_results = sorted(results, key=get_date_key, reverse=True)
        logger.info(f"Sorted {len(sorted_results)} results by recency")

        return sorted_results

    async def query(
        self,
        query_text: str,
        top_k: int = 20,
        temporal_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query the RAG corpus using RAG Engine retrieval API.

        Args:
            query_text: Query text
            top_k: Number of results to return
            temporal_filter: Optional temporal filtering criteria

        Returns:
            Query results with relevant documents and temporal context
        """
        # Ensure RAG corpus exists
        if not self.rag_corpus:
            self._load_existing_corpus()

        if not self.rag_corpus:
            raise ValueError("Corpus not found. Please create a corpus first using /corpus/create")

        try:
            logger.info(f"Querying RAG corpus: {query_text}")

            # Use RAG Engine's retrieval_query API
            logger.info(f"Using RAG Engine retrieval API with corpus: {self.rag_corpus.name}")

            # Build retrieval configuration
            retrieval_config = rag.RagRetrievalConfig(
                top_k=top_k,
                # Optional: vector distance threshold for filtering
                filter=rag.utils.resources.Filter(vector_distance_threshold=0.1)
            )

            # Execute RAG retrieval query
            rag_response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=self.rag_corpus.name,
                        # Optional: filter by specific files if needed
                    )
                ],
                text=query_text,
                rag_retrieval_config=retrieval_config,
            )

            logger.info(f"RAG retrieval response received")
            logger.info(f"Response type: {type(rag_response)}")
            logger.info(f"Response: {rag_response}")

            # Format results from RAG Engine response
            results = []
            if hasattr(rag_response, 'contexts') and rag_response.contexts:
                logger.info(f"Found {len(rag_response.contexts.contexts)} contexts in RAG response")

                for idx, context in enumerate(rag_response.contexts.contexts):
                    # Debug: log all available attributes
                    logger.info(f"Context {idx} attributes: {dir(context)}")
                    logger.info(f"Context {idx} full object: {context}")

                    # Extract information from RAG context
                    # The score field is the similarity score (higher is better)
                    score = context.score if hasattr(context, 'score') else 0.0
                    source_uri = context.source_uri if hasattr(context, 'source_uri') else None
                    text_content = context.text if hasattr(context, 'text') else ""

                    logger.info(f"Context {idx}: score={score}, source_uri={source_uri}, text_len={len(text_content)}")

                    # Try to extract document ID from source_uri
                    # Source URI format might be gs://bucket/path/to/doc_id.json
                    doc_id = None
                    if source_uri:
                        # Extract filename from GCS path
                        import os
                        doc_id = os.path.basename(source_uri).replace('.json', '')

                    # Try to find metadata using document ID or content matching
                    doc_info = {}
                    metadata = {}

                    if doc_id and doc_id in self.document_metadata:
                        doc_info = self.document_metadata[doc_id]
                        metadata = doc_info.get('metadata', {})
                        logger.info(f"Found metadata for {doc_id}")
                    else:
                        # No metadata found - use RAG Engine data directly
                        logger.warning(f"No metadata found for document from source: {source_uri}")
                        metadata = {'source_uri': source_uri}

                    # Create result with available information
                    result = {
                        "id": doc_id or f"rag_result_{idx}",
                        "score": score,  # Use RAG Engine's score directly (higher is better)
                        "title": doc_info.get('title') or metadata.get('filename', 'RAG Document'),
                        "content": text_content,
                        "content_preview": text_content[:300] + '...' if len(text_content) > 300 else text_content,
                        "metadata": metadata,
                        "source_uri": source_uri,
                        "citation": self._format_citation(doc_id or f"rag_result_{idx}", doc_info) if doc_info else source_uri,
                        "images": doc_info.get('images', []) if doc_info else []
                    }
                    results.append(result)
                    logger.info(f"  - Result {idx + 1}: {result['id']} (score: {result['score']:.4f})")
            else:
                logger.warning("No contexts found in RAG response")

            # RAG Engine returns results sorted by relevance
            # Ensure results are sorted by score descending (best match first)
            if results:
                results.sort(key=lambda x: x['score'], reverse=True)
                logger.info(f"Results sorted by similarity score (top score: {results[0]['score']:.4f})")

            # Apply temporal filtering if provided or extractable from query
            temporal_filter_applied = False
            effective_filter = temporal_filter  # Track which filter was used

            if temporal_filter and results:
                # Explicit filter provided by user
                logger.info(f"Applying explicit temporal filter: {temporal_filter}")
                results = self._apply_temporal_filter(results, temporal_filter)
                temporal_filter_applied = True
            elif not temporal_filter and results:
                # Try to extract implicit filter from query text
                implicit_filter = self._extract_temporal_filter_from_query(query_text)
                if implicit_filter:
                    logger.info(f"Applying implicit temporal filter extracted from query: {implicit_filter}")
                    results = self._apply_temporal_filter(results, implicit_filter)
                    effective_filter = implicit_filter
                    temporal_filter_applied = True

            # After filtering, re-sort by distance score
            if results:
                results.sort(key=lambda x: x['score'], reverse=True)

            # Detect temporal intent and sort by date if needed
            has_temporal_intent = self._detect_temporal_intent(query_text)
            if has_temporal_intent and results:
                logger.info(f"Temporal intent detected in query: '{query_text}'")
                logger.info("Sorting results by recency (most recent first)")
                results = self._sort_by_recency(results)
                logger.info(f"After temporal sorting, top result: {results[0].get('title', 'Unknown')}")

            return {
                "query": query_text,
                "results": results,
                "result_count": len(results),
                "temporal_filter": dict(effective_filter) if effective_filter else None,
                "temporal_filter_applied": temporal_filter_applied,
                "temporal_sort_applied": has_temporal_intent,
                "queried_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error querying corpus: {str(e)}")
            raise

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document information with citation
        """
        doc_info = self.document_metadata.get(document_id)
        if doc_info:
            return {
                **doc_info,
                "citation": self._format_citation(document_id, doc_info)
            }
        return None

    async def get_corpus_info(self) -> Dict[str, Any]:
        """Get information about the RAG corpus and Vector Search infrastructure.

        Validates actual existence of resources in Google Cloud.

        Returns:
            Corpus information including RAG corpus and Vector Search details
        """
        # Try to load existing RAG corpus if not already loaded
        if not self.rag_corpus:
            self._load_existing_corpus()

        corpus_exists = self.rag_corpus is not None

        # Verify Vector Search resources actually exist in GCP
        index_available = False
        endpoint_available = False
        index_obj = None
        endpoint_obj = None

        # Verify index exists
        if self.vector_search_index:
            try:
                from google.cloud import aiplatform
                index_obj = aiplatform.MatchingEngineIndex(index_name=self.vector_search_index)
                # Try to access a property to verify it exists
                _ = index_obj.display_name
                index_available = True
                logger.info(f"✓ Verified index exists: {index_obj.display_name}")
            except Exception as e:
                logger.warning(f"Index in config but doesn't exist in GCP: {str(e)}")
                index_available = False

        # Verify endpoint exists
        if self.vector_search_endpoint:
            try:
                from google.cloud import aiplatform
                endpoint_obj = aiplatform.MatchingEngineIndexEndpoint(
                    index_endpoint_name=self.vector_search_endpoint
                )
                # Try to access a property to verify it exists
                _ = endpoint_obj.display_name
                endpoint_available = True
                logger.info(f"✓ Verified endpoint exists: {endpoint_obj.display_name}")
            except Exception as e:
                logger.warning(f"Endpoint in config but doesn't exist in GCP: {str(e)}")
                endpoint_available = False

        info = {
            "project_id": self.project_id,
            "location": self.location,
            "index_available": index_available,
            "endpoint_available": endpoint_available,
            "corpus_available": corpus_exists,
            "status": "created" if corpus_exists else "not_created",
            "message": "Corpus is active and ready to use" if corpus_exists else "Corpus has not been created yet. Use 'Create Corpus' to initialize."
        }

        # Add RAG corpus information ONLY if corpus exists
        if self.rag_corpus:
            info["corpus_name"] = self.rag_corpus.display_name
            info["corpus_resource_name"] = self.rag_corpus.name
            if hasattr(self.rag_corpus, 'description') and self.rag_corpus.description:
                info["corpus_description"] = self.rag_corpus.description

        # Add Vector Search index information ONLY if it actually exists
        if index_available and index_obj:
            info["index_id"] = self.vector_search_index
            info["index_display_name"] = index_obj.display_name

        # Add Vector Search endpoint information ONLY if it actually exists
        if endpoint_available and endpoint_obj:
            info["endpoint_id"] = self.vector_search_endpoint
            info["endpoint_display_name"] = endpoint_obj.display_name

        return info

    async def _load_existing_resources(self):
        """Load existing Vector Search resources from GCP if they exist."""
        try:
            logger.info(f"Attempting to load existing resources for corpus: {self.corpus_display_name}")

            # List all indices in the project
            logger.info("Searching for existing indices...")
            index_list = aiplatform.MatchingEngineIndex.list()

            logger.info(f"Found {len(index_list)} total indices")

            # Filter by display name
            for idx in index_list:
                logger.info(f"Index found: {idx.display_name}")
                if idx.display_name == self.corpus_display_name:
                    self.index = idx
                    logger.info(f"✓ Loaded existing index: {self.index.resource_name}")
                    break

            # List all endpoints in the project
            logger.info("Searching for existing endpoints...")
            endpoint_list = aiplatform.MatchingEngineIndexEndpoint.list()

            logger.info(f"Found {len(endpoint_list)} total endpoints")

            # Filter by display name
            for endpoint in endpoint_list:
                logger.info(f"Endpoint found: {endpoint.display_name}")
                if endpoint.display_name == f"{self.corpus_display_name}-endpoint":
                    # Reload the endpoint to ensure we have the latest connection details
                    self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                        index_endpoint_name=endpoint.resource_name
                    )
                    logger.info(f"✓ Loaded existing endpoint: {self.index_endpoint.resource_name}")

                    # Try to find the deployed index ID
                    if self.index_endpoint.deployed_indexes:
                        # Get the first deployed index (assuming one index per endpoint)
                        self.deployed_index_id = self.index_endpoint.deployed_indexes[0].id
                        logger.info(f"✓ Found deployed index: {self.deployed_index_id}")
                    else:
                        logger.warning("Endpoint exists but no deployed indexes found")
                    break

            if not self.index:
                logger.info(f"No index found with display name: {self.corpus_display_name}")
            if not self.index_endpoint:
                logger.info(f"No endpoint found with display name: {self.corpus_display_name}-endpoint")

        except Exception as e:
            logger.error(f"Error loading existing resources: {str(e)}", exc_info=True)
            # If loading fails, resources likely don't exist

    async def clear_all_datapoints(self) -> Dict[str, Any]:
        """Remove all datapoints from the index without deleting the index itself.

        This is faster than recreating the index and endpoint.

        Returns:
            Result of the clear operation
        """
        try:
            if not self.vector_search_index:
                return {
                    "success": False,
                    "message": "No index configured to clear"
                }

            # Get all datapoint IDs from metadata
            datapoint_ids = list(self.document_metadata.keys())

            if not datapoint_ids:
                return {
                    "success": True,
                    "message": "No datapoints to clear",
                    "cleared_count": 0
                }

            logger.info(f"Clearing {len(datapoint_ids)} datapoints from index...")

            # Use IndexServiceClient to remove datapoints
            from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
            from google.cloud.aiplatform_v1.types import RemoveDatapointsRequest

            client = IndexServiceClient(
                client_options={"api_endpoint": f"{self.location}-aiplatform.googleapis.com"}
            )

            # Remove datapoints in batches (API has limits)
            batch_size = 100
            total_removed = 0

            for i in range(0, len(datapoint_ids), batch_size):
                batch = datapoint_ids[i:i + batch_size]

                request = RemoveDatapointsRequest(
                    index=self.vector_search_index,
                    datapoint_ids=batch
                )

                try:
                    client.remove_datapoints(request=request)
                    total_removed += len(batch)
                    logger.info(f"Removed batch {i//batch_size + 1}: {len(batch)} datapoints")
                except Exception as e:
                    logger.warning(f"Error removing batch: {str(e)}")
                    # Continue with other batches

            # Clear metadata
            self.document_metadata = {}
            self._clear_metadata_from_gcs()

            # Clear all GCS files and folders
            self._clear_all_gcs_files()

            logger.info(f"Successfully cleared {total_removed} datapoints from index and all GCS files")

            return {
                "success": True,
                "message": f"Cleared {total_removed} datapoints and all associated files from GCS",
                "cleared_count": total_removed
            }

        except Exception as e:
            logger.error(f"Error clearing datapoints: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "message": f"Error clearing datapoints: {str(e)}"
            }

    async def delete_vector_search_infrastructure(self) -> Dict[str, Any]:
        """Delete ONLY the Vector Search index and endpoint (not RAG corpus).

        Use this to clean up old Vector Search resources before creating new ones.

        Returns:
            Deletion status and details
        """
        try:
            logger.info("Deleting Vector Search infrastructure...")

            deleted_resources = []

            if not self.vector_search_index and not self.vector_search_endpoint:
                return {
                    "status": "nothing_to_delete",
                    "message": "No Vector Search infrastructure configured to delete"
                }

            from google.cloud import aiplatform

            # Step 1: Undeploy and delete endpoint
            if self.vector_search_endpoint:
                try:
                    logger.info(f"Processing endpoint: {self.vector_search_endpoint}")
                    endpoint = aiplatform.MatchingEngineIndexEndpoint(
                        index_endpoint_name=self.vector_search_endpoint
                    )

                    # Undeploy all deployed indexes
                    if endpoint.deployed_indexes:
                        for deployed_index in endpoint.deployed_indexes:
                            logger.info(f"Undeploying index: {deployed_index.id}")
                            endpoint.undeploy_index(deployed_index_id=deployed_index.id)
                            deleted_resources.append(f"Undeployed index: {deployed_index.id}")
                            logger.info("✓ Index undeployed successfully")

                    # Delete endpoint
                    logger.info(f"Deleting endpoint: {self.vector_search_endpoint}")
                    endpoint.delete(force=True)
                    deleted_resources.append(f"Deleted endpoint: {endpoint.display_name}")
                    logger.info("✓ Endpoint deleted successfully")
                except Exception as e:
                    logger.error(f"Error deleting endpoint: {str(e)}")
                    raise

            # Step 2: Delete index
            if self.vector_search_index:
                try:
                    logger.info(f"Deleting index: {self.vector_search_index}")
                    index = aiplatform.MatchingEngineIndex(
                        index_name=self.vector_search_index
                    )
                    index.delete()
                    deleted_resources.append(f"Deleted index: {index.display_name}")
                    logger.info("✓ Index deleted successfully")
                except Exception as e:
                    logger.error(f"Error deleting index: {str(e)}")
                    raise

            logger.info("✓ Vector Search infrastructure deletion completed")

            # Update .env file to remove the deleted resources
            self._clear_vector_search_from_env()

            # Clear in-memory references
            self.vector_search_index = None
            self.vector_search_endpoint = None

            return {
                "status": "deleted",
                "deleted_resources": deleted_resources,
                "deleted_at": datetime.now().isoformat(),
                "message": "Vector Search infrastructure deleted successfully. You can now create new infrastructure using STEP 1."
            }

        except Exception as e:
            logger.error(f"Error deleting Vector Search infrastructure: {str(e)}")
            raise

    async def delete_corpus(self) -> Dict[str, Any]:
        """Delete the corpus and all associated resources.

        Returns:
            Deletion status and details
        """
        try:
            logger.info(f"Starting deletion of corpus: {self.corpus_name}")

            deleted_resources = []

            # Step 1: Delete RAG corpus if it exists
            if self.rag_corpus:
                logger.info(f"Deleting RAG corpus: {self.rag_corpus.name}")
                try:
                    rag.delete_corpus(name=self.rag_corpus.name)
                    deleted_resources.append(f"Deleted RAG corpus: {self.rag_corpus.display_name}")
                    logger.info("✓ RAG corpus deleted successfully")
                except Exception as e:
                    logger.warning(f"Error deleting RAG corpus: {str(e)}")

            # Step 2: Delete Vector Search infrastructure if configured
            if self.vector_search_index or self.vector_search_endpoint:
                from google.cloud import aiplatform

                # Get endpoint object to undeploy index
                if self.vector_search_endpoint:
                    try:
                        logger.info(f"Getting endpoint: {self.vector_search_endpoint}")
                        endpoint = aiplatform.MatchingEngineIndexEndpoint(
                            index_endpoint_name=self.vector_search_endpoint
                        )

                        # Undeploy index if deployed
                        if endpoint.deployed_indexes:
                            deployed_index_id = endpoint.deployed_indexes[0].id
                            logger.info(f"Undeploying index: {deployed_index_id}")
                            endpoint.undeploy_index(deployed_index_id=deployed_index_id)
                            deleted_resources.append(f"Undeployed index: {deployed_index_id}")
                            logger.info("✓ Index undeployed successfully")

                        # Delete endpoint
                        logger.info(f"Deleting endpoint: {self.vector_search_endpoint}")
                        endpoint.delete(force=True)
                        deleted_resources.append(f"Deleted endpoint: {endpoint.display_name}")
                        logger.info("✓ Endpoint deleted successfully")
                    except Exception as e:
                        logger.warning(f"Error deleting endpoint: {str(e)}")

                # Delete index
                if self.vector_search_index:
                    try:
                        logger.info(f"Deleting index: {self.vector_search_index}")
                        index = aiplatform.MatchingEngineIndex(
                            index_name=self.vector_search_index
                        )
                        index.delete()
                        deleted_resources.append(f"Deleted index: {index.display_name}")
                        logger.info("✓ Index deleted successfully")
                    except Exception as e:
                        logger.warning(f"Error deleting index: {str(e)}")

            # Step 3: Clear all GCS files
            self._clear_all_gcs_files()
            deleted_resources.append("Cleared all GCS files")

            # Clear corpus from .env
            self._clear_corpus_from_env()

            # Clear local references
            self.rag_corpus = None
            self.document_metadata.clear()

            logger.info("✓ Corpus deletion completed")

            return {
                "status": "deleted",
                "corpus_name": self.corpus_name,
                "deleted_resources": deleted_resources,
                "deleted_at": datetime.now().isoformat(),
                "message": "Corpus and all associated resources have been deleted successfully"
            }

        except Exception as e:
            logger.error(f"Error deleting corpus: {str(e)}")
            raise

    def _save_metadata_to_gcs(self):
        """Save document metadata to GCS for persistence across restarts."""
        try:
            metadata_path = f"rag_corpus/{self.corpus_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(metadata_path)

            # Convert metadata to JSON
            metadata_json = json.dumps(self.document_metadata, indent=2)
            blob.upload_from_string(metadata_json, content_type='application/json')

            logger.info(f"✓ Saved metadata for {len(self.document_metadata)} documents to GCS")
        except Exception as e:
            logger.warning(f"Could not save metadata to GCS: {str(e)}")

    def _clear_metadata_from_gcs(self):
        """Clear metadata file from GCS."""
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            metadata_blob_name = f"rag_corpus/{self.corpus_name}/metadata.json"
            blob = bucket.blob(metadata_blob_name)

            if blob.exists():
                blob.delete()
                logger.info(f"Cleared metadata from GCS: {metadata_blob_name}")
        except Exception as e:
            logger.warning(f"Error clearing metadata from GCS: {str(e)}")

    def _clear_all_gcs_files(self):
        """Clear all GCS files and folders associated with this corpus."""
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)

            # List of prefixes to delete
            prefixes_to_clear = [
                f"rag_corpus/{self.corpus_name}/",  # All corpus files
                "document_images/"  # Multimodal images
            ]

            total_deleted = 0
            for prefix in prefixes_to_clear:
                # List all blobs with this prefix
                blobs = bucket.list_blobs(prefix=prefix)
                blobs_list = list(blobs)

                if blobs_list:
                    logger.info(f"Deleting {len(blobs_list)} files from {prefix}")

                    # Delete in batches
                    for blob in blobs_list:
                        try:
                            blob.delete()
                            total_deleted += 1
                        except Exception as e:
                            logger.warning(f"Could not delete {blob.name}: {str(e)}")

            logger.info(f"Cleared {total_deleted} total files from GCS")

        except Exception as e:
            logger.warning(f"Error clearing GCS files: {str(e)}")

    def _load_metadata_from_gcs(self):
        """Load document metadata from GCS."""
        try:
            metadata_path = f"rag_corpus/{self.corpus_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(metadata_path)

            if blob.exists():
                metadata_json = blob.download_as_text()
                self.document_metadata = json.loads(metadata_json)
                logger.info(f"✓ Loaded metadata for {len(self.document_metadata)} documents from GCS")
            # Silently skip if no metadata exists yet (normal for first run)
        except Exception as e:
            # Only log actual errors, not missing files
            if "404" not in str(e) and "does not exist" not in str(e).lower():
                logger.warning(f"Could not load metadata from GCS: {str(e)}")
