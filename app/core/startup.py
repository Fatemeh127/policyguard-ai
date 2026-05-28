"""Startup ingestion utilities for PolicyGuard AI."""

import logging
from collections.abc import Callable
from pathlib import Path

from app.api.deps import get_vector_store
from app.core.config import settings
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

SUPPORTED_LOADERS: dict[str, Callable[[str], str]] = {
    ".pdf": load_pdf,
    ".docx": load_docx,
}

ROLES = ("employee", "manager", "admin")


def get_role_directories(base_dir: Path | None = None) -> list[tuple[str, Path]]:
    """Return valid role directories under the sample docs directory."""
    root_dir = base_dir or settings.sample_docs_dir

    if not root_dir.exists():
        logger.warning("Sample documents directory not found: %s", root_dir)
        return []

    role_directories: list[tuple[str, Path]] = []

    for role in ROLES:
        role_dir = root_dir / role

        if not role_dir.exists():
            logger.warning("Role directory not found: %s", role_dir)
            continue

        if not role_dir.is_dir():
            logger.warning("Role path is not a directory: %s", role_dir)
            continue

        role_directories.append((role, role_dir))

    return role_directories


def get_supported_files(role_dir: Path) -> list[Path]:
    """Return supported PDF and DOCX files recursively from a role directory."""
    files: list[Path] = []

    for suffix in SUPPORTED_LOADERS:
        files.extend(role_dir.rglob(f"*{suffix}"))

    return sorted(file for file in files if file.is_file())


def build_document_id(role: str, file_path: Path) -> str:
    """Build a stable role-aware document ID."""
    safe_name = file_path.stem.lower().replace(" ", "_")
    extension = file_path.suffix.lower().lstrip(".")
    return f"{role}_{safe_name}_{extension}"


def load_document_text(file_path: Path) -> str:
    """Load text from a supported document file."""
    loader = SUPPORTED_LOADERS.get(file_path.suffix.lower())

    if loader is None:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return loader(str(file_path))


def document_already_loaded(
    vector_store: VectorStore,
    document_id: str,
    role: str,
) -> bool:
    """Check whether a document is already loaded."""
    exists_method = getattr(vector_store, "document_exists", None)

    if callable(exists_method):
        return bool(exists_method(document_id=document_id, role=role))

    return False


def delete_existing_document(
    vector_store: VectorStore,
    document_id: str,
    role: str,
) -> None:
    """Delete an existing document if the vector store supports deletion."""
    delete_method = getattr(vector_store, "delete_document", None)

    if callable(delete_method):
        delete_method(document_id=document_id, role=role)
        logger.info("Deleted existing document before reload: %s | role=%s", document_id, role)
        return

    logger.warning("force_reload=True, but vector store has no delete_document method")


def ingest_file(
    vector_store: VectorStore,
    file_path: Path,
    role: str,
    force_reload: bool = False,
) -> int:
    """Load, chunk, and store one file in the vector database."""
    if role not in ROLES:
        raise ValueError(f"Unsupported role: {role}")

    document_id = build_document_id(role=role, file_path=file_path)

    if not force_reload and document_already_loaded(vector_store, document_id, role):
        logger.info("Skipping already-loaded document: %s | role=%s", document_id, role)
        return 0

    if force_reload:
        delete_existing_document(vector_store, document_id, role)

    text = load_document_text(file_path)

    if not text.strip():
        logger.warning("Skipping empty document: %s | role=%s", file_path.name, role)
        return 0

    chunks = recursive_chunk_text(
        text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    if not chunks:
        logger.warning("No chunks created for document: %s | role=%s", file_path.name, role)
        return 0

    inserted_count = vector_store.add_documents(
        chunks=chunks,
        document_id=document_id,
        role=role,
    )

    logger.info(
        "Loaded document successfully | document_id=%s | role=%s | file=%s | chunks=%d",
        document_id,
        role,
        file_path.name,
        inserted_count,
    )

    return inserted_count


def load_sample_documents(force_reload: bool = False) -> int:
    """Load all role-based sample documents into the vector database."""
    vector_store = get_vector_store()
    total_chunks = 0

    role_directories = get_role_directories()

    if not role_directories:
        logger.warning("No role directories found for sample document ingestion")
        return 0

    for role, role_dir in role_directories:
        files = get_supported_files(role_dir)

        logger.info(
            "Found %d supported files for role=%s in %s",
            len(files),
            role,
            role_dir,
        )

        for file_path in files:
            try:
                total_chunks += ingest_file(
                    vector_store=vector_store,
                    file_path=file_path,
                    role=role,
                    force_reload=force_reload,
                )
            except Exception:
                logger.exception(
                    "Failed to ingest document: %s | role=%s",
                    file_path,
                    role,
                )

    logger.info("Sample document ingestion completed | total_chunks=%d", total_chunks)
    return total_chunks


def ensure_sample_data(force_reload: bool = False) -> None:
    """Safe startup wrapper for sample document ingestion."""
    try:
        load_sample_documents(force_reload=force_reload)
    except Exception:
        logger.exception("Startup sample document ingestion failed")
