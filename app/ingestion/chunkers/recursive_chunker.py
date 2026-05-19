"""Recursive text chunker with semantic boundaries."""

import logging

# import re

logger = logging.getLogger(__name__)


def recursive_chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> list[dict]:
    """
    Split text recursively using semantic separators.

    Tries separators in order: paragraphs → newlines → sentences → words → chars
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Invalid chunk_overlap")

    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    # Split text into sentences/parts based on first valid separator
    chunks_text = _split_text_with_separators(text, chunk_size, separators)

    # Build chunks with overlap
    chunks = []
    for i, chunk_text in enumerate(chunks_text):
        chunks.append(
            {
                "chunk_id": i,
                "text": chunk_text,
                "char_count": len(chunk_text),
            }
        )

    return chunks


def _split_text_with_separators(
    text: str,
    chunk_size: int,
    separators: list[str],
) -> list[str]:
    """Helper: recursively split text using separators."""

    # Base case: text fits
    if len(text) <= chunk_size:
        return [text]

    # Try each separator
    for i, sep in enumerate(separators):
        if sep == "":
            # Character-level fallback
            return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

        if sep in text:
            splits = text.split(sep)
            chunks = []
            current_chunk = ""

            for split in splits:
                # Test if adding this split exceeds chunk_size
                test_chunk = current_chunk + sep + split if current_chunk else split

                if len(test_chunk) <= chunk_size:
                    current_chunk = test_chunk
                else:
                    # Save current chunk
                    if current_chunk:
                        chunks.append(current_chunk)

                    # If split itself is too large, recurse with next separators
                    if len(split) > chunk_size:
                        sub_chunks = _split_text_with_separators(
                            split, chunk_size, separators[i + 1 :]
                        )
                        chunks.extend(sub_chunks)
                        current_chunk = ""
                    else:
                        current_chunk = split

            # Don't forget the last chunk
            if current_chunk:
                chunks.append(current_chunk)

            return chunks

    # Fallback (shouldn't reach here)
    return [text]
