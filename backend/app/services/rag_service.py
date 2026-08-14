from app.core.config import get_settings
from app.schemas.chat import ChatResponse, ChatTurn, SourceChunk
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
1. Base your factual answer only on the CONTEXT. Do not use outside knowledge, do not guess, and do not invent prices, hours, policies, or services that aren't explicitly stated there.
2. If the CONTEXT doesn't fully answer the question, say so honestly and suggest the customer contact the business directly — never make something up to fill the gap.
3. Use RECENT CONVERSATION only to understand what the customer is referring to (e.g. "that", "it", "the same one"). Never treat a prior assistant answer as a source of fact by itself — always ground the actual answer in CONTEXT.
4. Keep answers concise, warm, and professional — a few sentences, or a short list if the question calls for one.
5. Never mention "context", "documents", "chunks", "conversation history", or any other internal system detail. Speak naturally, the way front-desk staff would.
6. If the question is entirely unrelated to {business_name}'s services (general knowledge, coding help, other businesses, etc.), politely decline and redirect the customer to ask about {business_name} instead.

Note : Currency INR (Indian Rupees)



RECENT CONVERSATION (oldest first, may be empty):
{history}

CONTEXT:
{context}
"""


class RAGService:
    def __init__(self, vector_store: VectorStoreService | None = None) -> None:
        self.vector_store = vector_store or get_vector_store()

    # History handling

    def _trim_history(self, history: list[ChatTurn]) -> list[ChatTurn]:
        """Keep only the last N exchanges (user+assistant pairs), server-side."""
        max_messages = settings.max_history_exchanges * 2
        return history[-max_messages:] if history else []

    def _format_history(self, history: list[ChatTurn]) -> str:
        if not history:
            return "(no prior messages)"
        speaker = {"user": "Customer", "assistant": "Assistant"}
        return "\n".join(f"{speaker[turn.role]}: {turn.content}" for turn in history)

    def _build_search_query(self, question: str, history: list[ChatTurn]) -> str:
        if not history:
            return question

        recent_user_turns = [turn.content for turn in history if turn.role == "user"]
        if not recent_user_turns:
            return question

        context_snippet = " ".join(recent_user_turns[-2:])
        return f"{context_snippet} {question}".strip()

    # Retrieval

    def retrieve_context(self, search_query: str, top_k: int | None = None) -> list[SourceChunk]:
        """Hybrid vector+keyword search — see VectorStoreService.search."""
        hits = self.vector_store.search(search_query, top_k=top_k)
        return [
            SourceChunk(content=hit["text"], source=hit["source"], score=hit["score"])
            for hit in hits
        ]

    # Out-of-domain filtering 

    def _is_out_of_domain(self, context: list[SourceChunk]) -> bool:
        if not context:
            return True
        best_score = max((chunk.score or 0.0) for chunk in context)
        return best_score < settings.relevance_score_threshold

    def generate_answer(
        self, question: str, context: list[SourceChunk], history: list[ChatTurn]
    ) -> str:
        llm = get_llm_service()

        context_block = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.content}" for chunk in context
        )
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=settings.business_name,
            business_description=settings.business_description,
            history=self._format_history(history),
            context=context_block,
        )
        return llm.generate(system_prompt=system_prompt, user_prompt=question)

    def answer_question(
        self,
        question: str,
        session_id: str | None = None,
        history: list[ChatTurn] | None = None,
    ) -> ChatResponse:
        history = self._trim_history(history or [])

        search_query = self._build_search_query(question, history)
        context = self.retrieve_context(search_query)

        if self._is_out_of_domain(context):
            return ChatResponse(
                answer=OUT_OF_DOMAIN_MESSAGE.format(business_name=settings.business_name),
                sources=[],
                session_id=session_id,
            )

        answer = self.generate_answer(question, context, history)
        return ChatResponse(answer=answer, sources=context, session_id=session_id)