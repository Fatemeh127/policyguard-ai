"""FastAPI application initialization."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_vector_store

# Import and include routers
from app.api.routes import ask, eval, health, ingest
from app.api.routes import metrics as metrics_route
from app.core.config import settings
from app.core.logging import setup_logging
from app.ingestion.chunkers.recursive_chunker import recursive_chunk_text
from app.ingestion.loaders.docx_loader import load_docx
from app.ingestion.loaders.pdf_loader import load_pdf
from app.middleware.request_id import RequestIDMiddleware
from app.observability.prometheus_metrics import PrometheusMiddleware, metrics_endpoint
from app.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)

setup_logging()

LOADERS = {
    ".pdf": load_pdf,
    ".docx": load_docx,
}

SAMPLE_DOCS_DIR = Path("data/sample_docs")
ROLES = ["admin", "manager", "employee"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application lifecycle events."""

    logger.info("Starting PolicyGuard AI API")
    logger.info("Environment: %s", settings.environment)

    vs: VectorStore = get_vector_store()

    try:
        logger.info("Loading sample documents...")

        for role in ROLES:
            role_dir = SAMPLE_DOCS_DIR / role

            pdf_files = list(role_dir.glob("*.pdf"))
            docx_files = list(role_dir.glob("*.docx"))

            all_files = pdf_files + docx_files

            logger.info(
                "Loading %d documents for role: %s",
                len(all_files),
                role,
            )

            for file_path in all_files:
                logger.info(
                    "Loading document: %s for role: %s",
                    file_path.name,
                    role,
                )

                # Load file based on extension
                loader = LOADERS.get(file_path.suffix)

                if not loader:
                    logger.warning(
                        "Unsupported file type: %s",
                        file_path.name,
                    )
                    continue

                text = loader(str(file_path))

                chunks = recursive_chunk_text(
                    text,
                    chunk_size=1000,
                    chunk_overlap=200,
                )

                document_id = f"{role}_{file_path.stem}"

                vs.add_documents(
                    chunks=chunks,
                    document_id=document_id,
                    role=role,
                )

                logger.info(
                    "Document loaded successfully: %s (%d chunks), role=%s",
                    file_path.name,
                    len(chunks),
                    role,
                )

        logger.info("All sample documents loaded successfully")

    except Exception as e:
        logger.error("Failed to load sample documents: %s", str(e))

    yield

    logger.info("Shutting down PolicyGuard AI API")


# Create FastAPI app
app = FastAPI(
    title="PolicyGuard AI",
    description="RAG-based organizational document assistant with RBAC",
    version="0.1.0",
    lifespan=lifespan,
)

# Add request ID middleware
app.add_middleware(RequestIDMiddleware)


# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://172.20.10.6:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics() -> Any:
    """Prometheus metrics endpoint."""
    return await metrics_endpoint()


# Health check endpoint
@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {"message": "PolicyGuard AI API", "version": "0.1.0", "status": "running"}


app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(ask.router, prefix="/api", tags=["Q&A"])
app.include_router(ingest.router, prefix="/api", tags=["Ingestion"])
app.include_router(metrics_route.router, prefix="/api", tags=["Metrics"])
app.include_router(eval.router, prefix="/api/v1", tags=["eval"])
