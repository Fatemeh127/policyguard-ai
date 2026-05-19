"""Schemas for ingest endpoint."""

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request model for document ingestion."""

    document_id: str = Field(..., description="Unique document identifier")
    role: str = Field(..., description="Required role to access this document")


class IngestResponse(BaseModel):
    """Response model for ingestion."""

    document_id: str
    chunks_added: int
    status: str
