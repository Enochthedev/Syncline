"""Tests for structured logging functionality."""

import pytest
import json
import logging
import asyncio
from unittest.mock import Mock, patch
from io import StringIO

from services.monitoring.logging import (
    CorrelationIdFilter, StructuredFormatter, setup_structured_logging,
    get_correlation_id, set_correlation_id, generate_correlation_id,
    with_correlation_id, LoggerAdapter, get_logger,
    log_event, log_performance, log_error, log_api_request,
    log_connector_event, log_ai_operation
)


class TestCorrelationId:
    """Test correlation ID functionality."""

    def test_generate_correlation_id(self):
        """Test generating correlation IDs."""
        cid1 = generate_correlation_id()
        cid2 = generate_correlation_id()

        assert cid1 != cid2
        assert len(cid1) > 0
        assert len(cid2) > 0

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-id"

        # Initially should be None
        assert get_correlation_id() is None

        # Set correlation ID
        set_correlation_id(test_id)

        # Should return the set ID
        assert get_correlation_id() == test_id

    @pytest.mark.asyncio
    async def test_correlation_id_context_isolation(self):
        """Test that correlation IDs are isolated between contexts."""
        async def task_with_id(task_id: str):
            set_correlation_id(f"task-{task_id}")
            await asyncio.sleep(0.01)  # Yield control
            return get_correlation_id()

        # Run multiple tasks concurrently
        results = await asyncio.gather(
            task_with_id("1"),
            task_with_id("2"),
            task_with_id("3")
        )

        # Each task should have its own correlation ID
        assert results[0] == "task-1"
        assert results[1] == "task-2"
        assert results[2] == "task-3"


class TestCorrelationIdFilter:
    """Test correlation ID filter."""

    def test_correlation_id_filter(self):
        """Test correlation ID filter adds correlation ID to records."""
        filter_instance = CorrelationIdFilter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Set correlation ID
        set_correlation_id("test-id")

        # Apply filter
        result = filter_instance.filter(record)

        assert result is True
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == "test-id"

    def test_correlation_id_filter_no_id(self):
        """Test correlation ID filter when no ID is set."""
        filter_instance = CorrelationIdFilter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Don't set correlation ID (should be None)

        # Apply filter
        result = filter_instance.filter(record)

        assert result is True
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == "none"


class TestStructuredFormatter:
    """Test structured JSON formatter."""

    def test_structured_formatter_basic(self):
        """Test basic structured formatting."""
        formatter = StructuredFormatter("test-service")

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"

        # Format the record
        formatted = formatter.format(record)

        # Parse as JSON
        log_data = json.loads(formatted)

        assert log_data["service"] == "test-service"
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["correlation_id"] == "test-correlation-id"
        assert log_data["module"] == "test"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_structured_formatter_with_exception(self):
        """Test structured formatting with exception information."""
        formatter = StructuredFormatter("test-service")

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = True
        else:
            exc_info = None

        # Create a log record with exception
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.correlation_id = "test-correlation-id"

        # Format the record
        formatted = formatter.format(record)

        # Parse as JSON
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]

    def test_structured_formatter_with_extra_fields(self):
        """Test structured formatting with extra fields."""
        formatter = StructuredFormatter("test-service")

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"

        # Add extra fields
        record.user_id = "user123"
        record.request_id = "req456"
        record.custom_data = {"key": "value"}

        # Format the record
        formatted = formatter.format(record)

        # Parse as JSON
        log_data = json.loads(formatted)

        assert "extra" in log_data
        assert log_data["extra"]["user_id"] == "user123"
        assert log_data["extra"]["request_id"] == "req456"
        assert log_data["extra"]["custom_data"] == {"key": "value"}


class TestWithCorrelationIdDecorator:
    """Test correlation ID decorator."""

    @pytest.mark.asyncio
    async def test_async_function_with_correlation_id(self):
        """Test async function with correlation ID decorator."""
        @with_correlation_id("test-async-id")
        async def async_function():
            return get_correlation_id()

        result = await async_function()
        assert result == "test-async-id"

    def test_sync_function_with_correlation_id(self):
        """Test sync function with correlation ID decorator."""
        @with_correlation_id("test-sync-id")
        def sync_function():
            return get_correlation_id()

        result = sync_function()
        assert result == "test-sync-id"

    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id(self):
        """Test decorator with auto-generated correlation ID."""
        @with_correlation_id()
        async def async_function():
            return get_correlation_id()

        result = await async_function()
        assert result is not None
        assert len(result) > 0


class TestStructuredLoggingUtilities:
    """Test structured logging utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a string stream to capture log output
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setFormatter(StructuredFormatter("test-service"))

        # Create a test logger
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

        # Set correlation ID for tests
        set_correlation_id("test-correlation-id")

    def teardown_method(self):
        """Clean up test fixtures."""
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_log_event(self):
        """Test structured event logging."""
        log_event(
            self.logger,
            "info",
            "user_login",
            user_id="user123",
            ip_address="192.168.1.1"
        )

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "INFO"
        assert "Event: user_login" in log_data["message"]
        assert log_data["extra"]["event"] == "user_login"
        assert log_data["extra"]["user_id"] == "user123"
        assert log_data["extra"]["ip_address"] == "192.168.1.1"

    def test_log_performance(self):
        """Test performance logging."""
        log_performance(
            self.logger,
            "database_query",
            123.45,
            query_type="SELECT",
            table="users"
        )

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "INFO"
        assert "Performance: database_query took 123.45ms" in log_data["message"]
        assert log_data["extra"]["event"] == "performance"
        assert log_data["extra"]["operation"] == "database_query"
        assert log_data["extra"]["duration_ms"] == 123.45

    def test_log_error(self):
        """Test error logging."""
        error = ValueError("Test error")
        context = {"user_id": "user123", "action": "update_profile"}

        log_error(self.logger, error, context)

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "ERROR"
        assert "Error: Test error" in log_data["message"]
        assert log_data["extra"]["event"] == "error"
        assert log_data["extra"]["error_type"] == "ValueError"
        assert log_data["extra"]["error_message"] == "Test error"
        assert log_data["extra"]["user_id"] == "user123"
        assert log_data["extra"]["action"] == "update_profile"

    def test_log_api_request(self):
        """Test API request logging."""
        log_api_request(
            self.logger,
            "GET",
            "/api/v1/users",
            200,
            45.67,
            user_id="user123"
        )

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "INFO"
        assert "API GET /api/v1/users -> 200 (45.67ms)" in log_data["message"]
        assert log_data["extra"]["event"] == "api_request"
        assert log_data["extra"]["method"] == "GET"
        assert log_data["extra"]["path"] == "/api/v1/users"
        assert log_data["extra"]["status_code"] == 200
        assert log_data["extra"]["duration_ms"] == 45.67
        assert log_data["extra"]["user_id"] == "user123"

    def test_log_connector_event(self):
        """Test connector event logging."""
        log_connector_event(
            self.logger,
            "gmail",
            "message_received",
            "success",
            message_count=5,
            thread_id="thread123"
        )

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "INFO"
        assert "Connector gmail: message_received - success" in log_data["message"]
        assert log_data["extra"]["event"] == "connector_event"
        assert log_data["extra"]["platform"] == "gmail"
        assert log_data["extra"]["event_type"] == "message_received"
        assert log_data["extra"]["status"] == "success"
        assert log_data["extra"]["message_count"] == 5
        assert log_data["extra"]["thread_id"] == "thread123"

    def test_log_ai_operation(self):
        """Test AI operation logging."""
        log_ai_operation(
            self.logger,
            "entity_extractor",
            "extract_entities",
            234.56,
            "success",
            entities_found=3,
            confidence=0.95
        )

        # Get log output
        log_output = self.log_stream.getvalue()
        log_data = json.loads(log_output.strip())

        assert log_data["level"] == "INFO"
        assert "AI entity_extractor: extract_entities - success (234.56ms)" in log_data["message"]
        assert log_data["extra"]["event"] == "ai_operation"
        assert log_data["extra"]["agent_type"] == "entity_extractor"
        assert log_data["extra"]["operation"] == "extract_entities"
        assert log_data["extra"]["duration_ms"] == 234.56
        assert log_data["extra"]["status"] == "success"
        assert log_data["extra"]["entities_found"] == 3
        assert log_data["extra"]["confidence"] == 0.95


class TestLoggingSetup:
    """Test logging setup functionality."""

    @patch('services.monitoring.logging.logging.config.dictConfig')
    def test_setup_structured_logging(self, mock_dict_config):
        """Test structured logging setup."""
        setup_structured_logging(
            level="DEBUG",
            service_name="test-service",
            enable_console=True,
            log_file="/tmp/test.log"
        )

        # Verify dictConfig was called
        mock_dict_config.assert_called_once()

        # Get the config that was passed
        config = mock_dict_config.call_args[0][0]

        assert config["version"] == 1
        assert config["disable_existing_loggers"] is False
        assert "structured" in config["formatters"]
        assert "console" in config["formatters"]
        assert "correlation_id" in config["filters"]

    def test_get_logger(self):
        """Test getting a logger."""
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestLoggingIntegration:
    """Test logging integration functionality."""

    def test_logger_adapter(self):
        """Test logger adapter functionality."""
        base_logger = logging.getLogger("test")
        adapter = LoggerAdapter(base_logger, {})

        # Set correlation ID
        set_correlation_id("test-adapter-id")

        # Test message processing
        msg, kwargs = adapter.process("Test message", {})

        assert "[test-adapter-id]" in msg
        assert "Test message" in msg

    def test_logger_adapter_no_correlation_id(self):
        """Test logger adapter when no correlation ID is set."""
        base_logger = logging.getLogger("test")
        adapter = LoggerAdapter(base_logger, {})

        # Don't set correlation ID

        # Test message processing
        msg, kwargs = adapter.process("Test message", {})

        # Should return original message unchanged
        assert msg == "Test message"
