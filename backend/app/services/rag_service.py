from app.schemas.chat import ChatResponse, SourceChunk
from app.services.vector_store import VectorStoreService, get_vector_store


class RAGService:
    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    def retrieve_context(self, question: str, top_k: int = 5) -> list[SourceChunk]:
        """Return the top_k most relevant chunks for a question. Fully implemented."""
        hits = self.vector_store.search(question, top_k=top_k)
        return [
            SourceChunk(content=hit["text"], source=hit["source"], score=hit["score"])
            for hit in hits
        ]

    def generate_answer(self, question: str, context: list[SourceChunk]) -> str:
        """
        TODO (Phase 2): build a prompt from `context` + `question` and call
        an LLM (Anthropic/OpenAI/etc.) to produce a grounded answer.

        Sketch:
            context_block = "\\n\\n".join(f"[{c.source}] {c.content}" for c in context)
            prompt = SYSTEM_PROMPT.format(context=context_block, question=question)
            response = llm_client.messages.create(...)
            return response.content
        """
        raise NotImplementedError(
            "Answer generation isn't implemented yet — see docs/RAG_PIPELINE.md Phase 2."
        )

    def answer_question(self, question: str, session_id: str | None = None) -> ChatResponse:
        """Full pipeline: retrieve then generate. Blocked on generate_answer()."""
        context = self.retrieve_context(question)
        answer = self.generate_answer(question, context)  # raises until Phase 2 is built
        return ChatResponse(answer=answer, sources=context, session_id=session_id)