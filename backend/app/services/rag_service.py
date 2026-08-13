from app.core.config import get_settings
from app.schemas.chat import ChatResponse, SourceChunk
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService, get_vector_store

settings = get_settings()

OUT_OF_DOMAIN_MESSAGE = (
    "I'm sorry, that's outside what I can help with here — I can only answer "
    "questions about {business_name}'s services, pricing, hours, and policies. "
    "Feel free to ask me about those, or reach out to us directly for anything else."
)

SYSTEM_PROMPT_TEMPLATE = """You are the customer support assistant for {business_name}, a {business_description}.

Answer the customer's question using ONLY the information in the CONTEXT below. Follow these rules strictly:
1. Base your answer only on the CONTEXT. Do not use outside knowledge, do not guess, and do not invent prices, hours, policies, or services that aren't explicitly stated there.
2. If the CONTEXT doesn't fully answer the question, say so honestly and suggest the customer contact the business directly — never make something up to fill the gap.
3. Keep answers concise, warm, and professional — a few sentences, or a short list if the question calls for one.
4. Never mention "context", "documents", "chunks", or any other internal system detail. Speak naturally, the way front-desk staff would.
5. If the question is entirely unrelated to {business_name}'s services (general knowledge, coding help, other businesses, etc.), politely decline and redirect the customer to ask about {business_name} instead.

CONTEXT:
{context}
"""


class RAGService:
    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    # --- Retrieval (implemented since Phase 1) -----------------------------

    def retrieve_context(self, question: str, top_k: int | None = None) -> list[SourceChunk]:
        """Return the top_k most relevant chunks for a question, with scores."""
        top_k = top_k or settings.retrieval_top_k
        hits = self.vector_store.search(question, top_k=top_k)
        return [
            SourceChunk(content=hit["text"], source=hit["source"], score=hit["score"])
            for hit in hits
        ]

    # --- Out-of-domain filtering -------------------------------------------

    def _is_out_of_domain(self, context: list[SourceChunk]) -> bool:
        """
        No retrieved chunks, or a best match below the relevance
        threshold, means the question likely isn't covered by anything
        that's been uploaded — treat it as out-of-domain instead of
        letting the LLM improvise from weak/irrelevant context.
        """
        if not context:
            return True
        best_score = max((chunk.score or 0.0) for chunk in context)
        return best_score < settings.relevance_score_threshold

    # --- Generation (Phase 2) -----------------------------------------------

    def generate_answer(self, question: str, context: list[SourceChunk]) -> str:
        """Build a grounded prompt from retrieved chunks and call Groq."""
        llm = get_llm_service()

        context_block = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.content}" for chunk in context
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=settings.business_name,
            business_description=settings.business_description,
            context=context_block,
        )
        return llm.generate(system_prompt=system_prompt, user_prompt=question)

    # --- Full pipeline -----------------------------------------------------

    def answer_question(self, question: str, session_id: str | None = None) -> ChatResponse:
        context = self.retrieve_context(question)

        if self._is_out_of_domain(context):
            return ChatResponse(
                answer=OUT_OF_DOMAIN_MESSAGE.format(business_name=settings.business_name),
                sources=[],
                session_id=session_id,
            )

        answer = self.generate_answer(question, context)
        return ChatResponse(answer=answer, sources=context, session_id=session_id)