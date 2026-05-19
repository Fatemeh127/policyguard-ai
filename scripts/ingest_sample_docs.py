"""Script to ingest sample documents into the system."""

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf
from app.retrieval.vector_store import VectorStore

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("ingestion")

# --- Imports (project modules) ---
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Retry decorator ---
def retry(max_attempts=3, delay=1.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Retry {attempt}/{max_attempts} failed: {e}")
                    if attempt == max_attempts:
                        raise
                    time.sleep(delay * attempt)
            raise RuntimeError("Unreachable code reached in retry wrapper")

        return wrapper

    return decorator


# --- File loader ---
@retry(max_attempts=3)
def load_document(file_path: Path) -> str:
    if file_path.suffix.lower() == ".pdf":
        return load_pdf(str(file_path))
    if file_path.suffix.lower() == ".docx":
        return load_docx(str(file_path))
    raise ValueError(f"Unsupported file type: {file_path}")


# --- Processing logic ---
def process_file(
    file_path: Path, vector_store: VectorStore, role: str, chunk_size: int, chunk_overlap: int
) -> dict[str, Any]:
    start_time = time.time()

    logger.info(f"Processing {file_path.name}")

    # Load
    text = load_document(file_path)
    if not text.strip():
        raise ValueError("Empty document")

    # Chunk
    chunks = recursive_chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Metadata
    base_metadata = {
        "document_id": file_path.name,
        "source": str(file_path),
        "role": role,
        "timestamp": time.time(),
        "chunk_count": len(chunks),
    }

    documents = []
    for i, chunk in enumerate(chunks):
        documents.append({
            "text": chunk,
            "metadata": {
                **base_metadata,
                "chunk_index": i,
                "chunk_count": len(chunks)
            }
        })

    # Store
    count = vector_store.add_documents(chunks=chunks, document_id=file_path.name, role=role)

    duration = round(time.time() - start_time, 2)

    logger.info(f"Done {file_path.name} | chunks={count} | {duration}s")

    return {"file": file_path.name,
            "chunks": count,
            "duration": duration,
            "document_id": base_metadata["document_id"]
}


# --- Main ingestion ---
def ingest_documents(
    folder_path: str,
    vector_store: VectorStore | None = None,
    role: str = "employee",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    max_workers: int = 4,
):
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    files = list(folder.glob("*.pdf")) + list(folder.glob("*.docx"))

    if not files:
        logger.warning("No documents found")
        return []

    logger.info(f"Found {len(files)} files")

    vs = vector_store or VectorStore()

    results = []

    # Parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_file, file_path, vs, role, chunk_size, chunk_overlap)
            for file_path in files
        ]

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed processing file: {e}")

    logger.info("Ingestion complete")

    return results


# --- CLI ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Document ingestion pipeline")

    parser.add_argument("--folder", type=str, required=True)
    parser.add_argument("--role", type=str, default="employee")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--overlap", type=int, default=200)

    args = parser.parse_args()

    ingest_documents(
        folder_path=args.folder,
        role=args.role,
        max_workers=args.workers,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
    )
