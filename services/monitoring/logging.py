"""Structured logging with correlation IDs for MESH system."""

import logging
import logging.config
import uuid
import json
import sys
from typing import Dict, Any, Optional
from contextvars import ContextVar
from datetime import datetime
import traceback

# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        """Add correlation ID to the log record."""
        record.correlation_id = correlation_id_var.get() or "none"
        return True


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, service_name: str = "mesh-system"):
        """Initialize structured formatter."""
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'none'),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info', 'correlation_id'
            } and not key.startswith('_'):
                log_entry["extra"] = log_entry.get("extra", {})
                log_entry["extra"][key] = value

        return json.dumps(log_entry, default=str)


def setup_structured_logging(
    level: str = "INFO",
    service_name: str = "mesh-system",
    enable_console: bool = True,
    log_file: Optional[str] = None
):
    """Set up structured logging configuration."""

    # Create formatters
    structured_formatter = StructuredFormatter(service_name)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )

    # Create handlers
    handlers = {}

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(CorrelationIdFilter())
        handlers['console'] = console_handler

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(structured_formatter)
        file_handler.addFilter(CorrelationIdFilter())
        handlers['file'] = file_handler

    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'structured': {
                '()': StructuredFormatter,
                'service_name': service_name
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
            }
        },
        'filters': {
            'correlation_id': {
                '()': CorrelationIdFilter
            }
        },
        'handlers': {},
        'root': {
            'level': level,
            'handlers': list(handlers.keys())
        },
        'loggers': {
            'mesh': {
                'level': level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'services': {
                'level': level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'integrations': {
                'level': level,
                'handlers': list(handlers.keys()),
                'propagate': False
            },
            'api': {
                'level': level,
                'handlers': list(handlers.keys()),
                'propagate': False
            }
        }
    }

    # Add handlers to config
    for name, handler in handlers.items():
        if name == 'console':
            logging_config['handlers'][name] = {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'filters': ['correlation_id'],
                'stream': 'ext://sys.stdout'
            }
        elif name == 'file':
            logging_config['handlers'][name] = {
                'class': 'logging.FileHandler',
                'formatter': 'structured',
                'filters': ['correlation_id'],
                'filename': log_file
            }

    # Apply configuration
    logging.config.dictConfig(logging_config)

    # Set up specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Structured logging configured for service: {service_name}")


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str):
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def with_correlation_id(correlation_id: Optional[str] = None):
    """Decorator to set correlation ID for a function."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            cid = correlation_id or generate_correlation_id()
            token = correlation_id_var.set(cid)
            try:
                return await func(*args, **kwargs)
            finally:
                correlation_id_var.reset(token)

        def sync_wrapper(*args, **kwargs):
            cid = correlation_id or generate_correlation_id()
            token = correlation_id_var.set(cid)
            try:
                return func(*args, **kwargs)
            finally:
                correlation_id_var.reset(token)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes correlation ID."""

    def process(self, msg, kwargs):
        """Process log message to include correlation ID."""
        correlation_id = get_correlation_id()
        if correlation_id:
            return f"[{correlation_id}] {msg}", kwargs
        return msg, kwargs


def get_logger(name: str) -> logging.Logger:
    """Get a logger with correlation ID support."""
    logger = logging.getLogger(name)
    return logger


# Structured logging utilities
def log_event(
    logger: logging.Logger,
    level: str,
    event: str,
    **kwargs
):
    """Log a structured event with additional context."""
    extra = {
        "event": event,
        **kwargs
    }

    getattr(logger, level.lower())(f"Event: {event}", extra=extra)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    **kwargs
):
    """Log performance metrics."""
    extra = {
        "event": "performance",
        "operation": operation,
        "duration_ms": duration_ms,
        **kwargs
    }

    logger.info(
        f"Performance: {operation} took {duration_ms:.2f}ms", extra=extra)


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any] = None
):
    """Log an error with structured context."""
    extra = {
        "event": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(context or {})
    }

    logger.error(f"Error: {str(error)}", extra=extra, exc_info=True)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None
):
    """Log API request with structured data."""
    extra = {
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "user_id": user_id
    }

    logger.info(
        f"API {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
        extra=extra
    )


def log_connector_event(
    logger: logging.Logger,
    platform: str,
    event_type: str,
    status: str,
    **kwargs
):
    """Log connector events with structured data."""
    extra = {
        "event": "connector_event",
        "platform": platform,
        "event_type": event_type,
        "status": status,
        **kwargs
    }

    logger.info(
        f"Connector {platform}: {event_type} - {status}",
        extra=extra
    )


def log_ai_operation(
    logger: logging.Logger,
    agent_type: str,
    operation: str,
    duration_ms: float,
    status: str,
    **kwargs
):
    """Log AI operations with structured data."""
    extra = {
        "event": "ai_operation",
        "agent_type": agent_type,
        "operation": operation,
        "duration_ms": duration_ms,
        "status": status,
        **kwargs
    }

    logger.info(
        f"AI {agent_type}: {operation} - {status} ({duration_ms:.2f}ms)",
        extra=extra
    )
