"""Input validation for RAG question requests."""

VALID_ROLES = {"employee", "manager", "admin"}


def validate_rag_input(
    query: str,
    role: str,
    limit: int,
) -> str | None:
    """Validate basic RAG input values."""

    if role not in VALID_ROLES:
        return "Invalid role."

    if not query.strip():
        return "Query cannot be empty."

    if len(query) > 5000:
        return "Query is too large."

    if limit <= 0 or limit > 20:
        return "Invalid retrieval limit."

    return None
