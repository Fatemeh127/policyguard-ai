import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from app.core.config import settings
from app.core.request_context import get_request_id


class RequestIDFilter(logging.Filter):
    """
    Injects request_id from ContextVar into all log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "no-request-id"
        return True


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure application-wide logging with:
    - Console logging
    - Optional rotating file logging
    - Request ID injection
    - Third-party log noise reduction
    """

    # Determine log level
    level_name = (log_level or settings.log_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    # Formatter (includes request_id)
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-25s | [%(request_id)s] | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers in reload environments
    if not root_logger.handlers:

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(RequestIDFilter())
        root_logger.addHandler(console_handler)

        # File handler (optional)
        if getattr(settings, "log_file", None):
            file_handler = RotatingFileHandler(
                settings.log_file,
                maxBytes=10_000_000,   # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(RequestIDFilter())
            root_logger.addHandler(file_handler)

    # Reduce noise from libraries
    noisy_libs = getattr(settings, "noisy_loggers", [
        "httpx",
        "httpcore",
        "urllib3",
        "asyncio",
        "multipart"
    ])

    for lib in noisy_libs:
        logging.getLogger(lib).setLevel(logging.WARNING)

    # Startup log
    root_logger.info(
        "Logging configured | level=%s | environment=%s",
        level_name,
        settings.environment
    )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a standard logger for modules.
    """
    return logging.getLogger(name)