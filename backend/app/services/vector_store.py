from typing import Any, List, Optional
from qdrant_client import QdrantClient
from app.core.config import get_settings
settings = get_settings()

class VectorStoreService:
    def __init__(self) -> None:
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )
        self.collection_name = settings.qdrant_collection_name

    def ensure_collection(self, vector_size: int = 1536) -> None:
        """TODO: create the collection if it doesn't already exist."""
        raise NotImplementedError

    def embed_text(self, text: str) -> List[float]:
        """TODO: call your embedding model of choice and return the vector."""
        raise NotImplementedError

    def upsert_documents(self, documents: List[dict[str, Any]]) -> None:
        """TODO: embed + upsert a batch of knowledge-base documents."""
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> List[dict[str, Any]]:
        """TODO: embed the query and return the top_k most relevant chunks."""
        raise NotImplementedError
