"""Schemas for ask endpoint."""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Source


class AskRequest(BaseModel):
    """Request model for asking questions."""

    query: str = Field(..., min_length=1, max_length=500, description="User question")
    role: str = Field(..., description="User role for RBAC filtering")
    limit: int = Field(default=5, ge=1, le=20, description="Max chunks to retrieve")
    session_id: str


class AskResponse(BaseModel):
    """Response model for ask endpoint."""

    answer: str
    sources: list[Source]
    context_used: bool
    metadata: dict[str, Any]
