"""
Temporal Context Embedding Handler

This module handles the creation of embeddings that incorporate temporal context.
It extracts date information from documents and enhances the embedding process
to maintain temporal awareness.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import re
import asyncio
import time
import logging
from google import genai

logger = logging.getLogger(__name__)


class TemporalEmbeddingHandler:
    """Handles embedding generation with temporal context awareness."""

    def __init__(self, project_id: str, location: str, model_name: str = "text-embedding-005",
                 requests_per_minute: int = 60):
        """Initialize the temporal embedding handler.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            model_name: Vertex AI embedding model name (default: text-embedding-005)
            requests_per_minute: Rate limit for API calls (default: 60)
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.requests_per_minute = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute  # Minimum delay between requests
        self.last_request_time = 0

        logger.info(f"TemporalEmbeddingHandler initialized:")
        logger.info(f"  - Model: {model_name}")
        logger.info(f"  - Rate limit: {requests_per_minute} requests/minute ({self.min_delay:.2f}s between requests)")

        # Initialize google-genai client with Vertex AI
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

    def extract_temporal_info(self, text: str) -> List[Dict[str, Any]]:
        """Extract temporal information from text.

        Args:
            text: Input text to analyze

        Returns:
            List of temporal entities found in the text
        """
        temporal_entities = []

        # Pattern for various date formats
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{2}/\d{2}/\d{4}\b',  # MM/DD/YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
        ]

        # Year patterns
        year_pattern = r'\b(19|20)\d{2}\b'

        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                temporal_entities.append({
                    'type': 'date',
                    'value': match.group(),
                    'position': match.span()
                })

        # Find years
        year_matches = re.finditer(year_pattern, text)
        for match in year_matches:
            temporal_entities.append({
                'type': 'year',
                'value': match.group(),
                'position': match.span()
            })

        return temporal_entities

    def enhance_text_with_temporal_context(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enhance text with temporal context markers.

        Args:
            text: Original text
            metadata: Optional metadata containing temporal information

        Returns:
            Enhanced text with temporal context
        """
        # Extract temporal info from text
        temporal_entities = self.extract_temporal_info(text)

        # Build temporal context prefix
        temporal_context = []

        if metadata and 'document_date' in metadata:
            temporal_context.append(f"Document Date: {metadata['document_date']}")

        if metadata and 'created_at' in metadata:
            temporal_context.append(f"Created: {metadata['created_at']}")

        if temporal_entities:
            dates = [e['value'] for e in temporal_entities if e['type'] == 'date']
            years = [e['value'] for e in temporal_entities if e['type'] == 'year']

            if dates:
                temporal_context.append(f"Contains dates: {', '.join(set(dates[:3]))}")
            if years:
                temporal_context.append(f"Relevant years: {', '.join(set(years[:3]))}")

        # Combine context with original text
        if temporal_context:
            prefix = "[TEMPORAL_CONTEXT: " + " | ".join(temporal_context) + "] "
            return prefix + text

        return text

    def _rate_limit(self):
        """Apply rate limiting by waiting if necessary."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_delay:
            sleep_time = self.min_delay - time_since_last_request
            logger.info(f"Rate limiting: waiting {sleep_time:.2f}s before next embedding request")
            time.sleep(sleep_time)
        elif self.last_request_time > 0:
            logger.debug(f"No rate limit needed, {time_since_last_request:.2f}s since last request")

        self.last_request_time = time.time()

    def _call_embed_api_with_retry(self, contents: List[str], max_retries: int = 3) -> Any:
        """Call the embedding API with retry logic for quota errors.

        Args:
            contents: List of texts to embed
            max_retries: Maximum number of retry attempts

        Returns:
            API response
        """
        for attempt in range(max_retries):
            try:
                # Apply rate limiting before each request
                self._rate_limit()

                # Call the API
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=contents
                )
                return response

            except Exception as e:
                error_msg = str(e).lower()

                # Check if it's a quota error
                if 'quota' in error_msg or 'rate limit' in error_msg or '429' in error_msg:
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2^attempt seconds
                        wait_time = 2 ** attempt
                        logger.warning(f"Quota exceeded, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries reached for quota error: {e}")
                        raise
                else:
                    # Non-quota error, raise immediately
                    logger.error(f"API error: {e}")
                    raise

    def generate_embedding(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate embedding with temporal context.

        Args:
            text: Text to embed
            metadata: Optional metadata with temporal information

        Returns:
            Embedding vector
        """
        # Enhance text with temporal context
        enhanced_text = self.enhance_text_with_temporal_context(text, metadata)

        # Generate embedding using rate-limited API call
        response = self._call_embed_api_with_retry(contents=[enhanced_text])

        # Extract embedding values from response
        return response.embeddings[0].values

    def generate_batch_embeddings(
        self,
        texts: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with temporal context.

        Args:
            texts: List of texts to embed
            metadata_list: Optional list of metadata dicts

        Returns:
            List of embedding vectors
        """
        if metadata_list is None:
            metadata_list = [None] * len(texts)

        # Enhance all texts
        enhanced_texts = [
            self.enhance_text_with_temporal_context(text, metadata)
            for text, metadata in zip(texts, metadata_list)
        ]

        # Generate embeddings in batches (API limit is typically 5-250)
        batch_size = 5
        all_embeddings = []

        logger.info(f"Generating embeddings for {len(enhanced_texts)} texts in batches of {batch_size}")

        for i in range(0, len(enhanced_texts), batch_size):
            batch = enhanced_texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(enhanced_texts) + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")

            # Generate embeddings using rate-limited API call
            response = self._call_embed_api_with_retry(contents=batch)

            # Extract embedding values from response
            all_embeddings.extend([emb.values for emb in response.embeddings])

        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings
