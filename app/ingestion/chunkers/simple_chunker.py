"""
Text chunking utilities for splitting large documents into
overlapping segments suitable for embedding and retrieval.
"""

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)


class Chunk(TypedDict):
    chunk_id: int
    text: str
    start: int
    end: int


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Chunk]:

    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("overlap must be non-negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if len(text) <= chunk_size:
        return [{"chunk_id": 0, "text": text, "start": 0, "end": len(text)}]

    chunks: list[Chunk] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]

        if chunk.strip():
            chunks.append({"chunk_id": len(chunks), "text": chunk, "start": start, "end": end})
        else:
            logger.debug(f"Skipping empty chunk from index {start} to {end}")

        start += chunk_size - chunk_overlap

    return chunks
