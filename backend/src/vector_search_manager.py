"""
Vertex AI Vector Search Manager

This module manages Vector Search index creation, document import, and querying
with temporal context awareness.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import traceback
from google.cloud import aiplatform
from google.cloud import storage
import vertexai

from temporal_embeddings import TemporalEmbeddingHandler
from logging_config import get_logger

logger = get_logger(__name__)


class VectorSearchManager:
    """Manages Vertex AI Vector Search operations."""

    def __init__(
        self,
        project_id: str,
        location: str,
        index_name: str,
        embedding_handler: TemporalEmbeddingHandler,
        gcs_bucket_name: Optional[str] = None,
        vector_search_index: Optional[str] = None,
        vector_search_endpoint: Optional[str] = None
    ):
        """Initialize the Vector Search manager.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            index_name: Display name for the Vector Search index
            embedding_handler: Handler for temporal embeddings
            gcs_bucket_name: Optional GCS bucket for metadata storage
            vector_search_index: Optional existing Vector Search index resource name
            vector_search_endpoint: Optional existing Vector Search endpoint resource name
        """
        self.project_id = project_id
        self.location = location
        self.index_name = index_name
        self.embedding_handler = embedding_handler
        self.gcs_bucket_name = gcs_bucket_name or f"{project_id}-vector-search"
        self.vector_search_index = vector_search_index
        self.vector_search_endpoint = vector_search_endpoint

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.storage_client = storage.Client(project=project_id)

        # Index and endpoint objects
        self.index = None
        self.index_endpoint = None
        self.deployed_index_id = None

        # Document metadata cache for temporal context
        self.document_metadata: Dict[str, Dict[str, Any]] = {}

        # Load existing metadata from GCS if available
        self._load_metadata_from_gcs()

        # Try to load existing index and endpoint
        self._load_existing_resources()

    def _load_existing_resources(self):
        """Load existing Vector Search resources if they exist."""
        try:
            # Load index
            if self.vector_search_index:
                try:
                    self.index = aiplatform.MatchingEngineIndex(index_name=self.vector_search_index)
                    logger.info(
                        "Loaded existing Vector Search index",
                        extra={
                            'index_name': self.index.display_name,
                            'index_resource': self.vector_search_index
                        }
                    )
                except Exception as e:
                    logger.warning(
                        "Index configured but not found",
                        extra={
                            'index_resource': self.vector_search_index,
                            'error': str(e)
                        }
                    )
                    self.index = None

            # Load endpoint
            if self.vector_search_endpoint:
                try:
                    self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                        index_endpoint_name=self.vector_search_endpoint
                    )
                    logger.info(
                        "Loaded existing index endpoint",
                        extra={
                            'endpoint_name': self.index_endpoint.display_name,
                            'endpoint_resource': self.vector_search_endpoint
                        }
                    )

                    # Get deployed index ID
                    if self.index_endpoint.deployed_indexes:
                        self.deployed_index_id = self.index_endpoint.deployed_indexes[0].id
                        logger.info(
                            "Found deployed index",
                            extra={'deployed_index_id': self.deployed_index_id}
                        )
                except Exception as e:
                    logger.warning(
                        "Endpoint configured but not found",
                        extra={
                            'endpoint_resource': self.vector_search_endpoint,
                            'error': str(e)
                        }
                    )
                    self.index_endpoint = None

        except Exception as e:
            logger.warning(
                "Error loading existing resources",
                exc_info=True
            )

    async def create_vector_search_infrastructure(
        self,
        description: str = "Vector Search for Temporal RAG",
        dimensions: int = 768,
        index_algorithm: str = "brute_force"
    ) -> Dict[str, Any]:
        """Create Vector Search index and endpoint from scratch.

        Args:
            description: Description of the index
            dimensions: Embedding dimensions (768 for text-embedding-005)
            index_algorithm: 'brute_force' (fast) or 'tree_ah' (production)

        Returns:
            Resource names for index and endpoint
        """
        try:
            logger.info(f"Creating Vector Search infrastructure: {self.index_name}")

            # Ensure GCS bucket exists
            self._ensure_bucket_exists()

            # GCS path for index storage
            contents_delta_uri = f"gs://{self.gcs_bucket_name}/vector_search_indices/{self.index_name}"

            # Create Vector Search index
            if index_algorithm == "brute_force":
                logger.info(f"Creating BruteForce index (fast deployment, exact search)")
                self.index = aiplatform.MatchingEngineIndex.create_brute_force_index(
                    display_name=self.index_name,
                    contents_delta_uri=contents_delta_uri,
                    description=description,
                    dimensions=dimensions,
                    distance_measure_type="DOT_PRODUCT_DISTANCE",
                    index_update_method="STREAM_UPDATE",
                )
                machine_type = "e2-standard-16"
            else:  # tree_ah
                logger.info(f"Creating TreeAH index (slower deployment, approximate search)")
                self.index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                    display_name=self.index_name,
                    contents_delta_uri=contents_delta_uri,
                    description=description,
                    dimensions=dimensions,
                    approximate_neighbors_count=10,
                    distance_measure_type="DOT_PRODUCT_DISTANCE",
                    leaf_node_embedding_count=500,
                    leaf_nodes_to_search_percent=7,
                    index_update_method="STREAM_UPDATE",
                )
                machine_type = "e2-standard-16"

            logger.info(f"✓ Vector Search index created: {self.index.resource_name}")

            # Create index endpoint
            self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=f"{self.index_name}-endpoint",
                description=f"Endpoint for {description}",
                public_endpoint_enabled=True
            )

            logger.info(f"✓ Index endpoint created: {self.index_endpoint.resource_name}")

            # Deploy index to endpoint
            logger.info(f"Deploying index with machine type: {machine_type}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.deployed_index_id = f"{self.index_name.replace('-', '_')}_{timestamp}"

            self.index_endpoint.deploy_index(
                index=self.index,
                deployed_index_id=self.deployed_index_id,
                display_name=f"{self.index_name}-deployed",
                machine_type=machine_type,
                min_replica_count=1,
                max_replica_count=1
            )

            logger.info("✓ Index deployed to endpoint")

            # Update instance variables
            self.vector_search_index = self.index.resource_name
            self.vector_search_endpoint = self.index_endpoint.resource_name

            # Update .env file with new resource names
            self._update_env_file(self.index.resource_name, self.index_endpoint.resource_name)

            return {
                "index_resource_name": self.index.resource_name,
                "endpoint_resource_name": self.index_endpoint.resource_name,
                "deployed_index_id": self.deployed_index_id,
                "status": "created",
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error creating Vector Search infrastructure: {str(e)}")
            raise

    def _update_env_file(self, index_resource_name: str, endpoint_resource_name: str):
        """Update .env file with Vector Search resource names."""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '.env')

            if not os.path.exists(env_path):
                logger.warning(f".env file not found at {env_path}")
                return

            # Read current .env content
            with open(env_path, 'r') as f:
                lines = f.readlines()

            # Update or add Vector Search variables
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
                lines.append(f'\n# Vector Search Backend (auto-generated)\n')
                lines.append(f'VECTOR_SEARCH_INDEX={index_resource_name}\n')

            if not endpoint_updated:
                lines.append(f'VECTOR_SEARCH_INDEX_ENDPOINT={endpoint_resource_name}\n')

            # Write updated content
            with open(env_path, 'w') as f:
                f.writelines(lines)

            logger.info(f"✓ Updated .env file with Vector Search resource names")

            # Update environment variables in current process
            os.environ['VECTOR_SEARCH_INDEX'] = index_resource_name
            os.environ['VECTOR_SEARCH_INDEX_ENDPOINT'] = endpoint_resource_name

        except Exception as e:
            logger.error(f"Error updating .env file: {str(e)}")

    async def import_documents(
        self,
        documents: List[Dict[str, Any]],
        bucket_name: Optional[str] = None,
        store_chunk_json: bool = True
    ) -> Dict[str, Any]:
        """Import documents into Vector Search.

        Args:
            documents: List of documents with 'content', 'metadata', and optional 'id'
            bucket_name: Optional GCS bucket for storing documents
            store_chunk_json: If True, store chunk JSON files in GCS (default: True)
                             Note: Always True for both regular uploads and GCS imports.
                             Chunk JSON is the PROCESSED OUTPUT (different from original file INPUT).

        Returns:
            Import operation details
        """
        if not self.index or not self.index_endpoint:
            raise ValueError("Vector Search infrastructure not created. Please create index and endpoint first.")

        try:
            logger.info(f"Importing {len(documents)} documents")

            # Generate embeddings for all documents
            contents = [doc['content'] for doc in documents]
            metadata_list = [doc.get('metadata', {}) for doc in documents]

            embeddings = self.embedding_handler.generate_batch_embeddings(
                contents,
                metadata_list
            )

            # Prepare datapoints for Vector Search
            datapoints = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")

                # Create metadata with temporal info
                metadata = doc.get('metadata', {})
                metadata['content_preview'] = doc['content'][:200]
                metadata['indexed_at'] = datetime.now().isoformat()

                # Store full document metadata
                self.document_metadata[doc_id] = {
                    'id': doc_id,
                    'content': doc['content'],
                    'metadata': metadata,
                    'source': metadata.get('source_url') or metadata.get('filename', 'Unknown'),
                    'title': metadata.get('title', metadata.get('filename', f'Document {i+1}'))
                }

                # Create datapoint for upsert
                vector = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

                datapoints.append({
                    "datapoint_id": doc_id,
                    "feature_vector": vector
                })

            # Store chunk JSON files in GCS (optional for GCS imports)
            if store_chunk_json:
                storage_bucket = bucket_name or self.gcs_bucket_name
                gcs_paths = self._store_documents_in_gcs(storage_bucket, documents, datapoints)

                # Update metadata with chunk JSON paths (separate from original file)
                for doc_id, gcs_path in gcs_paths.items():
                    if doc_id in self.document_metadata:
                        self.document_metadata[doc_id]['chunk_json_path'] = gcs_path
                        object_path = gcs_path.replace(f'gs://{storage_bucket}/', '')
                        self.document_metadata[doc_id]['chunk_json_url'] = f"https://storage.cloud.google.com/{storage_bucket}/{object_path}"

                logger.info(
                    "Stored chunk JSON files",
                    extra={'chunk_count': len(documents), 'bucket': storage_bucket}
                )
            else:
                logger.info(
                    "Skipping chunk JSON storage (store_chunk_json=False)",
                    extra={'chunk_count': len(documents)}
                )

            # Upsert datapoints to index
            logger.info(f"Upserting {len(datapoints)} datapoints to index...")
            from google.cloud.aiplatform_v1.services.index_service import IndexServiceClient
            from google.cloud.aiplatform_v1.types import UpsertDatapointsRequest, IndexDatapoint

            client = IndexServiceClient(client_options={"api_endpoint": f"{self.location}-aiplatform.googleapis.com"})

            # Build IndexDatapoint objects
            index_datapoints = []
            for dp in datapoints:
                datapoint = IndexDatapoint({
                    "datapoint_id": dp["datapoint_id"],
                    "feature_vector": dp["feature_vector"]
                })
                index_datapoints.append(datapoint)

            # Send upsert request
            request = UpsertDatapointsRequest(
                index=self.vector_search_index,
                datapoints=index_datapoints
            )

            response = client.upsert_datapoints(request=request)
            logger.info(f"✓ Successfully upserted {len(datapoints)} vectors to index!")

            # Save metadata to GCS for persistence
            self._save_metadata_to_gcs()

            return {
                "status": "imported",
                "document_count": len(documents),
                "imported_at": datetime.now().isoformat(),
                "datapoints_created": len(datapoints)
            }

        except Exception as e:
            logger.error(f"Error importing documents: {str(e)}")
            raise

    async def query(
        self,
        query_text: str,
        top_k: int = 20,
        temporal_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query Vector Search index with temporal filtering.

        Args:
            query_text: Query text
            top_k: Number of results to return
            temporal_filter: Optional temporal filtering criteria

        Returns:
            Query results with relevant documents and temporal context
        """
        if not self.index_endpoint or not self.deployed_index_id:
            raise ValueError("Vector Search endpoint not deployed. Please create and deploy index first.")

        try:
            logger.info(f"Querying Vector Search: {query_text}")

            # Generate query embedding with temporal context
            query_embedding = self.embedding_handler.generate_embedding(query_text, {})
            query_vector = query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding)

            # Query the index using find_neighbors
            logger.info(f"Searching for {top_k} nearest neighbors...")
            response = self.index_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_vector],
                num_neighbors=top_k
            )

            # Parse results
            results = []
            if response and len(response) > 0:
                neighbors = response[0]  # First query results
                logger.info(f"Found {len(neighbors)} neighbors")

                for neighbor in neighbors:
                    doc_id = neighbor.id
                    distance = neighbor.distance

                    # Get document metadata
                    doc_info = self.document_metadata.get(doc_id, {})
                    metadata = doc_info.get('metadata', {})

                    # Create result
                    result = {
                        "id": doc_id,
                        "score": distance,  # DOT_PRODUCT_DISTANCE (higher is better)
                        "title": doc_info.get('title', 'Unknown Document'),
                        "content": doc_info.get('content', ''),
                        "content_preview": doc_info.get('content', '')[:300] + '...' if len(doc_info.get('content', '')) > 300 else doc_info.get('content', ''),
                        "metadata": metadata,
                        "source_uri": doc_info.get('gcs_url', ''),
                        "citation": self._format_citation(doc_id, doc_info, score=distance)
                    }
                    results.append(result)

            # Sort by score descending (best match first)
            if results:
                results.sort(key=lambda x: x['score'], reverse=True)

            # Apply temporal filtering if provided
            temporal_filter_applied = False
            effective_filter = temporal_filter

            if temporal_filter and results:
                logger.info(f"Applying explicit temporal filter: {temporal_filter}")
                results = self._apply_temporal_filter(results, temporal_filter)
                temporal_filter_applied = True
            elif not temporal_filter and results:
                # Try to extract implicit filter from query text
                implicit_filter = self._extract_temporal_filter_from_query(query_text)
                if implicit_filter:
                    logger.info(f"Applying implicit temporal filter: {implicit_filter}")
                    results = self._apply_temporal_filter(results, implicit_filter)
                    effective_filter = implicit_filter
                    temporal_filter_applied = True

            # Re-sort by score after filtering
            if results:
                results.sort(key=lambda x: x['score'], reverse=True)

            # Detect temporal intent and sort by date if needed
            has_temporal_intent = self._detect_temporal_intent(query_text)
            if has_temporal_intent and results:
                logger.info(f"Temporal intent detected in query: '{query_text}'")
                logger.info("Sorting results by recency (most recent first)")
                results = self._sort_by_recency(results)

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
            logger.error(f"Error querying index: {str(e)}")
            raise

    def _detect_temporal_intent(self, query_text: str) -> bool:
        """Detect if query has temporal intent."""
        temporal_keywords = [
            'latest', 'most recent', 'newest', 'current', 'recent',
            'last', 'up to date', 'up-to-date', 'today', 'this year',
            'this quarter', 'this month'
        ]
        query_lower = query_text.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)

    def _extract_temporal_filter_from_query(self, query_text: str) -> Optional[Dict[str, Any]]:
        """Extract temporal filter criteria from query text with date normalization."""
        temporal_entities = self.embedding_handler.extract_temporal_info(query_text)

        if not temporal_entities:
            return None

        dates = [e['value'] for e in temporal_entities if e['type'] == 'date']
        years = [e['value'] for e in temporal_entities if e['type'] == 'year']

        filter_criteria = {}

        if dates:
            # Normalize the date to YYYY-MM-DD format for consistent filtering
            raw_date = dates[0]
            normalized_date = self.embedding_handler._normalize_date(raw_date)

            if normalized_date:
                filter_criteria['document_date'] = normalized_date
                logger.info(f"Extracted date filter: {raw_date} -> normalized: {normalized_date}")
            else:
                # If normalization fails, use raw date
                filter_criteria['document_date'] = raw_date
                logger.warning(f"Could not normalize date filter: {raw_date}, using as-is")
        elif years:
            year = max(years)
            filter_criteria['year'] = str(year)
            logger.info(f"Extracted year filter: {year}")

        return filter_criteria if filter_criteria else None

    def _apply_temporal_filter(self, results: List[Dict[str, Any]], temporal_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results based on temporal criteria."""
        if not temporal_filter or not results:
            return results

        filtered = []
        filter_type = None
        filter_value = None

        if 'document_date' in temporal_filter:
            filter_type = 'date'
            filter_value = temporal_filter['document_date']
        elif 'year' in temporal_filter:
            filter_type = 'year'
            filter_value = temporal_filter['year']

        if not filter_type:
            return results

        for result in results:
            metadata = result.get('metadata', {})
            doc_date = metadata.get('document_date', '')

            if filter_type == 'date':
                if doc_date.startswith(filter_value):
                    filtered.append(result)
            elif filter_type == 'year':
                if filter_value in doc_date:
                    filtered.append(result)

        logger.info(f"Temporal filter applied: {len(filtered)}/{len(results)} results matched")
        return filtered

    def _sort_by_recency(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort results by document date (most recent first)."""
        def get_date_key(result):
            metadata = result.get('metadata', {})
            doc_date = metadata.get('document_date')

            if doc_date:
                try:
                    from dateutil import parser
                    return parser.parse(doc_date)
                except:
                    pass

            uploaded_at = metadata.get('uploaded_at')
            if uploaded_at:
                try:
                    from dateutil import parser
                    return parser.parse(uploaded_at)
                except:
                    pass

            return datetime.min

        sorted_results = sorted(results, key=get_date_key, reverse=True)
        logger.info(f"Sorted {len(sorted_results)} results by recency")
        return sorted_results

    def _format_citation(
        self,
        doc_id: str,
        doc_info: Dict[str, Any],
        score: Optional[float] = None
    ) -> Dict[str, str]:
        """Format citation information for a document.

        Args:
            doc_id: Document identifier
            doc_info: Document information including metadata
            score: Optional relevance/similarity score from vector search

        Returns:
            Citation dictionary with formatted strings and clickable links
        """
        metadata = doc_info.get('metadata', {})

        citation = {
            "document_id": doc_id,
            "title": doc_info.get('title', 'Unknown Document'),
            "source": doc_info.get('source', 'Unknown'),
        }

        # Add relevance score if provided
        if score is not None:
            citation['score'] = round(score, 4)
            citation['relevance'] = round(score, 4)

        # Add page and chunk information from metadata
        if 'page_number' in metadata:
            citation['page_number'] = metadata['page_number']

        if 'chunk_index' in metadata:
            citation['chunk_index'] = metadata['chunk_index']

        if 'page_chunk_index' in metadata:
            citation['page_chunk_index'] = metadata['page_chunk_index']

        if 'quality_score' in metadata:
            citation['quality_score'] = metadata['quality_score']

        # URLs (prioritize original file URL over chunk URL)
        if 'original_file_url' in metadata:
            citation['original_file_url'] = metadata['original_file_url']
            citation['clickable_link'] = metadata['original_file_url']
        elif metadata.get('source_url'):
            citation['source_url'] = metadata['source_url']
            citation['clickable_link'] = metadata['source_url']
        elif 'gcs_url' in doc_info:
            citation['gcs_chunk_url'] = doc_info['gcs_url']
            citation['clickable_link'] = doc_info['gcs_url']

        # Document date
        if 'document_date' in metadata:
            citation['date'] = metadata['document_date']

        # Build enhanced formatted citation string
        citation_parts = []

        # Title with page and chunk location
        title_part = citation['title']
        location_info = []

        if citation.get('page_number') is not None:
            location_info.append(f"Page {citation['page_number']}")

        if citation.get('page_chunk_index') is not None:
            location_info.append(f"Chunk {citation['page_chunk_index']}")
        elif citation.get('chunk_index') is not None:
            location_info.append(f"Chunk {citation['chunk_index']}")

        if location_info:
            title_part += f" ({', '.join(location_info)})"

        citation_parts.append(title_part)

        # Add document date if available
        if citation.get('date'):
            citation_parts.append(f"Date: {citation['date']}")

        # Add relevance score if available
        if citation.get('score') is not None:
            citation_parts.append(f"Relevance: {citation['score']}")

        # Add source filename if not Unknown
        if citation.get('source') != 'Unknown':
            citation_parts.append(f"Source: {citation['source']}")

        # Main formatted string (pipe-separated for readability)
        citation['formatted'] = ' | '.join(citation_parts)

        # Formatted version with clickable link
        if citation.get('clickable_link'):
            citation['formatted_with_link'] = citation['formatted'] + f"\nView Document: {citation['clickable_link']}"
        else:
            citation['formatted_with_link'] = citation['formatted']

        # Log citation generation with key details
        logger.debug(
            "Generated citation",
            extra={
                'document_id': doc_id,
                'has_score': score is not None,
                'has_page_number': 'page_number' in citation,
                'has_chunk_info': 'chunk_index' in citation or 'page_chunk_index' in citation,
                'has_clickable_link': 'clickable_link' in citation,
                'formatted_length': len(citation['formatted'])
            }
        )

        return citation

    def _ensure_bucket_exists(self):
        """Ensure the GCS bucket exists."""
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

    def store_original_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """Store original uploaded file in GCS."""
        try:
            bucket = self.storage_client.bucket(bucket_name or self.gcs_bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            blob_name = f"vector_search/{self.index_name}/original_files/{timestamp}_{filename}"
            blob = bucket.blob(blob_name)

            blob.upload_from_string(
                file_content,
                content_type=content_type
            )

            authenticated_url = f"https://storage.cloud.google.com/{bucket.name}/{blob_name}"
            logger.info(f"Stored original file: {authenticated_url}")
            return authenticated_url

        except Exception as e:
            logger.error(f"Error storing original file: {str(e)}")
            raise

    def list_gcs_files(self, gcs_path: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """List files from a GCS path (supports folders).

        Args:
            gcs_path: GCS path (gs://bucket/path/to/folder/ or gs://bucket/path/file.pdf)
            recursive: If True, recursively list all files in subfolders

        Returns:
            List of file information dictionaries
        """
        try:
            # Parse GCS path
            if not gcs_path.startswith('gs://'):
                raise ValueError(f"Invalid GCS path: {gcs_path}. Must start with 'gs://'")

            path_parts = gcs_path[5:].split('/', 1)
            bucket_name = path_parts[0]
            prefix = path_parts[1] if len(path_parts) > 1 else ''

            logger.info(
                "Listing GCS files",
                extra={
                    'bucket': bucket_name,
                    'prefix': prefix,
                    'recursive': recursive
                }
            )

            bucket = self.storage_client.bucket(bucket_name)

            # List blobs with prefix
            if recursive:
                # Get all blobs under prefix (including subfolders)
                blobs = bucket.list_blobs(prefix=prefix)
            else:
                # Get only blobs directly under prefix (no subfolders)
                blobs = bucket.list_blobs(prefix=prefix, delimiter='/')

            files = []
            for blob in blobs:
                # Skip directories (blobs ending with /)
                if blob.name.endswith('/'):
                    continue

                # Get file extension
                filename = blob.name.split('/')[-1]
                file_ext = filename.split('.')[-1].lower() if '.' in filename else ''

                # Only include supported file types
                supported_extensions = ['pdf', 'docx', 'txt', 'md', 'markdown']
                if file_ext not in supported_extensions:
                    logger.debug(
                        "Skipping unsupported file type",
                        extra={'document_filename': filename, 'extension': file_ext}
                    )
                    continue

                file_info = {
                    'gcs_path': f"gs://{bucket_name}/{blob.name}",
                    'bucket': bucket_name,
                    'blob_name': blob.name,
                    'filename': filename,
                    'size_bytes': blob.size,
                    'content_type': blob.content_type,
                    'updated': blob.updated.isoformat() if blob.updated else None,
                    'public_url': f"https://storage.cloud.google.com/{bucket_name}/{blob.name}"
                }
                files.append(file_info)

            logger.info(
                "Found GCS files",
                extra={
                    'total_files': len(files),
                    'bucket': bucket_name,
                    'prefix': prefix
                }
            )

            return files

        except Exception as e:
            logger.error(
                "Error listing GCS files",
                exc_info=True,
                extra={'gcs_path': gcs_path}
            )
            raise

    def download_gcs_file(self, gcs_path: str) -> bytes:
        """Download file content from GCS.

        Args:
            gcs_path: Full GCS path (gs://bucket/path/to/file.pdf)

        Returns:
            File content as bytes
        """
        try:
            # Parse GCS path
            if not gcs_path.startswith('gs://'):
                raise ValueError(f"Invalid GCS path: {gcs_path}")

            path_parts = gcs_path[5:].split('/', 1)
            bucket_name = path_parts[0]
            blob_name = path_parts[1]

            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            if not blob.exists():
                raise ValueError(f"File not found: {gcs_path}")

            logger.info(
                "Downloading GCS file",
                extra={
                    'gcs_path': gcs_path,
                    'size_bytes': blob.size
                }
            )

            content = blob.download_as_bytes()

            logger.info(
                "Downloaded GCS file",
                extra={
                    'gcs_path': gcs_path,
                    'content_length': len(content)
                }
            )

            return content

        except Exception as e:
            logger.error(
                "Error downloading GCS file",
                exc_info=True,
                extra={'gcs_path': gcs_path}
            )
            raise

    async def import_from_gcs(
        self,
        gcs_path: str,
        document_date: Optional[str] = None,
        recursive: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> Dict[str, Any]:
        """Import documents from GCS path (file or folder).

        Args:
            gcs_path: GCS path (gs://bucket/path/to/folder/ or gs://bucket/file.pdf)
            document_date: Optional document date for all files
            recursive: If True and path is folder, import all files recursively
            chunk_size: Size of each text chunk in characters (default: 1000)
            chunk_overlap: Overlap between consecutive chunks in characters (default: 200)

        Returns:
            Import results with file counts and status
        """
        try:
            logger.info(
                "Starting GCS import",
                extra={
                    'gcs_path': gcs_path,
                    'document_date': document_date,
                    'recursive': recursive,
                    'chunk_size': chunk_size,
                    'chunk_overlap': chunk_overlap
                }
            )

            # List files from GCS path
            files = self.list_gcs_files(gcs_path, recursive=recursive)

            if not files:
                return {
                    'success': False,
                    'message': 'No supported files found at GCS path',
                    'files_found': 0
                }

            # Import each file
            from document_parser import DocumentParser
            from text_chunker import TextChunker

            # Initialize chunker with custom parameters
            logger.info(f"Using chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
            chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            imported_files = []
            failed_files = []

            for file_info in files:
                try:
                    logger.info(
                        "Processing GCS file",
                        extra={
                            'document_filename': file_info['filename'],
                            'gcs_path': file_info['gcs_path']
                        }
                    )

                    # Download file content
                    file_bytes = self.download_gcs_file(file_info['gcs_path'])

                    # Parse document
                    parsed = DocumentParser.parse_document(
                        file_bytes,
                        file_info['filename'],
                        file_info.get('content_type')
                    )

                    # Create base metadata BEFORE chunking
                    base_metadata = {
                        'filename': file_info['filename'],
                        'source': file_info['filename'],
                        'title': file_info['filename'].rsplit('.', 1)[0],
                        'original_file_url': file_info['public_url'],
                        'source_url': file_info['public_url'],
                        'gcs_source_path': file_info['gcs_path'],
                        'imported_from_gcs': True,
                        'uploaded_at': datetime.now().isoformat()
                    }

                    # Create document ID
                    document_id = f"{file_info['filename'].replace('.', '_').replace(' ', '_')}_{int(datetime.now().timestamp())}"

                    # Chunk the document
                    if parsed['type'] == 'pdf':
                        # Use parse_pdf_by_pages for PDFs
                        pdf_result = DocumentParser.parse_pdf_by_pages(file_bytes)

                        # Add PDF-specific metadata
                        base_metadata.update({
                            'document_type': 'pdf',
                            'total_pages': pdf_result['total_pages'],
                            'non_empty_pages': pdf_result.get('non_empty_pages', pdf_result['total_pages']),
                            'has_tables': pdf_result.get('has_tables', False),
                            'total_tables': pdf_result.get('total_tables', 0)
                        })

                        # Chunk with proper parameters
                        chunks = chunker.chunk_pdf_by_pages(
                            page_texts=pdf_result['page_texts'],
                            metadata=base_metadata,
                            document_id=document_id
                        )
                    else:
                        # Add non-PDF metadata
                        base_metadata.update({
                            'document_type': parsed['type']
                        })

                        # Chunk with proper parameters
                        chunks = chunker.chunk_text(
                            text=parsed['text'],
                            metadata=base_metadata,
                            document_id=document_id
                        )

                    # Determine document date ONCE for all chunks (user-provided takes priority)
                    final_document_date = document_date

                    # If not provided, extract from filename
                    if not final_document_date:
                        extracted_date = self.embedding_handler.extract_date_from_filename(file_info['filename'])
                        if extracted_date:
                            final_document_date = extracted_date
                            logger.info(
                                "Extracted date from filename",
                                extra={
                                    'document_filename': file_info['filename'],
                                    'extracted_date': extracted_date
                                }
                            )

                    # Prepare documents for import
                    documents = []
                    for chunk in chunks:
                        # Get chunk metadata (already includes base_metadata from chunking)
                        metadata = chunk.get('metadata', {})

                        # Add document_date if we have one
                        if final_document_date:
                            metadata['document_date'] = final_document_date

                        # Create document with chunk ID and content
                        doc = {
                            'id': chunk.get('id', f"{document_id}_chunk{len(documents)}"),
                            'content': chunk['content'],
                            'metadata': metadata
                        }
                        documents.append(doc)

                    # Import documents (chunk JSON storage needed - different from original file!)
                    import_result = await self.import_documents(
                        documents=documents,
                        bucket_name=None,
                        store_chunk_json=True  # Store chunk JSON (processed output)
                    )

                    imported_files.append({
                        'filename': file_info['filename'],
                        'gcs_path': file_info['gcs_path'],
                        'chunks_created': len(documents),
                        'status': 'success'
                    })

                    logger.info(
                        "Imported GCS file",
                        extra={
                            'document_filename': file_info['filename'],
                            'chunks_created': len(documents)
                        }
                    )

                except Exception as e:
                    failed_files.append({
                        'filename': file_info['filename'],
                        'gcs_path': file_info['gcs_path'],
                        'error': str(e),
                        'status': 'failed'
                    })

                    logger.error(
                        "Failed to import GCS file",
                        exc_info=True,
                        extra={'document_filename': file_info['filename']}
                    )

            return {
                'success': len(imported_files) > 0,
                'message': f"Imported {len(imported_files)} of {len(files)} files from GCS",
                'files_found': len(files),
                'files_imported': len(imported_files),
                'files_failed': len(failed_files),
                'imported_files': imported_files,
                'failed_files': failed_files,
                'imported_at': datetime.now().isoformat(),
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap
            }

        except Exception as e:
            logger.error(
                "Error in GCS import",
                exc_info=True,
                extra={'gcs_path': gcs_path}
            )
            raise

    def _store_documents_in_gcs(
        self,
        bucket_name: str,
        documents: List[Dict[str, Any]],
        datapoints: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Store documents in GCS."""
        gcs_paths = {}
        try:
            bucket = self.storage_client.bucket(bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Store individual documents
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{timestamp}")
                doc_blob_name = f"vector_search/{self.index_name}/documents/{doc_id}.json"
                doc_blob = bucket.blob(doc_blob_name)

                doc_blob.upload_from_string(
                    json.dumps(doc, indent=2),
                    content_type='application/json'
                )

                gcs_paths[doc_id] = f"gs://{bucket_name}/{doc_blob_name}"

            # Store batch for backup
            batch_blob_name = f"vector_search/{self.index_name}/batches/documents_{timestamp}.json"
            batch_blob = bucket.blob(batch_blob_name)

            batch_blob.upload_from_string(
                json.dumps(documents, indent=2),
                content_type='application/json'
            )

            logger.info(f"Stored {len(documents)} documents in GCS")
            return gcs_paths

        except Exception as e:
            logger.error(f"Error storing in GCS: {str(e)}")
            raise

    def _save_metadata_to_gcs(self):
        """Save document metadata to GCS for persistence."""
        try:
            metadata_path = f"vector_search/{self.index_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(metadata_path)

            metadata_json = json.dumps(self.document_metadata, indent=2)
            blob.upload_from_string(metadata_json, content_type='application/json')

            logger.info(f"✓ Saved metadata for {len(self.document_metadata)} documents to GCS")
        except Exception as e:
            logger.warning(f"Could not save metadata to GCS: {str(e)}")

    def _load_metadata_from_gcs(self):
        """Load document metadata from GCS."""
        try:
            metadata_path = f"vector_search/{self.index_name}/metadata/document_metadata.json"
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(metadata_path)

            if blob.exists():
                metadata_json = blob.download_as_text()
                self.document_metadata = json.loads(metadata_json)
                logger.info(f"✓ Loaded metadata for {len(self.document_metadata)} documents from GCS")
        except Exception as e:
            if "404" not in str(e):
                logger.warning(f"Could not load metadata from GCS: {str(e)}")

    def _clear_all_gcs_files(self):
        """Clear all GCS files and folders associated with this index."""
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)

            # List of prefixes to delete
            prefixes_to_clear = [
                f"vector_search/{self.index_name}/documents/",      # Document JSON files
                f"vector_search/{self.index_name}/batches/",         # Batch files
                f"vector_search/{self.index_name}/original_files/",  # Original uploaded files
                f"vector_search/{self.index_name}/metadata/",        # Metadata files
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

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        doc_info = self.document_metadata.get(document_id)
        if doc_info:
            return {
                **doc_info,
                "citation": self._format_citation(document_id, doc_info)
            }
        return None

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
            self._save_metadata_to_gcs()

            # Clear all GCS files
            self._clear_all_gcs_files()

            logger.info(f"Successfully cleared {total_removed} datapoints from index and all GCS files")

            return {
                "success": True,
                "message": f"Cleared {total_removed} datapoints from index and all associated files from GCS",
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

    async def get_index_info(self) -> Dict[str, Any]:
        """Get information about the Vector Search index and endpoint."""
        index_available = self.index is not None
        endpoint_available = self.index_endpoint is not None

        info = {
            "project_id": self.project_id,
            "location": self.location,
            "index_available": index_available,
            "endpoint_available": endpoint_available,
            "status": "created" if (index_available and endpoint_available) else "not_created",
            "message": "Index is active and ready to use" if (index_available and endpoint_available) else "Index has not been created yet."
        }

        if index_available:
            info["index_id"] = self.vector_search_index
            info["index_display_name"] = self.index.display_name

        if endpoint_available:
            info["endpoint_id"] = self.vector_search_endpoint
            info["endpoint_display_name"] = self.index_endpoint.display_name
            if self.deployed_index_id:
                info["deployed_index_id"] = self.deployed_index_id

        return info

    async def delete_index_infrastructure(self) -> Dict[str, Any]:
        """Delete Vector Search index and endpoint."""
        try:
            logger.info("Deleting Vector Search infrastructure...")

            deleted_resources = []

            if not self.index and not self.index_endpoint:
                return {
                    "status": "nothing_to_delete",
                    "message": "No Vector Search infrastructure to delete"
                }

            # Undeploy and delete endpoint
            if self.index_endpoint:
                try:
                    if self.index_endpoint.deployed_indexes:
                        for deployed_index in self.index_endpoint.deployed_indexes:
                            logger.info(f"Undeploying index: {deployed_index.id}")
                            self.index_endpoint.undeploy_index(deployed_index_id=deployed_index.id)
                            deleted_resources.append(f"Undeployed index: {deployed_index.id}")

                    logger.info(f"Deleting endpoint...")
                    self.index_endpoint.delete(force=True)
                    deleted_resources.append(f"Deleted endpoint: {self.index_endpoint.display_name}")
                except Exception as e:
                    logger.error(f"Error deleting endpoint: {str(e)}")
                    raise

            # Delete index
            if self.index:
                try:
                    logger.info(f"Deleting index...")
                    self.index.delete()
                    deleted_resources.append(f"Deleted index: {self.index.display_name}")
                except Exception as e:
                    logger.error(f"Error deleting index: {str(e)}")
                    raise

            logger.info("✓ Vector Search infrastructure deletion completed")

            # Clear all GCS files
            self._clear_all_gcs_files()
            deleted_resources.append("Cleared all GCS files")

            # Clear metadata
            self.document_metadata = {}

            # Clear references
            self.index = None
            self.index_endpoint = None
            self.deployed_index_id = None
            self.vector_search_index = None
            self.vector_search_endpoint = None

            return {
                "status": "deleted",
                "deleted_resources": deleted_resources,
                "deleted_at": datetime.now().isoformat(),
                "message": "Vector Search infrastructure and all associated files deleted successfully"
            }

        except Exception as e:
            logger.error(f"Error deleting infrastructure: {str(e)}")
            raise
