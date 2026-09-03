import logging
import re
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.document_chunk import DocumentChunk
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


def _tokenize(text_value: str) -> set[str]:
    tokens = _TOKEN_PATTERN.findall(text_value.lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _keyword_overlap_score(query_terms: set[str], text_value: str) -> float:
    if not query_terms:
        return 0.0
    chunk_terms = _tokenize(text_value)
    matched = query_terms & chunk_terms
    return len(matched) / len(query_terms)


class VectorStoreService:

    def __init__(self) -> None:
        self.embedder = get_embedding_service()
        self._extension_checked = False

    @contextmanager
    def _session(self) -> Iterator[Session]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def ensure_collection(self) -> None:
        if self._extension_checked:
            return
        with self._session() as db:
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.commit()
        self._extension_checked = True

    def upsert_document_chunks(
        self,
        document_id: str,
        chunks: list[str],
        source_filename: str,
        version: int,
        batch_size: int | None = None,
    ) -> int:
        self.ensure_collection()
        batch_size = batch_size or settings.embedding_batch_size

        total_written = 0
        with self._session() as db:
            for batch_start in range(0, len(chunks), batch_size):
                batch = chunks[batch_start : batch_start + batch_size]
                vectors = self.embedder.embed_batch(batch)

                rows = [
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=batch_start + i,
                        text=chunk,
                        source=source_filename,
                        version=version,
                        embedding=vector,
                    )
                    for i, (chunk, vector) in enumerate(zip(batch, vectors))
                ]
                db.add_all(rows)
                db.commit()
                total_written += len(rows)

        logger.info("Upserted %d chunks for document_id=%s", total_written, document_id)
        return total_written

    def delete_by_document_id(self, document_id: str) -> None:
        self.ensure_collection()
        with self._session() as db:
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            db.commit()
        logger.info("Deleted existing vectors for document_id=%s", document_id)

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        self.ensure_collection()
        top_k = top_k or settings.retrieval_top_k
        candidate_limit = max(top_k * settings.retrieval_candidate_multiplier, top_k)

        query_vector = self.embedder.embed_text(query)
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        with self._session() as db:
            stmt = (
                select(DocumentChunk, distance)
                .order_by(distance)
                .limit(candidate_limit)
            )
            rows = db.execute(stmt).all()

            query_terms = _tokenize(query)
            weight = settings.keyword_boost_weight

            scored = []
            for chunk, cos_distance in rows:
                similarity = 1 - float(cos_distance)  # cosine distance -> cosine similarity
                keyword_score = _keyword_overlap_score(query_terms, chunk.text)
                combined_score = ((1 - weight) * similarity) + (weight * keyword_score)
                scored.append(
                    {
                        "text": chunk.text,
                        "source": chunk.source,
                        "document_id": chunk.document_id,
                        "score": similarity,  # comparable to the old cosine score
                        "combined_score": combined_score,
                    }
                )

        scored.sort(key=lambda item: item["combined_score"], reverse=True)
        return scored[:top_k]


@lru_cache
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()