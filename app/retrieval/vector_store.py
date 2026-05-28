"""Qdrant vector store operations."""

import logging
import uuid
from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.retrieval.embeddings import get_embedding

logger = logging.getLogger(__name__)


def _build_role_filter(role: str, document_ids: Sequence[str] | None) -> Filter:
    """Build a Qdrant filter for role and optional document scope."""

    must_conditions: list[Any] = [FieldCondition(key="role", match=MatchValue(value=role))]

    if document_ids:
        must_conditions.append(
            FieldCondition(
                key="document_id",
                match=MatchAny(any=list(document_ids)),
            )
        )

    return Filter(must=must_conditions)


def _hit_to_dict(hit: Any) -> dict[str, Any]:
    """Normalise a single Qdrant search hit into a clean result dict."""

    payload = hit.payload or {}

    return {
        "document_id": payload.get("document_id"),
        "chunk_id": payload.get("chunk_id"),
        "text": payload.get("text"),
        "score": hit.score,
        "role": payload.get("role"),
        "char_count": payload.get("char_count"),
    }


class VectorStore:
    """Manages Qdrant vector database operations."""

    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dim = settings.embedding_dim
        self._ensure_collection()

    # Collection setup

    def _ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info("Creating collection: %s", self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Collection created successfully.")
            else:
                logger.debug("Collection already exists: %s", self.collection_name)

        except Exception as exc:
            logger.exception("Failed to ensure collection exists.")
            raise RuntimeError("Vector store initialization failed") from exc

    # Insert documents

    def add_documents(
        self,
        chunks: list[dict[str, Any]],
        document_id: str,
        role: str,
    ) -> int:
        """
        Embed and upsert document chunks into the vector store.

        Returns the number of successfully upserted chunks.
        Raises RuntimeError if embedding succeeds for some chunks but upsert fails,
        or ValueError if chunks is empty.
        """

        if not chunks:
            raise ValueError(f"No chunks provided for document: {document_id}")

        points: list[PointStruct] = []
        failed = 0

        for i, chunk in enumerate(chunks):
            try:
                embedding = get_embedding(chunk["text"])

                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "document_id": document_id,
                            "chunk_id": chunk.get("chunk_id", i),
                            "role": role,
                            "text": chunk["text"],
                            "char_count": len(chunk["text"]),
                        },
                    )
                )

            except Exception:
                failed += 1
                logger.exception(
                    "Embedding failed for chunk %d/%d | document=%s | preview=%r",
                    i + 1,
                    len(chunks),
                    document_id,
                    chunk["text"][:50],
                )

        if not points:
            raise RuntimeError(f"All {failed} chunk(s) failed to embed for document: {document_id}")

        if failed:
            logger.warning(
                "%d/%d chunk(s) failed to embed and were skipped | document=%s",
                failed,
                len(chunks),
                document_id,
            )

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(
                "Upserted %d/%d chunk(s) | document=%s",
                len(points),
                len(chunks),
                document_id,
            )

            return len(points)

        except Exception as exc:
            logger.exception("Qdrant upsert failed | document=%s", document_id)
            raise RuntimeError("Vector store insertion failed") from exc

    # Search

    def search(
        self,
        query: str,
        role: str,
        limit: int = 5,
        document_ids: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for the most relevant chunks for a query.

        Raises RuntimeError on embedding or Qdrant failure.
        """

        try:
            query_vector = get_embedding(query)

        except Exception as exc:
            logger.exception("Embedding failed for search query | role=%s", role)
            raise RuntimeError("Query embedding failed") from exc

        try:
            query_filter = _build_role_filter(role, document_ids)

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
            )

            results = [_hit_to_dict(hit) for hit in search_result.points]

            logger.debug(
                "Search completed | role=%s | scoped_to_docs=%s | results=%d",
                role,
                len(document_ids) if document_ids else "all",
                len(results),
            )

            return results

        except RuntimeError:
            raise

        except Exception as exc:
            logger.exception("Vector search failed | role=%s", role)
            raise RuntimeError("Vector store search failed") from exc
