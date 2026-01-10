"""Centralized logging configuration for glueprompt."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

# Default log level
_DEFAULT_LOG_LEVEL = logging.INFO


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging (used by server module)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation of log record
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def _get_log_level() -> int:
    """Get log level from environment variable.

    Returns:
        Logging level integer
    """
    level_str = os.getenv("GLUEPROMPT_LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str, _DEFAULT_LOG_LEVEL)


def _configure_logging() -> None:
    """Configure root glueprompt logger."""
    logger = logging.getLogger("glueprompt")
    logger.setLevel(_get_log_level())

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(_get_log_level())
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    _configure_logging()
    return logging.getLogger(name)


def get_json_logger(name: str) -> logging.Logger:
    """Get a logger with JSON formatting (for server module).

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger with JSON formatter
    """
    logger = logging.getLogger(name)
    logger.setLevel(_get_log_level())

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(_get_log_level())
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Initialize logging on module import
_configure_logging()

