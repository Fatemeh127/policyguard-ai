"""
Professional trace logger for request-level observability.
"""

import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

from app.core.logging import get_logger
from app.core.request_context import get_request_id

logger = get_logger(__name__)


class TraceLogger:
    """
    High-level tracing utility for tracking request flow and performance.
    """

    def __init__(self, component: str):
        self.component = component
        self.request_id = get_request_id()

    def _log(self, level: str, message: str, **kwargs):
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)

        msg = f"[{self.component}] {message}"
        if extra:
            msg += f" | {extra}"

        if level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "debug":
            logger.debug(msg)

    # Basic logs
    def info(self, message: str, **kwargs):
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log("error", message, **kwargs)

    def debug(self, message: str, **kwargs):
        self._log("debug", message, **kwargs)

    # Step timing (VERY IMPORTANT)
    @contextmanager
    def span(self, step: str, **kwargs):
        """
        Context manager to measure execution time of a block.
        """
        start = time.time()

        self.debug(f"{step} started", **kwargs)

        try:
            yield
            duration = round(time.time() - start, 3)
            self.info(f"{step} completed", duration_s=duration, **kwargs)

        except Exception as e:
            duration = round(time.time() - start, 3)
            self.error(f"{step} failed", duration_s=duration, error=str(e))
            raise

    # Specialized helpers (RAG)
    def log_retrieval(self, num_chunks: int, max_score: Optional[float]):
        self.info(
            "retrieval_result",
            chunks=num_chunks,
            max_score=round(max_score, 3) if max_score else None,
        )

    def log_generation(self, answer_length: int):
        self.info("generation_result", answer_len=answer_length)

    def log_fallback(self, reason: str):
        self.warning("fallback_triggered", reason=reason)

    def log_blocked(self, reason: str):
        self.warning("request_blocked", reason=reason)
