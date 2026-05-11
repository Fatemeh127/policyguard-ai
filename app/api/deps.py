from app.retrieval.vector_store import VectorStore

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store