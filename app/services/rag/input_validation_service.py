"""Input validation service for RAG requests."""

from app.services.rag.input_validator import validate_rag_input


class InputValidationService:
    """Handles validation for RAG input."""

    def validate(
        self,
        query: str,
        role: str,
        limit: int,
    ) -> str | None:
        return validate_rag_input(
            query=query,
            role=role,
            limit=limit,
        )
