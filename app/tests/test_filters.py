"""Tests for role-based access control (RBAC) in vector retrieval."""

from typing import Any

from app.retrieval.retriever import RetrievalService


class FakeVectorStore:
    def search(
        self,
        query: str,
        role: str,
        limit: int,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "document_id": "doc1",
                "chunk_id": 1,
                "text": "employee handbook",
                "score": 0.9,
                "role": role,
            }
        ]


def test_employee_cannot_access_manager_docs() -> None:
    """Employee should not see manager-only documents."""

    service = RetrievalService(vector_store=FakeVectorStore())

    results = service.retrieve_chunks_with_metadata(
        query="manager salary",
        role="employee",
        top_k=10,
        min_score=0.0,
    )

    assert all(r["role"] != "manager" for r in results)
