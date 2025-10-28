"""Document parsing utilities for various file formats."""

import io
import logging
from typing import Dict, Any
from pypdf import PdfReader
from docx import Document

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse various document formats and extract text."""

    @staticmethod
    def parse_pdf(file_bytes: bytes) -> str:
        """Extract text from PDF file.

        Args:
            file_bytes: PDF file content as bytes

        Returns:
            Extracted text content
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)

            text_parts = []
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from PDF ({len(reader.pages)} pages)")

            return full_text
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_pdf_by_pages(file_bytes: bytes) -> Dict[str, Any]:
        """Extract text from PDF file page by page.

        Args:
            file_bytes: PDF file content as bytes

        Returns:
            Dictionary with page texts and metadata
        """
        try:
            pdf_file = io.BytesIO(file_bytes)
            reader = PdfReader(pdf_file)

            page_texts = []
            total_chars = 0

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                page_texts.append(text if text else "")
                total_chars += len(text) if text else 0

            logger.info(f"Extracted {total_chars} characters from PDF ({len(reader.pages)} pages)")

            return {
                'page_texts': page_texts,
                'total_pages': len(reader.pages),
                'total_chars': total_chars
            }
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_bytes: bytes) -> str:
        """Extract text from DOCX file.

        Args:
            file_bytes: DOCX file content as bytes

        Returns:
            Extracted text content
        """
        try:
            docx_file = io.BytesIO(file_bytes)
            doc = Document(docx_file)

            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)

            full_text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from DOCX ({len(doc.paragraphs)} paragraphs)")

            return full_text
        except Exception as e:
            logger.error(f"Error parsing DOCX: {str(e)}")
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    @staticmethod
    def parse_text(file_bytes: bytes, encoding: str = 'utf-8') -> str:
        """Extract text from plain text file.

        Args:
            file_bytes: Text file content as bytes
            encoding: Text encoding (default: utf-8)

        Returns:
            Decoded text content
        """
        try:
            text = file_bytes.decode(encoding)
            logger.info(f"Decoded {len(text)} characters from text file")
            return text
        except UnicodeDecodeError:
            # Try alternative encodings
            for alt_encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    text = file_bytes.decode(alt_encoding)
                    logger.info(f"Decoded {len(text)} characters using {alt_encoding}")
                    return text
                except UnicodeDecodeError:
                    continue
            raise ValueError("Unable to decode text file with common encodings")

    @classmethod
    def parse_document(cls, file_bytes: bytes, filename: str, content_type: str = None) -> Dict[str, Any]:
        """Parse document based on file type.

        Args:
            file_bytes: File content as bytes
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            Dictionary with extracted text and metadata
        """
        filename_lower = filename.lower()

        # Determine file type and parse accordingly
        if filename_lower.endswith('.pdf') or content_type == 'application/pdf':
            text = cls.parse_pdf(file_bytes)
            doc_type = 'pdf'
        elif filename_lower.endswith('.docx') or content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = cls.parse_docx(file_bytes)
            doc_type = 'docx'
        elif filename_lower.endswith('.doc'):
            raise ValueError("Legacy .doc format not supported. Please convert to .docx or PDF")
        elif filename_lower.endswith(('.txt', '.md', '.markdown')):
            text = cls.parse_text(file_bytes)
            doc_type = 'text'
        else:
            # Try as text file
            try:
                text = cls.parse_text(file_bytes)
                doc_type = 'text'
            except ValueError:
                raise ValueError(f"Unsupported file format: {filename}. Supported formats: PDF, DOCX, TXT, MD")

        return {
            'text': text,
            'type': doc_type,
            'char_count': len(text),
            'word_count': len(text.split())
        }
