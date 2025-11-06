"""Text chunking utilities for RAG document processing."""

from typing import List, Dict, Any, Tuple
import re
from logging_config import get_logger

logger = get_logger(__name__)


class TextChunker:
    """Split documents into chunks for embedding with semantic awareness."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
        respect_structure: bool = True
    ):
        """Initialize the text chunker.

        Args:
            chunk_size: Maximum number of characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            separators: List of separators to split on (in order of preference)
            respect_structure: Whether to respect markdown/structural boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.respect_structure = respect_structure
        self.separators = separators or [
            "\n## ",      # Markdown H2 headers
            "\n### ",     # Markdown H3 headers
            "\n#### ",    # Markdown H4 headers
            "\n\n\n",     # Multiple newlines (section breaks)
            "\n\n",       # Double newlines (paragraph breaks)
            "\n- ",       # List items
            "\n* ",       # List items
            "\n",         # Single newlines
            ". ",         # Sentence endings
            "! ",
            "? ",
            "; ",
            ", ",
            " ",          # Word boundaries
            ""            # Character-level split (last resort)
        ]

    def _extract_table_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Extract table blocks from text with their positions.

        Args:
            text: Text containing tables

        Returns:
            List of table block dictionaries with start, end, and content
        """
        import re
        table_blocks = []

        # Find all [TABLE N] ... [END TABLE] blocks
        pattern = r'\[TABLE\s+\d+\](.*?)\[END TABLE\]'

        for match in re.finditer(pattern, text, re.DOTALL):
            table_content = match.group(0)
            table_text = match.group(1).strip()

            # Skip empty or malformed tables
            if not table_text or len(table_text) < 5:
                logger.warning(f"Skipping empty or malformed table at position {match.start()}")
                continue

            table_size = len(table_content)

            # Log warning for very large tables
            if table_size > self.chunk_size * 2:
                logger.warning(f"Large table detected ({table_size} chars, exceeds chunk_size {self.chunk_size} by {table_size - self.chunk_size} chars)")

            table_blocks.append({
                'start': match.start(),
                'end': match.end(),
                'content': table_content,
                'table_text': table_text,
                'size': table_size
            })

        if table_blocks:
            logger.info(f"Extracted {len(table_blocks)} table block(s) from text")

        return table_blocks

    def _is_inside_table(self, position: int, table_blocks: List[Dict[str, Any]]) -> bool:
        """Check if a position is inside any table block.

        Args:
            position: Character position in text
            table_blocks: List of table block dictionaries

        Returns:
            True if position is inside a table
        """
        for table in table_blocks:
            if table['start'] <= position <= table['end']:
                return True
        return False

    def chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata and table awareness.

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

        # Extract table positions for awareness during chunking
        table_blocks = self._extract_table_blocks(text)

        # Split text into chunks (table-aware)
        text_chunks = self._split_text_table_aware(text, table_blocks)

        logger.info(f"Split document into {len(text_chunks)} chunks (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})")

        # Create chunk objects with metadata and quality scores
        for i, chunk_text in enumerate(text_chunks):
            quality = self._get_chunk_quality_score(chunk_text)

            chunk = {
                'content': chunk_text,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(text_chunks),
                    'chunk_size': len(chunk_text),
                    'is_first_chunk': i == 0,
                    'is_last_chunk': i == len(text_chunks) - 1,
                    'quality_score': quality['quality_score'],
                    'sentence_count': quality['sentence_count'],
                    'word_count': quality['word_count'],
                    'has_table': quality['has_table'],
                    'table_count': quality['table_count'],
                },
                'id': f"{document_id}_chunk_{i}" if document_id else f"chunk_{i}"
            }
            chunks.append(chunk)

        # Log quality statistics
        if chunks:
            avg_quality = sum(c['metadata']['quality_score'] for c in chunks) / len(chunks)
            logger.info(f"Average chunk quality score: {avg_quality:.2f}")

        return chunks

    def _split_text_table_aware(self, text: str, table_blocks: List[Dict[str, Any]]) -> List[str]:
        """Split text into chunks while protecting table boundaries.

        Args:
            text: Text to split
            table_blocks: List of table block dictionaries

        Returns:
            List of text chunks with intact tables
        """
        if not table_blocks:
            # No tables, use standard splitting
            return self._split_text(text)

        # Split text into segments: [text, table, text, table, ...]
        segments = []
        last_pos = 0

        for table in table_blocks:
            # Add text before table (if non-empty after strip)
            text_before = text[last_pos:table['start']]
            if text_before.strip():  # Only add if there's actual content
                segments.append({
                    'type': 'text',
                    'content': text_before,
                    'is_table': False
                })
            elif text_before:  # Has whitespace - preserve minimal spacing
                # Keep some whitespace between segments (max 2 newlines)
                whitespace = text_before[-min(len(text_before), 2):]
                if segments:  # Add to previous segment if exists
                    segments[-1]['content'] += whitespace

            # Add table as atomic segment
            segments.append({
                'type': 'table',
                'content': table['content'],
                'is_table': True,
                'size': table['size']
            })

            last_pos = table['end']

        # Add remaining text after last table
        text_after = text[last_pos:]
        if text_after.strip():
            segments.append({
                'type': 'text',
                'content': text_after,
                'is_table': False
            })

        # Now chunk each text segment normally, but keep tables intact
        chunked_segments = []
        for segment in segments:
            if segment['is_table']:
                # Tables are atomic - don't split them
                chunked_segments.append(segment['content'])
            else:
                # Split text normally
                if segment['content'].strip():
                    text_chunks = self._split_text(segment['content'])
                    chunked_segments.extend(text_chunks)

        # Merge segments respecting table boundaries
        final_chunks = self._merge_with_table_awareness(chunked_segments)

        return final_chunks

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

    def _merge_with_table_awareness(self, chunks: List[str]) -> List[str]:
        """Merge chunks while respecting table boundaries and size limits.

        Args:
            chunks: List of text chunks (may include tables)

        Returns:
            List of merged chunks with table-aware overlap
        """
        if not chunks:
            return []

        final_chunks = []
        current_chunk = chunks[0]
        current_has_table = '[TABLE' in current_chunk
        current_is_oversized = len(current_chunk) > self.chunk_size * 2

        for next_chunk in chunks[1:]:
            next_has_table = '[TABLE' in next_chunk
            next_is_oversized = len(next_chunk) > self.chunk_size * 2
            combined_size = len(current_chunk) + len(next_chunk)

            # NEVER merge oversized chunks
            if current_is_oversized or next_is_oversized:
                # Finalize oversized chunk immediately, no merging
                final_chunks.append(current_chunk.strip())
                current_chunk = next_chunk
                current_has_table = next_has_table
                current_is_oversized = next_is_oversized
                continue

            # Decision logic for merging normal-sized chunks
            should_merge = False

            # IMPORTANT: Never merge text-only chunks with table chunks
            # This preserves the semantic distinction between narrative and tabular content
            if current_has_table != next_has_table:
                # One has table, other doesn't - don't merge
                should_merge = False
            # Case 1: Current chunk is very small and doesn't end with table
            elif len(current_chunk) < self.chunk_size // 2 and not current_chunk.strip().endswith('[END TABLE]'):
                # Only merge if combined size is reasonable OR next is also small
                if combined_size <= self.chunk_size * 1.5 or len(next_chunk) < self.chunk_size // 2:
                    should_merge = True

            # Case 2: Next chunk is very small and doesn't start with table
            elif len(next_chunk) < self.chunk_size // 4 and not next_chunk.strip().startswith('[TABLE'):
                should_merge = True

            if should_merge:
                # Merge chunks
                current_chunk = current_chunk + "\n\n" + next_chunk
                current_has_table = current_has_table or next_has_table
            else:
                # Finalize current chunk and start new one
                final_chunks.append(current_chunk.strip())

                # Handle overlap - NEVER overlap across table boundaries
                if self.chunk_overlap > 0 and not current_has_table and not next_has_table:
                    # Safe to overlap - no tables involved
                    if len(current_chunk) > self.chunk_overlap:
                        # Find a semantic boundary for overlap (sentence, paragraph)
                        overlap_text = current_chunk[-self.chunk_overlap:]

                        # Try to start overlap at sentence boundary
                        sentence_start = overlap_text.find('. ')
                        if sentence_start != -1:
                            overlap_text = overlap_text[sentence_start + 2:]

                        current_chunk = overlap_text + "\n\n" + next_chunk
                    else:
                        current_chunk = next_chunk
                elif self.chunk_overlap > 0 and not current_chunk.strip().endswith('[END TABLE]') and not next_chunk.strip().startswith('[TABLE'):
                    # Current or next has table, but not at boundary - safe to do minimal overlap
                    if len(current_chunk) > self.chunk_overlap:
                        overlap_text = current_chunk[-min(self.chunk_overlap, 100):]  # Limited overlap
                        current_chunk = overlap_text + "\n\n" + next_chunk
                    else:
                        current_chunk = next_chunk
                else:
                    # Table at boundary - no overlap
                    current_chunk = next_chunk

                current_has_table = next_has_table

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

            # Extract table blocks for table-aware chunking
            table_blocks = self._extract_table_blocks(page_text)

            # Split page into chunks using table-aware method
            page_chunks = self._split_text_table_aware(page_text, table_blocks)

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

        # Update total_chunks in metadata and add quality scores with all metadata
        for chunk in all_chunks:
            chunk['metadata']['total_chunks'] = len(all_chunks)
            quality = self._get_chunk_quality_score(chunk['content'])

            # Add all quality metrics to metadata
            chunk['metadata']['quality_score'] = quality['quality_score']
            chunk['metadata']['sentence_count'] = quality['sentence_count']
            chunk['metadata']['word_count'] = quality['word_count']
            chunk['metadata']['has_table'] = quality['has_table']
            chunk['metadata']['table_count'] = quality['table_count']
            chunk['metadata']['has_complete_table'] = quality.get('has_complete_table', False)

        logger.info(f"Created {len(all_chunks)} chunks from {len(page_texts)} pages")

        return all_chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using improved sentence boundary detection.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Enhanced sentence boundary detection
        # Handles abbreviations, decimals, and common edge cases
        sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<![A-Z]\.)(?<=\.|\?|!)\s+'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _get_chunk_quality_score(self, chunk: str) -> Dict[str, Any]:
        """Calculate quality metrics for a chunk with table awareness.

        Args:
            chunk: Text chunk to analyze

        Returns:
            Dictionary with quality metrics including table detection
        """
        # Handle edge case: empty or whitespace-only chunk
        if not chunk or not chunk.strip():
            return {
                'char_count': len(chunk),
                'word_count': 0,
                'sentence_count': 0,
                'avg_word_length': 0,
                'avg_sentence_length': 0,
                'ends_complete': False,
                'starts_proper': False,
                'size_variance': 1.0,
                'quality_score': 0.0,
                'has_table': False,
                'table_count': 0,
                'has_complete_table': False
            }

        # Detect tables in chunk
        has_table = '[TABLE' in chunk
        table_count = chunk.count('[TABLE')
        has_complete_table = '[TABLE' in chunk and '[END TABLE]' in chunk

        # Calculate basic metrics
        char_count = len(chunk)
        word_count = len(chunk.split())

        # For table chunks, extract non-table text for sentence analysis
        if has_table:
            # Remove table markers and content for text analysis
            import re
            text_only = re.sub(r'\[TABLE\s+\d+\].*?\[END TABLE\]', '', chunk, flags=re.DOTALL)
            sentence_count = len(self._split_into_sentences(text_only)) if text_only.strip() else 0
        else:
            sentence_count = len(self._split_into_sentences(chunk))

        # Check for incomplete sentences (ends mid-sentence)
        ends_with_punctuation = chunk.strip()[-1] in '.!?;' if chunk.strip() else False
        starts_capitalized = chunk.strip()[0].isupper() if chunk.strip() else False

        # Table-specific quality checks
        ends_with_table = chunk.strip().endswith('[END TABLE]')
        starts_with_table = chunk.strip().startswith('[TABLE')

        # Density metrics
        avg_word_length = char_count / word_count if word_count > 0 else 0
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        # Size variance from target
        size_variance = abs(char_count - self.chunk_size) / self.chunk_size if self.chunk_size > 0 else 0

        # Quality score (0-1, higher is better) with table-aware criteria
        quality_score = 1.0

        if has_table:
            # Table-specific quality assessment
            if not has_complete_table:
                # Partial table (broken across chunks) - lower quality
                quality_score -= 0.3
            else:
                # Complete table(s) - check structure
                if ends_with_table or starts_with_table:
                    # Table at boundary is acceptable
                    quality_score -= 0.0
                else:
                    # Table embedded in text - good contextual chunking
                    quality_score -= 0.0

            # Check if we have text content too
            if sentence_count == 0 and not has_complete_table:
                quality_score -= 0.2  # No text and incomplete table
            elif sentence_count > 0:
                quality_score += 0.1  # Bonus for having context around table

            # Apply size variance penalty for excessively large table chunks
            # Use higher threshold than regular text since tables can legitimately be large
            if size_variance > 2.0:  # More than 3x chunk_size
                quality_score -= 0.3  # Significant penalty for very oversized tables
            elif size_variance > 1.0:  # More than 2x chunk_size
                quality_score -= 0.15  # Moderate penalty for oversized tables

        else:
            # Regular text quality assessment
            if not ends_with_punctuation:
                quality_score -= 0.2  # Penalty for incomplete ending
            if not starts_capitalized:
                quality_score -= 0.1  # Penalty for not starting properly
            if size_variance > 0.5:
                quality_score -= 0.2  # Penalty for being too far from target size
            if sentence_count == 0:
                quality_score -= 0.3  # Penalty for no complete sentences

        return {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(avg_sentence_length, 2),
            'ends_complete': ends_with_punctuation,
            'starts_proper': starts_capitalized,
            'size_variance': round(size_variance, 3),
            'quality_score': round(max(0.0, quality_score), 2),
            'has_table': has_table,
            'table_count': table_count,
            'has_complete_table': has_complete_table
        }
