"""Tests for structured logging."""

import json
import logging
from io import StringIO

from app.core.logging import ConsoleFormatter, JSONFormatter, LoggerAdapter, get_logger


class TestJSONFormatter:
    """Tests for JSON log formatter."""

    def test_basic_log_format(self):
        """Test basic JSON log output structure."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["line"] == 42
        assert "timestamp" in parsed
        assert "process" in parsed
        assert "thread" in parsed

    def test_json_formatter_with_extra(self):
        """Test JSON formatter includes extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="User login",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.ip_address = "192.168.1.1"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["extra"]["user_id"] == 123
        assert parsed["extra"]["ip_address"] == "192.168.1.1"

    def test_json_formatter_with_exception(self):
        """Test JSON formatter includes exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/app/test.py",
            lineno=42,
            msg="An error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test error"
        assert isinstance(parsed["exception"]["traceback"], list)

    def test_json_formatter_without_extra(self):
        """Test JSON formatter can exclude extra fields."""
        formatter = JSONFormatter(include_extra=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.custom_field = "should not appear"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "extra" not in parsed

    def test_json_formatter_handles_non_serializable(self):
        """Test JSON formatter handles non-JSON-serializable objects."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add a non-serializable object
        record.custom_object = object()

        # Should not raise an exception
        output = formatter.format(record)
        parsed = json.loads(output)

        # Object should be converted to string representation
        assert "extra" in parsed
        assert "object" in parsed["extra"]["custom_object"].lower()


class TestConsoleFormatter:
    """Tests for console log formatter."""

    def test_basic_console_format(self):
        """Test console formatter output structure."""
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "INFO" in output
        assert "test.logger" in output
        assert "Test message" in output

    def test_console_formatter_with_colors(self):
        """Test console formatter includes color codes."""
        formatter = ConsoleFormatter()

        for level, color in ConsoleFormatter.COLORS.items():
            record = logging.LogRecord(
                name="test.logger",
                level=getattr(logging, level),
                pathname="/app/test.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            assert color in output, f"Color code missing for {level}"


class TestLoggerAdapter:
    """Tests for LoggerAdapter context injection."""

    def test_adapter_adds_context(self):
        """Test LoggerAdapter adds context to log records."""
        base_logger = logging.getLogger("test.adapter")
        base_logger.setLevel(logging.DEBUG)

        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        base_logger.addHandler(handler)

        adapter = LoggerAdapter(base_logger, {"request_id": "abc-123", "user_id": 42})
        adapter.info("Test message")

        handler.flush()
        output = stream.getvalue()
        parsed = json.loads(output)

        assert parsed["extra"]["request_id"] == "abc-123"
        assert parsed["extra"]["user_id"] == 42

        # Cleanup
        base_logger.removeHandler(handler)

    def test_adapter_merges_extra(self):
        """Test LoggerAdapter merges context with per-call extra."""
        base_logger = logging.getLogger("test.adapter.merge")
        base_logger.setLevel(logging.DEBUG)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        base_logger.addHandler(handler)

        adapter = LoggerAdapter(base_logger, {"request_id": "abc-123"})
        adapter.info("Test message", extra={"action": "login"})

        handler.flush()
        output = stream.getvalue()
        parsed = json.loads(output)

        assert parsed["extra"]["request_id"] == "abc-123"
        assert parsed["extra"]["action"] == "login"

        base_logger.removeHandler(handler)


class TestSetupLogging:
    """Tests for logging setup function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_json_formatter_produces_valid_json(self):
        """Test that JSONFormatter produces parseable JSON output."""
        # Create a logger with JSON formatter
        test_logger = logging.getLogger("test.json.output")
        test_logger.setLevel(logging.DEBUG)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        test_logger.addHandler(handler)

        # Log a message
        test_logger.info("Test JSON output", extra={"user_id": 123})

        handler.flush()
        output = stream.getvalue()

        # Verify it's valid JSON
        parsed = json.loads(output)
        assert parsed["message"] == "Test JSON output"
        assert parsed["extra"]["user_id"] == 123

        test_logger.removeHandler(handler)

    def test_console_formatter_produces_readable_output(self):
        """Test that ConsoleFormatter produces human-readable output."""
        test_logger = logging.getLogger("test.console.output")
        test_logger.setLevel(logging.DEBUG)

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(ConsoleFormatter())
        test_logger.addHandler(handler)

        test_logger.info("Test console output")

        handler.flush()
        output = stream.getvalue()

        assert "INFO" in output
        assert "Test console output" in output

        test_logger.removeHandler(handler)
