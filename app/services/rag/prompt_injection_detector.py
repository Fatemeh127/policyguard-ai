"""Prompt injection detection utilities for RAG requests."""

import re

PROMPT_INJECTION_PATTERNS = (
    r"ignore\s+previous\s+instructions",
    r"forget\s+everything",
    r"act\s+as\s+",
    r"system\s+prompt",
    r"reveal\s+system",
    r"bypass",
)


def is_prompt_injection(query: str) -> bool:
    """Detect simple prompt injection attempts."""

    normalized_query = query.lower()

    return any(re.search(pattern, normalized_query) for pattern in PROMPT_INJECTION_PATTERNS)
