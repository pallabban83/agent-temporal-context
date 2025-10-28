"""Text chunking utilities for RAG document processing."""

import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class TextChunker:
    """Split documents into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None
    ):
        """Initialize the text chunker.

        Args:
            chunk_size: Maximum number of characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: List of separators to split on (in order of preference)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n\n",  # Multiple newlines (section breaks)
            "\n\n",    # Double newlines (paragraph breaks)
            "\n",      # Single newlines
            ". ",      # Sentence endings
            "! ",
            "? ",
            "; ",
            ", ",
            " ",       # Word boundaries
            ""         # Character-level split (last resort)
        ]

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata.

        Args:
            text: Text to chunk
            metadata: Document metadata to attach to each chunk
            document_id: Document ID for chunk naming

        Returns:
            List of chunks with metadata
        """
        if not text.strip():
            return []

        metadata = metadata or {}
        chunks = []

        # Split text into chunks
        text_chunks = self._split_text(text)

        logger.info(f"Split document into {len(text_chunks)} chunks (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})")

        # Create chunk objects with metadata
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                'content': chunk_text,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(text_chunks),
                    'chunk_size': len(chunk_text),
                    'is_first_chunk': i == 0,
                    'is_last_chunk': i == len(text_chunks) - 1,
                },
                'id': f"{document_id}_chunk_{i}" if document_id else f"chunk_{i}"
            }
            chunks.append(chunk)

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks using hierarchical separators.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        # Try to split using separators in order
        chunks = [text]

        for separator in self.separators:
            new_chunks = []

            for chunk in chunks:
                if len(chunk) <= self.chunk_size:
                    new_chunks.append(chunk)
                else:
                    # Split this chunk further
                    split_chunks = self._split_by_separator(chunk, separator)
                    new_chunks.extend(split_chunks)

            chunks = new_chunks

            # If all chunks are small enough, we're done
            if all(len(c) <= self.chunk_size for c in chunks):
                break

        # Merge small chunks and handle overlaps
        final_chunks = self._merge_and_overlap(chunks)

        return final_chunks

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """Split text by a separator while respecting chunk size.

        Args:
            text: Text to split
            separator: Separator to split on

        Returns:
            List of text chunks
        """
        if not separator:
            # Character-level split as last resort
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        # Split by separator
        parts = text.split(separator)
        chunks = []
        current_chunk = ""

        for part in parts:
            # If adding this part would exceed chunk size
            if len(current_chunk) + len(part) + len(separator) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = part
                else:
                    # Part itself is too large, add it anyway
                    chunks.append(part)
            else:
                if current_chunk:
                    current_chunk += separator + part
                else:
                    current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _merge_and_overlap(self, chunks: List[str]) -> List[str]:
        """Merge very small chunks and add overlap between chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of merged chunks with overlap
        """
        if not chunks:
            return []

        final_chunks = []
        current_chunk = chunks[0]

        for next_chunk in chunks[1:]:
            # If current chunk is too small, merge with next
            if len(current_chunk) < self.chunk_size // 2:
                current_chunk = current_chunk + " " + next_chunk
            else:
                # Add current chunk and start new one with overlap
                final_chunks.append(current_chunk.strip())

                # Add overlap from end of current chunk
                if self.chunk_overlap > 0 and len(current_chunk) > self.chunk_overlap:
                    overlap = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap + " " + next_chunk
                else:
                    current_chunk = next_chunk

        # Add the last chunk
        if current_chunk.strip():
            final_chunks.append(current_chunk.strip())

        return final_chunks

    def chunk_pdf_by_pages(
        self,
        page_texts: List[str],
        metadata: Dict[str, Any] = None,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """Chunk PDF content while preserving page boundaries.

        Args:
            page_texts: List of text from each page
            metadata: Document metadata
            document_id: Document ID

        Returns:
            List of chunks with page information
        """
        all_chunks = []
        chunk_index = 0

        for page_num, page_text in enumerate(page_texts):
            if not page_text.strip():
                continue

            # Split page into chunks if needed
            page_chunks = self._split_text(page_text)

            for i, chunk_text in enumerate(page_chunks):
                chunk = {
                    'content': chunk_text,
                    'metadata': {
                        **(metadata or {}),
                        'page_number': page_num + 1,  # 1-indexed
                        'chunk_index': chunk_index,
                        'chunk_size': len(chunk_text),
                        'page_chunk_index': i,
                        'chunks_in_page': len(page_chunks),
                    },
                    'id': f"{document_id}_page{page_num+1}_chunk{i}" if document_id else f"page{page_num+1}_chunk{i}"
                }
                all_chunks.append(chunk)
                chunk_index += 1

        # Update total_chunks in metadata
        for chunk in all_chunks:
            chunk['metadata']['total_chunks'] = len(all_chunks)

        logger.info(f"Created {len(all_chunks)} chunks from {len(page_texts)} pages")

        return all_chunks

    def chunk_multimodal_pdf(
        self,
        pages_data: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """Chunk PDF content with images.

        Args:
            pages_data: List of page data with text and images
            metadata: Document metadata
            document_id: Document ID

        Returns:
            List of chunks with image information
        """
        all_chunks = []
        chunk_index = 0

        for page_data in pages_data:
            page_num = page_data['page_number']
            page_text = page_data['text']
            page_images = page_data.get('images', [])

            # Build enhanced text with image descriptions
            text_parts = []

            # Add image descriptions at the beginning of page text
            if page_images:
                image_descriptions = []
                for img in page_images:
                    img_desc = f"[IMAGE {img['image_num'] + 1}: {img['description']}"
                    if img['has_text']:
                        img_desc += f" | OCR: {img['ocr_text'][:200]}"
                    img_desc += "]"
                    image_descriptions.append(img_desc)

                text_parts.append("\n".join(image_descriptions))

            # Add page text
            text_parts.append(page_text)

            # Combine text with image context
            enhanced_text = "\n\n".join(text_parts)

            # Split page into chunks if needed
            page_chunks = self._split_text(enhanced_text)

            for i, chunk_text in enumerate(page_chunks):
                chunk = {
                    'content': chunk_text,
                    'metadata': {
                        **(metadata or {}),
                        'page_number': page_num,
                        'chunk_index': chunk_index,
                        'chunk_size': len(chunk_text),
                        'page_chunk_index': i,
                        'chunks_in_page': len(page_chunks),
                        'has_images': len(page_images) > 0,
                        'image_count': len(page_images),
                    },
                    'images': [{'url': img['url'], 'description': img['description']} for img in page_images],
                    'id': f"{document_id}_page{page_num}_chunk{i}" if document_id else f"page{page_num}_chunk{i}"
                }
                all_chunks.append(chunk)
                chunk_index += 1

        # Update total_chunks in metadata
        for chunk in all_chunks:
            chunk['metadata']['total_chunks'] = len(all_chunks)

        logger.info(f"Created {len(all_chunks)} multimodal chunks from {len(pages_data)} pages")

        return all_chunks
