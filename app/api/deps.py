"""Provide a shared singleton instance of the vector store."""

from app.retrieval.vector_store import VectorStore

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """
    Return a cached singleton instance of the vector store.
    """

    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store
