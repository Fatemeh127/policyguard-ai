"""Centralized logging configuration for PolicyGuard AI."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings
from app.middleware.request_context import get_request_id


class RequestIDFilter(logging.Filter):
    """Add request_id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "no-request-id"
        return True


def setup_logging(log_level: str | None = None) -> None:
    """Configure application-wide logging."""

    level_name = (log_level or settings.log_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        fmt=("%(asctime)s | %(levelname)s | %(name)s | " "request_id=%(request_id)s | %(message)s"),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate logs when using uvicorn --reload
    if not root_logger.handlers:
        request_id_filter = RequestIDFilter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(request_id_filter)
        root_logger.addHandler(console_handler)

        if settings.log_file:
            file_handler = RotatingFileHandler(
                filename=settings.log_file,
                maxBytes=10_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(request_id_filter)
            root_logger.addHandler(file_handler)

    for logger_name in settings.noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    root_logger.info(
        "Logging configured | level=%s | environment=%s",
        level_name,
        settings.environment,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance for a module."""
    return logging.getLogger(name)
