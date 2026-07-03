"""Retrieve relevant chunks from the vector store for a given query."""

import logging
from typing import Any, Protocol

from app.core.config import settings
from app.retrieval.filter import apply_filters

logger = logging.getLogger(__name__)


class SearchableVectorStore(Protocol):
    """Protocol for vector stores that support search."""

    def search(
        self,
        query: str,
        role: str,
        limit: int,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]: ...


ROLE_ACCESS: dict[str, list[str]] = {
    "employee": ["employee"],
    "manager": ["manager", "employee"],
    "admin": ["admin", "manager", "employee"],
}


class RetrievalService:

    def __init__(
        self,
        vector_store: SearchableVectorStore,
    ) -> None:
        self.vector_store = vector_store

    def _search_vector_store(
        self,
        query: str,
        role: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Safely search the vector store for a single role."""

        try:
            results = self.vector_store.search(
                query=query,
                role=role,
                limit=top_k,
            )
        except Exception:
            logger.exception(
                "Vector search failed | role=%s | top_k=%d",
                role,
                top_k,
            )
            return []

        if not isinstance(results, list):
            logger.warning(
                "Vector store returned invalid result type: %s",
                type(results),
            )
            return []

        return results

    def _search_accessible_roles(
        self,
        query: str,
        role: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Search all roles accessible by the caller role."""

        accessible_roles = ROLE_ACCESS.get(role)

        if accessible_roles is None:
            logger.warning("Unknown role received for retrieval: %s", role)
            return []

        all_results: list[dict[str, Any]] = []

        for accessible_role in accessible_roles:
            role_results = self._search_vector_store(
                query=query,
                role=accessible_role,
                top_k=top_k,
            )

            all_results.extend(role_results)

        logger.debug(
            "Vector search completed across accessible roles | role=%s | roles=%s | results=%d",
            role,
            accessible_roles,
            len(all_results),
        )

        return all_results

    def _get_filtered_results(
        self,
        query: str,
        role: str,
        top_k: int,
        min_score: float,
    ) -> list[dict[str, Any]]:
        """
        Search all accessible roles, filter, deduplicate, sort, and retry once if needed.
        """

        results = self._search_accessible_roles(
            query=query,
            role=role,
            top_k=top_k,
        )

        filtered = apply_filters(
            results,
            min_score=min_score,
            dedup=True,
            limit=top_k,
        )

        if filtered:
            return filtered

        logger.warning(
            "No chunks after filtering. Retrying with expanded top_k | role=%s | top_k=%d",
            role,
            top_k * 2,
        )

        retry_results = self._search_accessible_roles(
            query=query,
            role=role,
            top_k=top_k * 2,
        )

        return apply_filters(
            retry_results,
            min_score=min_score,
            dedup=True,
            limit=top_k,
        )

    @staticmethod
    def _clean_metadata_result(result: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize one vector result into a clean RAG chunk."""

        text = result.get("text")

        if not isinstance(text, str) or not text.strip():
            return None

        return {
            "text": text.strip(),
            "score": result.get("score"),
            "document_id": result.get("document_id"),
            "chunk_id": result.get("chunk_id"),
            "role": result.get("role"),
        }

    def retrieve_chunks_with_metadata(
        self,
        query: str,
        role: str = "employee",
        top_k: int = 5,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks with metadata for RAG answer generation.
        """

        if not query.strip():
            logger.warning("Empty query received for retrieval.")
            return []

        min_score = settings.min_retrieval_score if min_score is None else min_score

        filtered_results = self._get_filtered_results(
            query=query,
            role=role,
            top_k=top_k,
            min_score=min_score,
        )

        cleaned = [
            cleaned_result
            for result in filtered_results
            if (cleaned_result := self._clean_metadata_result(result)) is not None
        ]

        logger.debug(
            "Final metadata chunks prepared | count=%d | role=%s",
            len(cleaned),
            role,
        )

        return cleaned

    def retrieve_chunks(
        self,
        query: str,
        role: str = "employee",
        top_k: int = 5,
        min_score: float | None = None,
    ) -> list[str]:
        """
        Retrieve clean text chunks only, ready to be used as LLM context.
        """

        chunks_with_metadata = self.retrieve_chunks_with_metadata(
            query=query,
            role=role,
            top_k=top_k,
            min_score=min_score,
        )

        chunks = [chunk["text"] for chunk in chunks_with_metadata]

        logger.debug("Final text chunks prepared | count=%d", len(chunks))

        return chunks
