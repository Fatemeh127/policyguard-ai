"""Response builders for RAG pipeline outcomes."""

from app.schemas.ask import AskResponse


def blocked_response() -> AskResponse:
    return AskResponse(
        answer="Your request was blocked due to safety policies.",
        sources=[],
        context_used=False,
        metadata={"blocked": True},
    )


def fallback_response() -> AskResponse:
    return AskResponse(
        answer=(
            "I couldn't find enough relevant information to answer your request. "
            "Please try rephrasing your question."
        ),
        sources=[],
        context_used=False,
        metadata={},
    )


def error_response(message: str) -> AskResponse:
    return AskResponse(
        answer=message,
        sources=[],
        context_used=False,
        metadata={"error": True},
    )
