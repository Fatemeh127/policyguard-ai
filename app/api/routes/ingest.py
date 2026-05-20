import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_vector_store
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf
from app.retrieval.vector_store import VectorStore
from app.schemas.ingest import IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    role: str = Form("employee"),
    vs: VectorStore = Depends(get_vector_store),
) -> IngestResponse:
    MAX_FILE_SIZE = 10 * 1024 * 1024

    try:
        file_content = await file.read()

        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(413, "File too large (max 10MB)")

    except Exception as exc:
        logger.exception("File read failed")
        raise HTTPException(status_code=400, detail="Failed to read file") from exc

    tmp_path = None

    try:
        filename = file.filename or ""
        suffix = os.path.splitext(filename)[1].lower()

        if suffix not in [".pdf", ".docx"]:

            raise HTTPException(400, "Only PDF and DOCX supported")

        # unique document id
        document_id = f"{document_id}_{uuid.uuid4().hex}"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        # load
        text = load_pdf(tmp_path) if suffix == ".pdf" else load_docx(tmp_path)

        if not text.strip():
            raise HTTPException(400, "Empty document")

        # chunk
        chunks = recursive_chunk_text(text, 1000, 200)

        # store
        count = vs.add_documents(chunks=chunks, document_id=document_id, role=role)

        logger.info("Ingest success | doc=%s | chunks=%d", document_id, count)

        return IngestResponse(document_id=document_id, chunks_added=count, status="success")

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Ingestion failed for request")

        raise HTTPException(status_code=500, detail="Document ingestion failed") from e

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning("Failed to delete temp file: %s", e)
