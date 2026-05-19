import logging
from pathlib import Path
from typing import List

from app.ingestion.loaders.pdf_loader import load_pdf
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.api.deps import get_vector_store

logger = logging.getLogger(__name__)


def get_sample_documents(folder: str = "data/sample_docs") -> List[Path]:
    sample_folder = Path(folder)

    if not sample_folder.exists():
        logger.warning("Sample documents folder not found: %s", folder)
        return []

    return list(sample_folder.glob("*.pdf")) + list(sample_folder.glob("*.docx"))


def load_sample_documents(force_reload: bool = False) -> int:
    vs = get_vector_store()

    files = get_sample_documents()

    if not files:
        logger.warning("No sample documents found")
        return 0

    loaded = 0

    for file_path in files:
        try:
            if file_path.suffix.lower() == ".pdf":
                text = load_pdf(str(file_path))
            elif file_path.suffix.lower() == ".docx":
                text = load_docx(str(file_path))
            else:
                continue

            if not text.strip():
                continue

            chunks = recursive_chunk_text(text, chunk_size=1000, chunk_overlap=200)

            count = vs.add_documents(chunks=chunks, document_id=file_path.name, role="employee")

            logger.info("Loaded %s (%d chunks)", file_path.name, count)
            loaded += 1

        except Exception as e:
            logger.error("Failed to load %s: %s", file_path.name, e)

    return loaded


def ensure_sample_data():
    try:
        load_sample_documents()
    except Exception as e:
        logger.error("Startup ingestion failed: %s", e)
