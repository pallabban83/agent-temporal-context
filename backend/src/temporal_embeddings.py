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
from google import genai
from logging_config import get_logger

logger = get_logger(__name__)


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

        logger.info(
            "TemporalEmbeddingHandler initialized",
            extra={
                'model': model_name,
                'requests_per_minute': requests_per_minute,
                'min_delay_seconds': round(self.min_delay, 2),
                'project_id': project_id,
                'location': location
            }
        )

        # Initialize google-genai client with Vertex AI
        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

    def _extract_table_context(self, text: str, position: tuple) -> Optional[str]:
        """Extract table context for a temporal entity if it's inside a table.

        Args:
            text: Full text containing tables
            position: (start, end) position of temporal entity

        Returns:
            Table context string or None
        """
        try:
            # Check if position is inside a table
            table_pattern = r'\[TABLE\s+\d+\](.*?)\[END TABLE\]'

            for table_match in re.finditer(table_pattern, text, re.DOTALL):
                if table_match.start() <= position[0] <= table_match.end():
                    # Entity is inside this table
                    table_text = table_match.group(1)

                    # Handle empty or malformed tables
                    if not table_text or not table_text.strip():
                        return "[Table Data]"

                    # Try to extract column header context
                    lines = table_text.split('\n')
                    if len(lines) >= 2:
                        # First line is likely the header
                        header_line = lines[0]
                        # Extract column headers
                        headers = [h.strip() for h in header_line.split('|') if h.strip()]

                        # Calculate entity's position within the table text
                        entity_text = text[position[0]:position[1]]
                        entity_pos_in_table = position[0] - table_match.start()

                        # Find the row containing the entity using position
                        char_count = 0
                        for line in lines:
                            # Skip markdown separator line (contains only dashes and pipes)
                            if line.strip() and all(c in '-| ' for c in line.strip()):
                                char_count += len(line) + 1  # +1 for newline
                                continue

                            line_start = char_count
                            line_end = char_count + len(line)

                            # Check if entity is in this line by position
                            if line_start <= entity_pos_in_table < line_end:
                                # Entity is in this line - find which column
                                # Calculate position within line
                                pos_in_line = entity_pos_in_table - line_start

                                # Split by pipes and track positions
                                cells = line.split('|')
                                cell_start = 0
                                for i, cell in enumerate(cells):
                                    cell_end = cell_start + len(cell)
                                    # Check if entity position is in this cell
                                    if cell_start <= pos_in_line < cell_end:
                                        # Found the cell! Map to header
                                        # Adjust index (skip empty leading cell from split)
                                        cell_index = i - 1 if cells[0].strip() == '' else i
                                        if 0 <= cell_index < len(headers):
                                            return f"[Table Column: {headers[cell_index]}]"
                                    cell_start = cell_end + 1  # +1 for pipe

                                # If we got here, return generic table data
                                return "[Table Data]"

                            char_count += len(line) + 1  # +1 for newline

                    return "[Table Data]"

            return None

        except Exception as e:
            logger.warning(
                "Error extracting table context",
                exc_info=True,
                extra={'position': position}
            )
            return None

    def extract_temporal_info(self, text: str) -> List[Dict[str, Any]]:
        """Extract temporal information from text including fiscal periods and quarters with table awareness.

        Args:
            text: Input text to analyze

        Returns:
            List of temporal entities found in the text with table context
        """
        temporal_entities = []

        # Pattern for various date formats
        date_patterns = [
            (r'\b\d{4}-\d{2}-\d{2}\b', 'date'),  # YYYY-MM-DD
            (r'\b\d{1,2}/\d{1,2}/\d{4}\b', 'date'),  # M/D/YYYY or MM/DD/YYYY
            # Full month names with optional ordinals (st, nd, rd, th) and flexible separators (comma, period, space)
            (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?[,.\s]+\d{4}\b', 'date'),
            # Abbreviated month names (Jan, Feb, etc.) with optional ordinals and flexible separators
            (r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?[,.\s]+\d{4}\b', 'date'),
            # Day first format (7 January 2025, 7th of January 2025)
            (r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)[,.\s]+\d{4}\b', 'date'),
        ]

        # Fiscal and quarter patterns
        fiscal_patterns = [
            (r'\bQ[1-4]\s+(?:FY\s+)?(?:\d{4}|\d{2})\b', 'fiscal_quarter'),  # Q1 2023, Q1 FY23
            (r'\b(?:FY|Fiscal\s+Year)\s+(?:\d{4}|\d{2})\b', 'fiscal_year'),  # FY2023, Fiscal Year 23
            (r'\b(?:first|second|third|fourth)\s+quarter\s+(?:of\s+)?\d{4}\b', 'fiscal_quarter'),  # first quarter of 2023
            (r'\bH[1-2]\s+\d{4}\b', 'fiscal_half'),  # H1 2023 (half year)
        ]

        # Relative date patterns
        relative_patterns = [
            (r'\b(?:last|previous|past)\s+(?:year|quarter|month|week)\b', 'relative_date'),
            (r'\b(?:this|current)\s+(?:year|quarter|month|week)\b', 'relative_date'),
            (r'\b(?:next|coming|upcoming)\s+(?:year|quarter|month|week)\b', 'relative_date'),
            (r'\b\d+\s+(?:years|quarters|months|weeks|days)\s+ago\b', 'relative_date'),
        ]

        # Year patterns
        year_pattern = [(r'\b(?:19|20)\d{2}\b', 'year')]

        # Month-Year patterns
        month_year_pattern = [(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', 'month_year')]

        # Combine all patterns
        all_patterns = date_patterns + fiscal_patterns + relative_patterns + year_pattern + month_year_pattern

        for pattern, entity_type in all_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract table context if applicable
                table_context = self._extract_table_context(text, match.span())

                temporal_entities.append({
                    'type': entity_type,
                    'value': match.group(),
                    'position': match.span(),
                    'context': table_context  # New: table context
                })

        # Remove duplicates (same position)
        seen_positions = set()
        unique_entities = []
        for entity in temporal_entities:
            pos = entity['position']
            if pos not in seen_positions:
                seen_positions.add(pos)
                unique_entities.append(entity)

        return unique_entities

    def extract_date_from_filename(self, filename: str) -> Optional[str]:
        """Extract temporal information from filename.

        Args:
            filename: Document filename (e.g., "Q1_2023_Report.pdf", "2023-12-31-Summary.pdf")

        Returns:
            Extracted date in normalized format (YYYY-MM-DD or closest approximation), or None if no date found

        Priority (most specific to least specific):
            1. Full ISO date (YYYY-MM-DD) or similar
            2. Fiscal quarter (Q1 2023)
            3. Month-Year (January 2023, 2023-01)
            4. Year only (2023, FY2023)
        """
        if not filename:
            return None

        # Remove file extension for cleaner matching
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # Dictionary to track best match (priority: full_date > quarter > month_year > year)
        matches = {
            'full_date': None,
            'quarter': None,
            'month_year': None,
            'year': None
        }

        # 1. Full date patterns (highest priority)
        full_date_patterns = [
            r'(\d{4})[_\-](\d{2})[_\-](\d{2})',  # 2023-12-31, 2023_12_31
            r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)',  # 20231231 (not part of longer number)
            r'(\d{2})[_\-](\d{2})[_\-](\d{4})',  # 12-31-2023, 12_31_2023
        ]

        # Check for full date patterns first
        for pattern in full_date_patterns:
            match = re.search(pattern, name_without_ext)
            if match:
                groups = match.groups()
                # Try to normalize to YYYY-MM-DD
                if len(groups[0]) == 4:  # Year first (YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD)
                    year, month, day = groups[0], groups[1], groups[2]
                else:  # Year last (MM-DD-YYYY, DD-MM-YYYY)
                    # Assume MM-DD-YYYY for US format
                    month, day, year = groups[0], groups[1], groups[2]

                # Basic validation
                try:
                    year_int = int(year)
                    month_int = int(month)
                    day_int = int(day)
                    if 1900 <= year_int <= 2100 and 1 <= month_int <= 12 and 1 <= day_int <= 31:
                        matches['full_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        break  # Found best match, stop searching
                except ValueError:
                    continue

        # Try month name + day + year format (e.g., "January 07, 2025", "JANUARY 28TH,2025", "July 1st. 2025")
        if not matches['full_date']:
            month_day_year_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)[_\-\s,]+(\d{1,2})(?:st|nd|rd|th)?[,\s.]+(\d{4})'
            match = re.search(month_day_year_pattern, name_without_ext, re.IGNORECASE)
            if match:
                month_name = match.group(1)
                day = match.group(2)
                year = match.group(3)

                # Map month name to number
                month_map = {
                    'january': '01', 'february': '02', 'march': '03', 'april': '04',
                    'may': '05', 'june': '06', 'july': '07', 'august': '08',
                    'september': '09', 'october': '10', 'november': '11', 'december': '12'
                }
                month = month_map.get(month_name.lower(), '01')

                # Validate
                try:
                    year_int = int(year)
                    day_int = int(day)
                    if 1900 <= year_int <= 2100 and 1 <= day_int <= 31:
                        matches['full_date'] = f"{year}-{month}-{day.zfill(2)}"
                except ValueError:
                    pass

        # Try abbreviated month name + day + year format (e.g., "Aug 27, 2024", "Jan 7, 2025")
        if not matches['full_date']:
            abbr_month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2})(?:st|nd|rd|th)?[,\s.]+(\d{4})'
            match = re.search(abbr_month_pattern, name_without_ext, re.IGNORECASE)
            if match:
                abbr_month = match.group(1)
                day = match.group(2)
                year = match.group(3)

                # Map abbreviated month to number
                abbr_map = {
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                    'sep': '09', 'sept': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                }
                month = abbr_map.get(abbr_month.lower(), '01')

                # Validate
                try:
                    year_int = int(year)
                    day_int = int(day)
                    if 1900 <= year_int <= 2100 and 1 <= day_int <= 31:
                        matches['full_date'] = f"{year}-{month}-{day.zfill(2)}"
                except ValueError:
                    pass

        # Try day-first format (e.g., "1st of November, 2024", "7th of January, 2025")
        if not matches['full_date']:
            day_first_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(January|February|March|April|May|June|July|August|September|October|November|December)[,\s.]+(\d{4})'
            match = re.search(day_first_pattern, name_without_ext, re.IGNORECASE)
            if match:
                day = match.group(1)
                month_name = match.group(2)
                year = match.group(3)

                # Map month name to number
                month_map = {
                    'january': '01', 'february': '02', 'march': '03', 'april': '04',
                    'may': '05', 'june': '06', 'july': '07', 'august': '08',
                    'september': '09', 'october': '10', 'november': '11', 'december': '12'
                }
                month = month_map.get(month_name.lower(), '01')

                # Validate
                try:
                    year_int = int(year)
                    day_int = int(day)
                    if 1900 <= year_int <= 2100 and 1 <= day_int <= 31:
                        matches['full_date'] = f"{year}-{month}-{day.zfill(2)}"
                except ValueError:
                    pass

        # 2. Fiscal quarter patterns
        quarter_patterns = [
            r'Q([1-4])[_\-\s]*(?:FY[_\-\s]*)?(\d{4})',  # Q1_2023, Q1-2023, Q1 FY 2023, Q12023
            r'Q([1-4])[_\-\s]*(?:FY)?(\d{2})',          # Q1_FY23, Q1-23, Q123
            r'(\d{4})[_\-\s]*Q([1-4])',                  # 2023Q1, 2023_Q1, 2023-Q1
            r'(first|second|third|fourth)[_\-\s]+quarter[_\-\s]*(\d{4})',  # first_quarter_2023
        ]

        for pattern in quarter_patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Parse quarter and year
                if groups[0].isdigit() and len(groups[0]) == 4:  # Year first format (2023Q1)
                    year = groups[0]
                    quarter = groups[1]
                elif groups[0].lower() in ['first', 'second', 'third', 'fourth']:  # Word format
                    quarter_map = {'first': '1', 'second': '2', 'third': '3', 'fourth': '4'}
                    quarter = quarter_map[groups[0].lower()]
                    year = groups[1]
                else:  # Quarter first format (Q1_2023)
                    quarter = groups[0]
                    year = groups[1]
                    # Handle 2-digit year
                    if len(year) == 2:
                        year = f"20{year}"

                # Store as Q1 2023 format
                matches['quarter'] = f"Q{quarter} {year}"
                break

        # 3. Month-Year patterns
        month_year_patterns = [
            r'(January|February|March|April|May|June|July|August|September|October|November|December)[_\-\s]*(\d{4})',  # January_2023, January2023
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[_\-\s]*(\d{4})',  # Jan2023, Jan_2023
            r'(\d{4})[_\-](\d{2})(?!\d)',  # 2023-01, 2023_01 (not part of full date)
        ]

        for pattern in month_year_patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Parse month and year
                if groups[0].isalpha():  # Month name format
                    month_map = {
                        'january': '01', 'jan': '01',
                        'february': '02', 'feb': '02',
                        'march': '03', 'mar': '03',
                        'april': '04', 'apr': '04',
                        'may': '05',
                        'june': '06', 'jun': '06',
                        'july': '07', 'jul': '07',
                        'august': '08', 'aug': '08',
                        'september': '09', 'sep': '09',
                        'october': '10', 'oct': '10',
                        'november': '11', 'nov': '11',
                        'december': '12', 'dec': '12'
                    }
                    month = month_map.get(groups[0].lower(), '01')
                    year = groups[1]
                    matches['month_year'] = f"{year}-{month}"
                elif len(groups[0]) == 4:  # Year first format (2023-01)
                    year = groups[0]
                    month = groups[1].zfill(2)
                    # Validate month
                    if 1 <= int(month) <= 12:
                        matches['month_year'] = f"{year}-{month}"
                break

        # 4. Year patterns (lowest priority)
        year_patterns = [
            r'(?:FY|Fiscal[_\-\s]*Year)[_\-\s]*(\d{4})',  # FY2023, Fiscal_Year_2023, FY_2023
            r'(?:FY)[_\-\s]*(\d{2})(?!\d)',                # FY23, FY_23
            r'(?<!\d)(19|20)(\d{2})(?!\d)',                # 2023 (standalone year, not part of date)
        ]

        for pattern in year_patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 1:  # Full year (2023, FY2023)
                    year = groups[0]
                    if len(year) == 2:  # Handle FY23
                        year = f"20{year}"
                else:  # Two-digit year split (19|20)(\d{2})
                    year = groups[0] + groups[1]

                # Validate year range
                try:
                    year_int = int(year)
                    if 1900 <= year_int <= 2100:
                        matches['year'] = year
                        break
                except ValueError:
                    continue

        # Return best match based on priority
        if matches['full_date']:
            return matches['full_date']
        elif matches['quarter']:
            return matches['quarter']
        elif matches['month_year']:
            return matches['month_year']
        elif matches['year']:
            return matches['year']

        return None

    def _normalize_date(self, date_string: str) -> Optional[str]:
        """Normalize a date string to YYYY-MM-DD format.

        Handles various date formats:
        - "January 7, 2025" -> "2025-01-07"
        - "Jan 7, 2025" -> "2025-01-07"
        - "01/07/2025" -> "2025-01-07"
        - "2025-01-07" -> "2025-01-07" (already normalized)
        - "January 7th, 2025" -> "2025-01-07"
        - "7 January 2025" -> "2025-01-07"
        - "January 7th.2025" -> "2025-01-07"

        Args:
            date_string: Date string in various formats

        Returns:
            Normalized date in YYYY-MM-DD format, or None if parsing fails
        """
        if not date_string:
            return None

        try:
            # Try dateutil parser for flexible parsing
            from dateutil import parser as date_parser
            import re

            # Remove ordinal suffixes (st, nd, rd, th) ONLY when they follow digits
            # This prevents removing "st" from "August" or "nd" from other words
            cleaned = date_string

            # Remove ordinals after digits: 1st, 2nd, 3rd, 21st, 22nd, 23rd, 31st, etc.
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)([,.\s])', r'\1\3', cleaned)

            # Replace periods with spaces when they separate date components (but not in abbreviated months like "Jan.")
            # This handles cases like "January 7.2025" -> "January 7 2025"
            cleaned = re.sub(r'\.(\d{4})', r' \1', cleaned)

            # Parse the date
            parsed_date = date_parser.parse(cleaned, fuzzy=False)

            # Return in YYYY-MM-DD format
            normalized = parsed_date.strftime('%Y-%m-%d')

            logger.debug(
                "Normalized date",
                extra={
                    'original': date_string,
                    'normalized': normalized
                }
            )

            return normalized

        except Exception as e:
            # If parsing fails, check if it's already in YYYY-MM-DD format
            import re
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_string):
                return date_string

            logger.debug(
                "Could not normalize date",
                extra={
                    'date_string': date_string,
                    'error': str(e)
                }
            )
            return None

    def enhance_text_with_temporal_context(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enhance text with comprehensive temporal context markers.

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

        # Add metadata temporal info
        if metadata and 'document_date' in metadata:
            temporal_context.append(f"Document Date: {metadata['document_date']}")

        if metadata and 'created_at' in metadata:
            temporal_context.append(f"Created: {metadata['created_at']}")

        # Categorize extracted entities with table awareness
        if temporal_entities:
            dates = [e['value'] for e in temporal_entities if e['type'] == 'date']
            years = [e['value'] for e in temporal_entities if e['type'] == 'year']
            fiscal_quarters = [e['value'] for e in temporal_entities if e['type'] == 'fiscal_quarter']
            fiscal_years = [e['value'] for e in temporal_entities if e['type'] == 'fiscal_year']
            month_years = [e['value'] for e in temporal_entities if e['type'] == 'month_year']
            relative_dates = [e['value'] for e in temporal_entities if e['type'] == 'relative_date']

            # Check if any temporal entities are in tables
            table_entities = [e for e in temporal_entities if e.get('context')]
            if table_entities:
                temporal_context.append("Contains Table Data")

            # Add unique temporal references (limit to top 3 of each type for brevity)
            if dates:
                # Normalize dates to YYYY-MM-DD format for consistent embeddings
                normalized_dates = []
                for date in dates:
                    normalized = self._normalize_date(date)
                    if normalized:
                        normalized_dates.append(normalized)
                    else:
                        # If normalization fails, keep original
                        normalized_dates.append(date)

                # Remove duplicates and limit to top 3
                unique_normalized_dates = list(set(normalized_dates))[:3]
                temporal_context.append(f"Dates: {', '.join(unique_normalized_dates)}")
            if fiscal_quarters:
                # Add table context if available
                table_quarters = [e for e in temporal_entities if e['type'] == 'fiscal_quarter' and e.get('context')]
                if table_quarters:
                    temporal_context.append(f"Fiscal Quarters (Tabular): {', '.join(list(set(fiscal_quarters))[:3])}")
                else:
                    temporal_context.append(f"Fiscal Quarters: {', '.join(list(set(fiscal_quarters))[:3])}")
            if fiscal_years:
                temporal_context.append(f"Fiscal Years: {', '.join(list(set(fiscal_years))[:3])}")
            if month_years:
                # Normalize month-year to YYYY-MM format for consistent embeddings
                normalized_month_years = []
                for month_year in month_years:
                    normalized = self._normalize_date(f"{month_year}-01")  # Add day for parsing
                    if normalized:
                        # Extract YYYY-MM from normalized date
                        normalized_month_years.append(normalized[:7])  # YYYY-MM
                    else:
                        # If normalization fails, keep original
                        normalized_month_years.append(month_year)

                # Remove duplicates and limit to top 3
                unique_normalized_month_years = list(set(normalized_month_years))[:3]
                temporal_context.append(f"Periods: {', '.join(unique_normalized_month_years)}")
            if relative_dates:
                temporal_context.append(f"References: {', '.join(list(set(relative_dates))[:2])}")
            # Only add years if not already captured in other patterns (dates, month_years, fiscal_years)
            if years and not dates and not month_years and not fiscal_years:
                temporal_context.append(f"Years: {', '.join(list(set(years))[:3])}")

        # Combine context with original text
        if temporal_context:
            full_context = " | ".join(temporal_context)
            prefix = f"[TEMPORAL_CONTEXT: {full_context}]\n"

            # Limit prefix length to reasonable size (max 200 chars for prefix)
            max_prefix_length = 200
            if len(prefix) > max_prefix_length:
                # Truncate and add indicator
                truncated_context = full_context[:max_prefix_length - 50]  # Leave room for markers
                # Find last complete item (split on |)
                last_separator = truncated_context.rfind('|')
                if last_separator > 0:
                    truncated_context = truncated_context[:last_separator].strip()

                prefix = f"[TEMPORAL_CONTEXT: {truncated_context}...]\n"
                logger.info(
                    "Temporal context truncated",
                    extra={
                        'original_length': len(full_context),
                        'truncated_length': len(truncated_context),
                        'max_length': max_prefix_length
                    }
                )

            return prefix + text

        return text

    def _rate_limit(self):
        """Apply rate limiting by waiting if necessary."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_delay:
            sleep_time = self.min_delay - time_since_last_request
            logger.info(
                "Rate limiting applied",
                extra={
                    'sleep_seconds': round(sleep_time, 2),
                    'min_delay': self.min_delay,
                    'time_since_last': round(time_since_last_request, 2)
                }
            )
            time.sleep(sleep_time)
        elif self.last_request_time > 0:
            logger.debug(
                "No rate limit needed",
                extra={'time_since_last_request': round(time_since_last_request, 2)}
            )

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
                        logger.warning(
                            "Quota exceeded, retrying",
                            extra={
                                'wait_seconds': wait_time,
                                'attempt': attempt + 1,
                                'max_retries': max_retries,
                                'error': str(e)
                            }
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            "Max retries reached for quota error",
                            exc_info=True,
                            extra={'attempts': max_retries}
                        )
                        raise
                else:
                    # Non-quota error, raise immediately
                    logger.error("Embedding API error", exc_info=True)
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

        total_batches = (len(enhanced_texts) + batch_size - 1) // batch_size
        logger.info(
            "Starting batch embedding generation",
            extra={
                'total_texts': len(enhanced_texts),
                'batch_size': batch_size,
                'total_batches': total_batches
            }
        )

        for i in range(0, len(enhanced_texts), batch_size):
            batch = enhanced_texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(
                "Processing embedding batch",
                extra={
                    'batch_num': batch_num,
                    'total_batches': total_batches,
                    'batch_size': len(batch)
                }
            )

            # Generate embeddings using rate-limited API call
            response = self._call_embed_api_with_retry(contents=batch)

            # Extract embedding values from response
            all_embeddings.extend([emb.values for emb in response.embeddings])

        logger.info(
            "Batch embedding generation completed",
            extra={'embeddings_generated': len(all_embeddings)}
        )
        return all_embeddings
