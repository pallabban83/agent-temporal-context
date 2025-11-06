"""
Centralized Logging Configuration

Supports two output formats:
- JSON: Structured JSON logs for production (machine-readable)
- LOGFMT: Key-value format for development (human-readable)

Configuration via environment variables in .env file.
"""

import logging
import sys
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
import traceback

# CST timezone (UTC-6)
CST = timezone(timedelta(hours=-6))


class LogfmtFormatter(logging.Formatter):
    """Format logs in logfmt style (key=value pairs)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as logfmt string."""
        # Format timestamp in CST with timezone
        dt_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)
        dt_cst = dt_utc.astimezone(CST)
        timestamp = dt_cst.strftime('%Y-%m-%d %H:%M:%S') + f'.{int(dt_cst.microsecond / 1000):03d} CST'

        # Collect extra fields first
        extra = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info', 'taskName']:
                if not key.startswith('_'):
                    extra[key] = value

        # Build ordered fields (important fields first)
        parts = []

        # Core fields in specific order
        parts.append(f'time="{timestamp}"')
        parts.append(f'level={record.levelname}')
        parts.append(f'msg="{record.getMessage()}"')

        # Logger name (shortened for readability)
        logger_short = record.name.split('.')[-1] if '.' in record.name else record.name
        parts.append(f'logger={logger_short}')

        # Source location (combined, only if available)
        if record.filename and record.lineno:
            if record.funcName and record.funcName != '<module>':
                parts.append(f'src={record.filename}:{record.funcName}:{record.lineno}')
            else:
                parts.append(f'src={record.filename}:{record.lineno}')

        # Extra fields (sorted for consistency)
        for key in sorted(extra.keys()):
            value = extra[key]
            if isinstance(value, str) and (' ' in value or '=' in value or '"' in value or '\n' in value):
                # Escape quotes and wrap in quotes
                escaped_value = value.replace('"', '\\"').replace('\n', '\\n')
                parts.append(f'{key}="{escaped_value}"')
            else:
                parts.append(f'{key}={value}')

        # Exception info at the end (if present)
        if record.exc_info:
            error_text = ''.join(traceback.format_exception(*record.exc_info))
            escaped_error = error_text.replace('"', '\\"').replace('\n', '\\n')
            parts.append(f'error="{escaped_error}"')

        return ' '.join(parts)


class JSONFormatter(logging.Formatter):
    """Format logs as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        # Format timestamp in CST with timezone
        dt_utc = datetime.fromtimestamp(record.created, tz=timezone.utc)
        dt_cst = dt_utc.astimezone(CST)
        timestamp = dt_cst.strftime('%Y-%m-%d %H:%M:%S') + f'.{int(dt_cst.microsecond / 1000):03d} CST'

        # Base fields
        log_data = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add source location
        log_data['source'] = {
            'file': record.filename,
            'line': record.lineno,
            'path': record.pathname,
        }

        # Add function name
        if record.funcName and record.funcName != '<module>':
            log_data['source']['function'] = record.funcName

        # Add process/thread info
        log_data['process'] = {
            'pid': record.process,
            'name': record.processName,
        }

        log_data['thread'] = {
            'id': record.thread,
            'name': record.threadName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['error'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info),
            }

        # Add extra fields from record
        extra = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info', 'taskName']:
                if not key.startswith('_'):
                    extra[key] = value

        if extra:
            log_data['extra'] = extra

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredLogfmtFormatter(LogfmtFormatter):
    """Logfmt formatter with colors for terminal output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
        'DIM': '\033[2m',         # Dim
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        formatted = super().format(record)

        # Color the level
        level_color = self.COLORS.get(record.levelname, '')
        formatted = formatted.replace(
            f'level={record.levelname}',
            f'level={level_color}{record.levelname}{self.COLORS["RESET"]}'
        )

        # Dim the timestamp
        formatted = formatted.replace(
            'time="',
            f'{self.COLORS["DIM"]}time="'
        )

        # Reset after timestamp, before level
        formatted = formatted.replace(
            f'CST" level=',
            f'CST"{self.COLORS["RESET"]} level='
        )

        # Make message bold
        # Find msg=" and add bold, then reset after the closing quote
        formatted = re.sub(
            r'(msg=")([^"]*)(")',
            rf'{self.COLORS["BOLD"]}\1\2\3{self.COLORS["RESET"]}',
            formatted
        )

        # Dim the logger and src fields
        formatted = formatted.replace(' logger=', f' {self.COLORS["DIM"]}logger=')
        formatted = formatted.replace(' src=', f'{self.COLORS["RESET"]} {self.COLORS["DIM"]}src=')

        # Reset at the end of src or logger (before extra fields or end)
        # Find the first space after src= or logger= that's not inside quotes
        formatted = re.sub(
            r'((?:logger|src)=[^\s]+)',
            rf'\1{self.COLORS["RESET"]}',
            formatted
        )

        return formatted


def setup_logging(
    log_format: str = "logfmt",
    log_level: str = "INFO",
    enable_colors: bool = True
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        log_format: Output format - "json" or "logfmt" (default: "logfmt")
        log_level: Minimum log level (default: "INFO")
        enable_colors: Enable colored output for logfmt (default: True)
    """
    # Determine formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    elif log_format.lower() == "logfmt":
        if enable_colors and sys.stdout.isatty():
            formatter = ColoredLogfmtFormatter()
        else:
            formatter = LogfmtFormatter()
    else:
        raise ValueError(f"Invalid log format: {log_format}. Must be 'json' or 'logfmt'")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure uvicorn loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(getattr(logging, log_level.upper()))

    # Configure Google Cloud SDK loggers
    google_loggers = [
        'google',
        'google.auth',
        'google.cloud',
        'google.api_core',
        'googleapiclient',
        'google_auth_httplib2',
    ]

    for logger_name in google_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        # Set Google SDK loggers to WARNING by default (they're very verbose)
        logger.setLevel(logging.WARNING)

    # Configure our application loggers
    app_loggers = [
        'agent',
        'temporal_embeddings',
        'document_parser',
        'text_chunker',
        'vector_search_manager',
        'config',
    ]

    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True
        logger.setLevel(getattr(logging, log_level.upper()))

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            'log_format': log_format,
            'log_level': log_level,
            'colors_enabled': enable_colors and sys.stdout.isatty(),
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Convenience function for structured logging
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any
) -> None:
    """
    Log a message with structured context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context as keyword arguments

    Example:
        log_with_context(
            logger, 'info', 'Processing document',
            document_id='doc_123',
            page_count=10,
            has_tables=True
        )
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra=context)
