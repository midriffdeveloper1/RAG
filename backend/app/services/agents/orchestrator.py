import json
import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.chat_session import ChatMessage, ChatSession
from app.models.customer import Customer
from app.schemas.chat import ChatResponse, ChatTurn
from app.services.agents.booking_agent import BookingAgent
from app.services.agents.knowledge_agent import KnowledgeAgent
from app.services.agents.support_agent import SupportAgent
from app.services.chat_session_service import ChatSessionService
from app.services.llm_service import get_llm_service
from app.services.support_ticket_service import SupportTicketService

logger = logging.getLogger(__name__)

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

_INTENT_SYSTEM_PROMPT = """You are a routing classifier in front of a salon's chat assistant. Decide which specialist should handle the customer's LATEST message, using the conversation for context.

- booking: checking availability, booking, rescheduling, cancelling an appointment, or anything about their own appointment/profile (including short follow-ups like confirming a time or giving their name/phone mid-booking).
- knowledge: questions about the business itself — services, pricing, hours, holidays/closures, policies, FAQs, location, contact details.

Reply with exactly one word, lowercase: booking or knowledge. Nothing else — no punctuation, no explanation."""

_CONTACT_EXTRACTION_SYSTEM_PROMPT = """Extract a customer's name and phone number from their message, if present.
Reply with EXACTLY this JSON shape and nothing else — no markdown, no explanation:
{"name": "<name or null>", "phone": "<phone or null>"}
Use JSON null (not the text "null") for anything not clearly stated. Do not guess — only extract what's explicitly given."""

MAX_CONTACT_INFO_ATTEMPTS = 2


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _classify_intent_keywords(question: str, history: list[ChatTurn]) -> str:
    """Fallback used only if the LLM classification call fails."""
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


class OrchestratorService:
    """Drop-in replacement for the old single-prompt AgentService — same
    public shape (`answer`, `preview_system_prompt`) so app/api/routes/chat.py
    barely has to change, but internally it's a router over three agents."""

    def __init__(
        self, db: Session, browser_id: str | None = None, customer: Customer | None = None
    ) -> None:
        self.db = db
        self.browser_id = browser_id
        self.customer = customer
        self.support = SupportAgent()
        self.llm = get_llm_service()

    def preview_system_prompt(self) -> str:
        """Used by the admin's "preview system prompt" screen. Shows the
        Booking Agent's prompt, since it's the most detailed of the two —
        the Knowledge Agent's prompt follows the same DB-first pattern."""
        return BookingAgent(self.db, self.browser_id, self.customer).system_prompt()

    # --- Intent routing ---

    def _classify_intent(self, question: str, history: list[ChatTurn]) -> str:
        context_lines = [f"{turn.role}: {turn.content}" for turn in history[-6:]]
        context = "\n".join(context_lines)
        user_prompt = (
            f"Conversation so far:\n{context}\n\nLatest message: {question}"
            if context
            else f"Latest message: {question}"
        )
        try:
            raw = self.llm.generate(_INTENT_SYSTEM_PROMPT, user_prompt, max_tokens=5, temperature=0)
            cleaned = (raw or "").strip().lower()
            if "booking" in cleaned:
                return "booking"
            if "knowledge" in cleaned:
                return "knowledge"
            logger.warning("Intent classifier returned unexpected output %r; falling back", raw)
        except Exception:  # noqa: BLE001 - never let routing crash the turn
            logger.exception("LLM intent classification failed; falling back to keyword routing")
        return _classify_intent_keywords(question, history)

    # --- Contact-info extraction (used only while gating an escalation) ---

    def _extract_contact_info(self, message: str) -> tuple[str | None, str | None]:
        try:
            raw = self.llm.generate(_CONTACT_EXTRACTION_SYSTEM_PROMPT, message, max_tokens=60, temperature=0)
            data = json.loads(raw)
        except Exception:  # noqa: BLE001 - extraction is best-effort
            logger.exception("Contact-info extraction failed")
            return None, None

        def _clean(value):
            if not isinstance(value, str):
                return None
            value = value.strip()
            return value if value and value.lower() not in {"null", "none"} else None

        return _clean(data.get("name")), _clean(data.get("phone"))

    def _missing_contact_fields(self) -> list[str]:
        missing = []
        if not self.customer or not (self.customer.name or "").strip():
            missing.append("name")
        if not self.customer or not (self.customer.phone or "").strip():
            missing.append("phone")
        return missing

    # --- Escalation / ticket flow ---

    def _handle_already_escalated(
        self, question: str, session: ChatSession, tickets: SupportTicketService
    ) -> ChatResponse:
        reply = (
            f"Your ticket {session.ticket_number} is already with our team \u2014 no need to keep "
            "chatting here, they'll follow up with you directly. Let me know if there's anything "
            "else I can help with while you wait."
        )
        ticket = tickets.get_by_ticket_number(session.ticket_number)
        if ticket is not None:
            tickets.append_message(ticket, "user", question)
            tickets.append_message(ticket, "assistant", reply, agent="support")
        # Whatever the route already wrote to chat_messages for this turn
        # (and anything stray from before) is now archived above — keep
        # the live table empty for ticketed sessions.
        self.db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
        session.updated_at = datetime.utcnow()
        self.db.commit()
        return ChatResponse(
            answer=reply, sources=[], session_id=session.id, needs_human=True, agent="support",
            ticket_number=session.ticket_number,
        )

    def _finalize_escalation(
        self, reason: str, session: ChatSession, sessions: ChatSessionService,
        tickets: SupportTicketService, persist: bool,
    ) -> ChatResponse:
        sessions.escalate(session, reason)
        handoff = self.support.handoff_reply(session.ticket_number)
        if persist:
            ticket = tickets.get_by_ticket_number(session.ticket_number)
            if ticket is not None:
                tickets.append_message(ticket, "assistant", handoff, agent="support")
        return ChatResponse(
            answer=handoff, sources=[], session_id=session.id, needs_human=True, agent="support",
            ticket_number=session.ticket_number,
        )

    def _start_escalation(
        self, reason: str, session: ChatSession, sessions: ChatSessionService,
        tickets: SupportTicketService, persist: bool,
    ) -> ChatResponse:
        missing = self._missing_contact_fields()
        if missing and self.customer is not None:
            session.awaiting_contact_info = True
            session.escalation_reason = reason
            self.db.commit()
            ask = " and ".join(missing)
            message = (
                f"Before I connect you with our team, could you share your {ask} so they can "
                "reach you directly?"
            )
            if persist:
                sessions.append_message(session, "assistant", message, agent="support")
            return ChatResponse(
                answer=message, sources=[], session_id=session.id, needs_human=False, agent="support",
            )
        return self._finalize_escalation(reason, session, sessions, tickets, persist)

    def _handle_pending_escalation(
        self, question: str, session: ChatSession, sessions: ChatSessionService,
        tickets: SupportTicketService, persist: bool,
    ) -> ChatResponse:
        name, phone = self._extract_contact_info(question)
        if self.customer is not None:
            changed = False
            if name and not (self.customer.name or "").strip():
                self.customer.name = name
                changed = True
            if phone and not (self.customer.phone or "").strip():
                self.customer.phone = phone
                changed = True
            if changed:
                self.db.commit()

        missing = self._missing_contact_fields()
        if missing:
            session.unresolved_streak += 1
            if session.unresolved_streak >= MAX_CONTACT_INFO_ATTEMPTS:
                # Don't loop forever asking — raise the ticket with whatever we have.
                self.db.commit()
                return self._finalize_escalation(
                    session.escalation_reason or "Customer requested human assistance.",
                    session, sessions, tickets, persist,
                )
            self.db.commit()
            ask = " and ".join(missing)
            message = f"Thanks \u2014 I still need your {ask} so our team can follow up. Could you share that?"
            if persist:
                sessions.append_message(session, "assistant", message, agent="support")
            return ChatResponse(
                answer=message, sources=[], session_id=session.id, needs_human=False, agent="support",
            )

        return self._finalize_escalation(
            session.escalation_reason or "Customer requested human assistance.",
            session, sessions, tickets, persist,
        )

    # --- Main entry point ---

    def answer(
        self, question: str, session: ChatSession, history: list[ChatTurn], persist: bool = True
    ) -> ChatResponse:
        sessions = ChatSessionService(self.db)
        tickets = SupportTicketService(self.db)

        if session.needs_human and session.ticket_number:
            return self._handle_already_escalated(question, session, tickets)

        if session.awaiting_contact_info:
            return self._handle_pending_escalation(question, session, sessions, tickets, persist)

        reason = self.support.check_message(question) or self.support.check_streak(session)
        if reason:
            return self._start_escalation(reason, session, sessions, tickets, persist)

        # Route to the responsible agent.
        intent = self._classify_intent(question, history)
        history_dicts = [{"role": t.role, "content": t.content} for t in history]

        if intent == "booking":
            agent = BookingAgent(self.db, browser_id=self.browser_id, customer=self.customer)
        else:
            agent = KnowledgeAgent(self.db, customer=self.customer)

        reply = agent.handle(question, history_dicts)

        session.unresolved_streak = 0 if reply.resolved else session.unresolved_streak + 1
        self.db.commit()

        if persist:
            sessions.append_message(session, "assistant", reply.answer, agent=reply.agent)

        return ChatResponse(
            answer=reply.answer, sources=[], session_id=session.id, needs_human=False, agent=reply.agent,
        )