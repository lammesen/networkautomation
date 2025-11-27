"""Core logging configuration with structured JSON support."""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

from .config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging.

    Outputs logs as JSON objects with consistent fields for easy parsing
    by log aggregation tools like Loki, Elasticsearch, or CloudWatch.
    """

    def __init__(self, include_extra: bool = True) -> None:
        """Initialize JSON formatter.

        Args:
            include_extra: Whether to include extra fields from log records.
        """
        super().__init__()
        self.include_extra = include_extra
        # Fields that are part of LogRecord but shouldn't be in 'extra'
        self._reserved_attrs = {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add process and thread info for debugging
        log_entry["process"] = {
            "id": record.process,
            "name": record.processName,
        }
        log_entry["thread"] = {
            "id": record.thread,
            "name": record.threadName,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add stack info if present
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        # Add any extra fields passed to the logger
        if self.include_extra:
            extra = {}
            for key, value in record.__dict__.items():
                if key not in self._reserved_attrs and not key.startswith("_"):
                    # Try to serialize the value, fallback to string representation
                    try:
                        json.dumps(value)
                        extra[key] = value
                    except (TypeError, ValueError):
                        extra[key] = str(value)
            if extra:
                log_entry["extra"] = extra

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with colors for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console output."""
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Base message
        formatted = (
            f"{timestamp} - {color}{record.levelname:8}{self.RESET} - "
            f"{record.name} - {record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return formatted


def setup_logging() -> None:
    """Setup application logging with environment-appropriate formatting.

    In production (ENVIRONMENT=production), uses JSON formatting for log aggregation.
    In development, uses human-readable console formatting with colors.

    The LOG_FORMAT environment variable can override this behavior:
    - LOG_FORMAT=json: Force JSON formatting
    - LOG_FORMAT=console: Force console formatting
    """
    log_level = getattr(logging, settings.log_level.upper())
    log_format = getattr(settings, "log_format", None)

    # Determine formatter based on environment or explicit setting
    if log_format == "json":
        formatter: logging.Formatter = JSONFormatter()
    elif log_format == "console":
        formatter = ConsoleFormatter()
    elif settings.environment.lower() == "production":
        formatter = JSONFormatter()
    else:
        formatter = ConsoleFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("netmiko").setLevel(logging.WARNING)
    logging.getLogger("nornir").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with the given name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("User logged in", extra={"user_id": 123, "ip": "192.168.1.1"})
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages.

    Useful for adding request-specific context like user_id, customer_id, etc.

    Example:
        >>> base_logger = get_logger(__name__)
        >>> logger = LoggerAdapter(base_logger, {"request_id": "abc-123", "user_id": 42})
        >>> logger.info("Processing request")  # Includes request_id and user_id
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Add extra context to log record."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs
