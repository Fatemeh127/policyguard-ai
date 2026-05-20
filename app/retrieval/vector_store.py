"""Qdrant vector store operations."""

import logging
import uuid
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


class VectorStore:
    """Manages Qdrant vector database operations."""

    def __init__(self):
        """Initialize Qdrant client and ensure collection exists."""
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection_name
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info("Creating collection: %s", self.collection_name)
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                logger.info("Collection created successfully")
            else:
                logger.debug("Collection already exists: %s", self.collection_name)

        except Exception as exc:
            logger.exception("Failed to ensure collection exists")
            raise RuntimeError("Vector store initialization failed") from exc

    def add_documents(self, chunks: list[dict[str, Any]], document_id: str, role: str) -> int:
        """Add document chunks to vector store."""

        points = []

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
                logger.exception("Embedding failed for chunk: %s", chunk["text"][:50])

        if not points:
            logger.warning("No chunks embedded")
            return 0

        try:
            self.client.upsert(collection_name=self.collection_name, points=points)

            logger.info("Added %d chunks | document=%s", len(points), document_id)

            return len(points)

        except Exception as exc:
            logger.exception("Qdrant upsert failed")
            raise RuntimeError("Vector store insertion failed") from exc

    def search(
        self, query: str, role: str, limit: int = 5, document_ids: list[str] = None
    ) -> list[dict[str, Any]]:
        """Search for similar chunks with role + optional document filtering."""

        query_vector = get_embedding(query)

        try:
            # Build filters dynamically
            must_conditions = [FieldCondition(key="role", match=MatchValue(value=role))]

            if document_ids:
                must_conditions.append(
                    FieldCondition(key="document_id", match=MatchAny(any=document_ids))
                )

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                query_filter=Filter(must=must_conditions),
            )

            results = []
            for hit in search_result.points:
                results.append(
                    {
                        "document_id": hit.payload.get("document_id"),
                        "chunk_id": hit.payload.get("chunk_id"),
                        "text": hit.payload.get("text"),
                        "score": hit.score,
                        "role": hit.payload.get("role"),
                    }
                )

            logger.debug(
                "Search completed | role=%s | docs=%s | results=%d",
                role,
                document_ids,
                len(results),
            )

            return results

        except Exception as e:
            logger.exception("Vector search failed")
            raise RuntimeError("Vector store search failed") from e
