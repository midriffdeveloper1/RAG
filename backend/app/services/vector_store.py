import logging
import re
import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)
settings = get_settings()

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "by", "can", "do", "does", "for",
    "how", "i", "if", "in", "is", "it", "of", "on", "or", "our", "the",
    "to", "we", "what", "when", "where", "which", "who", "why", "will",
    "with", "you", "your",
}


def _tokenize(text: str) -> set[str]:
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _keyword_overlap_score(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0
    chunk_terms = _tokenize(text)
    matched = query_terms & chunk_terms
    return len(matched) / len(query_terms)


class VectorStoreService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = settings.qdrant_collection_name
        self.embedder = get_embedding_service()


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


    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        self.ensure_collection()
        top_k = top_k or settings.retrieval_top_k
        candidate_limit = max(top_k * settings.retrieval_candidate_multiplier, top_k)

        query_vector = self.embedder.embed_text(query)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=candidate_limit,
        )

        query_terms = _tokenize(query)
        weight = settings.keyword_boost_weight

        scored = []
        for hit in results:
            text = hit.payload.get("text", "")
            keyword_score = _keyword_overlap_score(query_terms, text)
            combined_score = ((1 - weight) * hit.score) + (weight * keyword_score)
            scored.append(
                {
                    "text": text,
                    "source": hit.payload.get("source"),
                    "document_id": hit.payload.get("document_id"),
                    "score": hit.score,  # raw cosine — used for the out-of-domain gate
                    "combined_score": combined_score,
                }
            )

        scored.sort(key=lambda item: item["combined_score"], reverse=True)
        # print(scored[:top_k])
        return scored[:top_k]


@lru_cache
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()