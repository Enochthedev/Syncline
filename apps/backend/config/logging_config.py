"""
Logging Configuration

Provides structured JSON logging with:
- Correlation IDs for request tracing
- Structured log fields
- Log level configuration
- Multiple handlers (console, file, etc.)
"""

import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Any

from config.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.

    Includes:
    - Timestamp
    - Log level
    - Logger name
    - Message
    - Correlation ID (if available)
    - Request context (if available)
    - Exception info (if available)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add request context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "correlation_id",
                "request_id",
                "user_id",
                "endpoint",
                "method",
            ]:
                try:
                    # Only include JSON-serializable values
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    pass

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.

    Uses colors for different log levels.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color
        color = self.COLORS.get(record.levelname, "")

        # Build message
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        parts = [
            f"{color}{record.levelname}{self.RESET}",
            f"[{timestamp}]",
            f"{record.name}",
        ]

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            parts.append(f"[{record.correlation_id}]")

        parts.append(f"- {record.getMessage()}")

        message = " ".join(parts)

        # Add exception if available
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up:
    - Console handler with human-readable format
    - File handler with JSON format (if configured)
    - Root logger configuration
    - Library logger levels
    """
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(ConsoleFormatter())
    handlers.append(console_handler)

    # File handler for JSON logs (production)
    if settings.ENVIRONMENT == "production":
        try:
            file_handler = logging.FileHandler("logs/app.json")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(StructuredFormatter())
            handlers.append(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file handler: {e}")

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # Set levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.LOG_LEVEL}, "
        f"Environment: {settings.ENVIRONMENT}"
    )


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds correlation ID to all log records.

    Usage:
        logger = LoggerAdapter(logging.getLogger(__name__), {"correlation_id": "xyz"})
        logger.info("Message")  # Will include correlation_id in output
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Add extra fields to log record."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(
    name: str, correlation_id: str | None = None, **extra_fields: Any
) -> logging.Logger | LoggerAdapter:
    """
    Get a logger with optional correlation ID and extra fields.

    Args:
        name: Logger name
        correlation_id: Optional correlation ID
        **extra_fields: Additional fields to include in logs

    Returns:
        Logger or LoggerAdapter with extra fields
    """
    logger = logging.getLogger(name)

    if correlation_id or extra_fields:
        extra = extra_fields.copy()
        if correlation_id:
            extra["correlation_id"] = correlation_id
        return LoggerAdapter(logger, extra)

    return logger


__all__ = [
    "setup_logging",
    "get_logger",
    "StructuredFormatter",
    "ConsoleFormatter",
    "LoggerAdapter",
]
