from app.schemas.chat import ChatResponse
from app.services.vector_store import VectorStoreService

class RAGService:
    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or VectorStoreService()

    def answer_question(self, question: str, session_id: str | None = None) -> ChatResponse:
        """TODO: retrieval + generation pipeline."""
        raise NotImplementedError
