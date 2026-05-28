"""CLI script to ingest documents into the vector store."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf
from app.retrieval.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("ingestion")

SUPPORTED_LOADERS: dict[str, Callable[[str], str]] = {
    ".pdf": load_pdf,
    ".docx": load_docx,
}

VALID_ROLES = {"employee", "manager", "admin"}


def load_document(file_path: Path) -> str:
    """Load text from a supported document file."""

    loader = SUPPORTED_LOADERS.get(file_path.suffix.lower())

    if loader is None:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return loader(str(file_path))


def build_document_id(role: str, file_path: Path) -> str:
    """Build stable document ID."""
    return f"{role}_{file_path.stem}"


def process_file(
    file_path: Path,
    vector_store: VectorStore,
    role: str,
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, Any]:
    """Load, chunk, and store one document."""

    start_time = time.perf_counter()

    logger.info("Processing document | file=%s | role=%s", file_path.name, role)

    text = load_document(file_path)

    if not text.strip():
        raise ValueError(f"Empty document: {file_path.name}")

    chunks = recursive_chunk_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    if not chunks:
        raise ValueError(f"No chunks generated: {file_path.name}")

    document_id = build_document_id(role, file_path)

    inserted_count = vector_store.add_documents(
        chunks=chunks,
        document_id=document_id,
        role=role,
    )

    duration = round(time.perf_counter() - start_time, 3)

    logger.info(
        "Document ingested | file=%s | document_id=%s | chunks=%d | duration=%.3fs",
        file_path.name,
        document_id,
        inserted_count,
        duration,
    )

    return {
        "file": file_path.name,
        "document_id": document_id,
        "chunks": inserted_count,
        "duration_seconds": duration,
        "status": "success",
    }


def ingest_documents(
    folder_path: str,
    vector_store: VectorStore | None = None,
    role: str = "employee",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict[str, Any]]:
    """Ingest all supported documents from a folder."""

    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    chunk_size = settings.chunk_size if chunk_size is None else chunk_size
    chunk_overlap = settings.chunk_overlap if chunk_overlap is None else chunk_overlap

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder not found or not a directory: {folder_path}")

    files = sorted(file for file in folder.iterdir() if file.suffix.lower() in SUPPORTED_LOADERS)

    if not files:
        logger.warning("No supported documents found | folder=%s", folder_path)
        return []

    logger.info("Found supported documents | count=%d | folder=%s", len(files), folder_path)

    vector_store = vector_store or VectorStore()
    results: list[dict[str, Any]] = []

    for file_path in files:
        try:
            results.append(
                process_file(
                    file_path=file_path,
                    vector_store=vector_store,
                    role=role,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            )
        except Exception as exc:
            logger.exception("Failed to ingest document | file=%s", file_path.name)
            results.append(
                {
                    "file": file_path.name,
                    "status": "failed",
                    "error": str(exc),
                }
            )

    logger.info("Ingestion complete | total=%d", len(results))

    return results


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Document ingestion pipeline")

    parser.add_argument("--folder", type=str, required=True)
    parser.add_argument("--role", type=str, default="employee")
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ingest_documents(
        folder_path=args.folder,
        role=args.role,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
    )
