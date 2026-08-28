import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.models.customer import Customer
from app.schemas.chat import ChatResponse, ChatTurn
from app.services.agents.booking_agent import BookingAgent
from app.services.agents.knowledge_agent import KnowledgeAgent
from app.services.agents.support_agent import SupportAgent

_BOOKING_KEYWORDS = {
    "book", "booking", "bookings", "appointment", "appointments", "reschedule",
    "rescheduling", "cancel", "cancelling", "cancellation", "slot", "slots",
    "available", "availability", "schedule", "scheduling", "reserve",
    "reservation", "rebook", "rebooking",
}
_KNOWLEDGE_KEYWORDS = {
    "price", "prices", "pricing", "cost", "costs", "hour", "hours", "open",
    "opens", "opening", "close", "closes", "closed", "closing", "policy",
    "policies", "faq", "faqs", "location", "address", "phone", "contact",
    "holiday", "holidays", "service", "services", "about", "who",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


class OrchestratorService:

    def __init__(
        self, db: Session, browser_id: str | None = None, customer: Customer | None = None
    ) -> None:
        self.db = db
        self.browser_id = browser_id
        self.customer = customer
        self.support = SupportAgent()

    def preview_system_prompt(self) -> str:
        return BookingAgent(self.db, self.browser_id, self.customer).system_prompt()

    def _classify_intent(self, question: str, history: list[ChatTurn]) -> str:
        tokens = _tokenize(question)
        booking_score = len(tokens & _BOOKING_KEYWORDS)
        knowledge_score = len(tokens & _KNOWLEDGE_KEYWORDS)
        if booking_score > knowledge_score:
            return "booking"
        if knowledge_score > booking_score:
            return "knowledge"
        for turn in reversed(history[-4:]):
            turn_tokens = _tokenize(turn.content)
            if turn_tokens & _BOOKING_KEYWORDS:
                return "booking"
            if turn_tokens & _KNOWLEDGE_KEYWORDS:
                return "knowledge"

        return "knowledge"

    def answer(self, question: str, session: ChatSession, history: list[ChatTurn]) -> ChatResponse:
        
        reason = self.support.check_message(question) or self.support.check_streak(session)
        if reason:
            session.needs_human = True
            session.escalation_reason = reason
            session.escalated_at = datetime.utcnow()
            self.db.commit()
            return ChatResponse(
                answer=self.support.handoff_reply(),
                sources=[],
                session_id=session.id,
                needs_human=True,
                agent="support",
            )

        intent = self._classify_intent(question, history)
        history_dicts = [{"role": t.role, "content": t.content} for t in history]

        if intent == "booking":
            agent = BookingAgent(self.db, browser_id=self.browser_id, customer=self.customer)
        else:
            agent = KnowledgeAgent(self.db, customer=self.customer)

        reply = agent.handle(question, history_dicts)

        session.unresolved_streak = 0 if reply.resolved else session.unresolved_streak + 1
        self.db.commit()

        return ChatResponse(
            answer=reply.answer,
            sources=[],
            session_id=session.id,
            needs_human=False,
            agent=reply.agent,
        )