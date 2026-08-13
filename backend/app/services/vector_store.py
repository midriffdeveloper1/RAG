

import logging
import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = settings.qdrant_collection_name
        self.embedder = get_embedding_service()

    # --- Collection lifecycle -------------------------------------------------

    def ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
            return

        logger.info("Creating Qdrant collection: %s", self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )
        # Index document_id so filtered delete (reindex/delete) is fast.
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.INTEGER,
        )

    # --- Ingestion --------------------------------------------------------

    def upsert_document_chunks(
        self,
        document_id: int,
        chunks: list[str],
        source_filename: str,
        version: int,
        batch_size: int | None = None,
    ) -> int:
        self.ensure_collection()
        batch_size = batch_size or settings.embedding_batch_size

        total_written = 0
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            vectors = self.embedder.embed_batch(batch)

            points = [
                qmodels.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "chunk_index": batch_start + i,
                        "text": chunk,
                        "source": source_filename,
                        "version": version,
                    },
                )
                for i, (chunk, vector) in enumerate(zip(batch, vectors))
            ]

            self.client.upsert(collection_name=self.collection_name, points=points)
            total_written += len(points)

        logger.info("Upserted %d chunks for document_id=%s", total_written, document_id)
        return total_written

    # --- Reindexing / memory management ------------------------------------

    def delete_by_document_id(self, document_id: int) -> None:
        self.ensure_collection()
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
        logger.info("Deleted existing vectors for document_id=%s", document_id)

    # --- Retrieval (used by Phase 2 RAG service) ---------------------------

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        self.ensure_collection()
        query_vector = self.embedder.embed_text(query)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
        return [
            {
                "text": hit.payload.get("text"),
                "source": hit.payload.get("source"),
                "document_id": hit.payload.get("document_id"),
                "score": hit.score,
            }
            for hit in results
        ]


@lru_cache
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()