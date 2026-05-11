"""Common schema definitions."""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source document reference."""
    document_id: str
    chunk_id: int
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str | None = None