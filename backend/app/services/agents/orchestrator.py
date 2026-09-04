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
from app.services.business_lookup_service import BusinessLookupService
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

_TURN_CLASSIFIER_SYSTEM_PROMPT = """Routing classifier for a salon assistant. Given the latest customer message (with context), output JSON:
{"escalate": true|false, "intent": "booking"|"knowledge"}
escalate=true only if they clearly ask for a human/manager/ticket, or show real anger/frustration (not mild "no"). intent="booking" for availability/booking/reschedule/cancel/their own appointment; else "knowledge". Fill intent either way. JSON only."""

_HUMANIZE_SYSTEM_PROMPT = """You're {business_name}'s front-desk assistant, texting a customer. Reword the given fact briefly and naturally, like a real person would — no markdown tables, no internal jargon. If it's a repetitive pattern (e.g. the same hours across several days), summarize it in one sentence instead of listing each day. If it's a list of distinct items (e.g. services with prices, staff names), keep it as a short clean list — don't compress away the actual items customers need to choose from. Never add/remove/change facts. Vary phrasing. Don't mention "the database" or that you're rephrasing."""

_CONTACT_EXTRACTION_SYSTEM_PROMPT = """Extract name and phone from the message, if present. JSON only: {"name": "<name or null>", "phone": "<phone or null>"}. Use null for anything not clearly stated — never guess."""

_PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s().]{7,14}\d")
_NAME_STRIP_PATTERN = re.compile(
    r"\b(my name'?s|my name is|i'?m|this is|call me|you can call me|name is|"
    r"phone( number)? is|number is|reach me at|contact me at|and|is|the|at)\b",
    re.IGNORECASE,
)

MAX_CONTACT_INFO_ATTEMPTS = 2

_CONTACT_HINT_PATTERN = re.compile(
    r"\b(my name'?s|my name is|i'?m|this is|call me|you can call me|"
    r"my number is|my phone( number)? is|contact me at|reach me at)\b"
    r"|\+?\d[\d\s\-().]{7,}\d"
)

_NEEDS_LLM_REVIEW_PATTERN = re.compile(
    r"[!?]{2,}|\b(no+t?|why not|ugh+|hate|angry|annoyed|frustrat\w*|shit|"
    r"stupid|idiot|useless|garbage|nonsense|rubbish|dumb|terrible|awful|"
    r"worst|connect|ticket|human|person|manager|supervisor)\b",
    re.IGNORECASE,
)


def _fast_route_intent(question: str) -> str | None:
    if _NEEDS_LLM_REVIEW_PATTERN.search(question):
        return None
    tokens = _tokenize(question)
    booking_score = len(tokens & _BOOKING_KEYWORDS)
    knowledge_score = len(tokens & _KNOWLEDGE_KEYWORDS)
    if booking_score >= 1 and booking_score > knowledge_score:
        return "booking"
    if knowledge_score >= 1 and knowledge_score > booking_score:
        return "knowledge"
    return None


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def _regex_extract_contact_info(message: str) -> tuple[str | None, str | None]:
    phone = None
    remainder = message
    match = _PHONE_PATTERN.search(message)
    if match:
        digit_count = sum(c.isdigit() for c in match.group(0))
        if 7 <= digit_count <= 15:
            phone = match.group(0).strip()
            remainder = (message[: match.start()] + " " + message[match.end() :]).strip()

    cleaned = _NAME_STRIP_PATTERN.sub(" ", remainder)
    cleaned = re.sub(r"[,:;.\-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    name = None
    if cleaned and 1 <= len(cleaned.split()) <= 4 and re.fullmatch(r"[A-Za-z][A-Za-z '.-]*", cleaned):
        name = cleaned.title()

    return name, phone


def _looks_complete(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", '"', "'", ")", "]", ":"))


def _salvage_incomplete(text: str) -> str | None:
    for cutoff in (". ", "! ", "? "):
        idx = text.rfind(cutoff)
        if idx != -1:
            return text[: idx + 1].strip()
    return None


def _classify_intent_keywords(question: str, history: list[ChatTurn]) -> str:
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
    
    def __init__(
        self,
        db: Session,
        browser_id: str | None = None,
        customer: Customer | None = None,
        channel: str = "chat",
    ) -> None:
        self.db = db
        self.browser_id = browser_id
        self.customer = customer
        self.channel = channel
        self.support = SupportAgent()
        self.llm = get_llm_service()

    def preview_system_prompt(self) -> str:
       return BookingAgent(self.db, self.browser_id, self.customer).system_prompt()

    def _classify_turn(self, question: str, history: list[ChatTurn]) -> tuple[bool, str]:
        context_lines = [f"{turn.role}: {turn.content}" for turn in history[-6:]]
        context = "\n".join(context_lines)
        user_prompt = (
            f"Conversation so far:\n{context}\n\nLatest message: {question}"
            if context
            else f"Latest message: {question}"
        )
        try:
            data = self.llm.generate_json(_TURN_CLASSIFIER_SYSTEM_PROMPT, user_prompt, max_tokens=300, temperature=0)
            print("*"*50)
            print(data)
            print("*"*50)
            escalate = bool(data.get("escalate"))
            intent = data.get("intent")
            if intent not in ("booking", "knowledge"):
                intent = _classify_intent_keywords(question, history)
                print("*"*50)
                print(intent)
                print("*"*50)
                
            return escalate, intent
        except Exception:
            logger.exception("LLM turn classification failed; falling back to keyword routing")
            return False, _classify_intent_keywords(question, history)

    def _extract_contact_info(self, message: str) -> tuple[str | None, str | None]:
        name, phone = _regex_extract_contact_info(message)
        if name and phone:
            return name, phone

        try:
            data = self.llm.generate_json(_CONTACT_EXTRACTION_SYSTEM_PROMPT, message, max_tokens=150, temperature=0)

            def _clean(value):
                if not isinstance(value, str):
                    return None
                value = value.strip()
                return value if value and value.lower() not in {"null", "none"} else None

            name = name or _clean(data.get("name"))
            phone = phone or _clean(data.get("phone"))
        except Exception:  # noqa: BLE001 - extraction is best-effort
            logger.exception("Contact-info LLM extraction failed; relying on regex pass only")

        return name, phone

    def _missing_contact_fields(self) -> list[str]:
        missing = []
        if not self.customer or not (self.customer.name or "").strip():
            missing.append("name")
        if not self.customer or not (self.customer.phone or "").strip():
            missing.append("phone")
        return missing

    def _maybe_capture_contact_info(self, question: str) -> None:
        if self.customer is None:
            return
        if not self._missing_contact_fields():
            return
        if not _CONTACT_HINT_PATTERN.search(question.lower()):
            return

        name, phone = self._extract_contact_info(question)
        changed = False
        if name and not (self.customer.name or "").strip():
            self.customer.name = name
            changed = True
        if phone and not (self.customer.phone or "").strip():
            self.customer.phone = phone
            changed = True
        if changed:
            self.db.commit()

    # --- Escalation / ticket flow ---

    def _handle_already_escalated(
        self, question: str, session: ChatSession, tickets: SupportTicketService
    ) -> ChatResponse:
        reply = (
            f"Thank you for your message. Your ticket {session.ticket_number} has already been "
            "raised, and our support team will review this chat shortly. If you have another "
            "question in the meantime, please feel free to start a new chat \u2014 thank you for "
            "your patience!"
        )
        ticket = tickets.get_by_ticket_number(session.ticket_number)
        if ticket is not None:
            tickets.append_message(ticket, "user", question)
            tickets.append_message(ticket, "assistant", reply, agent="support")
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
                sessions.append_message(session, "assistant", message, agent="support", channel=self.channel, message_type="assistant_text")
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
                self.db.commit()
                return self._finalize_escalation(
                    session.escalation_reason or "Customer requested human assistance.",
                    session, sessions, tickets, persist,
                )
            self.db.commit()
            ask = " and ".join(missing)
            message = f"Thanks \u2014 I still need your {ask} so our team can follow up. Could you share that?"
            if persist:
                sessions.append_message(session, "assistant", message, agent="support", channel=self.channel, message_type="assistant_text")
            return ChatResponse(
                answer=message, sources=[], session_id=session.id, needs_human=False, agent="support",
            )

        return self._finalize_escalation(
            session.escalation_reason or "Customer requested human assistance.",
            session, sessions, tickets, persist,
        )

    # --- Main entry point ---

    def _try_fast_knowledge_answer(self, question: str) -> str | None:
        from app.models.knowledge_base import Business

        business = self.db.query(Business).first()
        if business is None:
            return None
        return BusinessLookupService(self.db).answer(business, question)

    def _humanize_fast_answer(self, raw_answer: str) -> str:
        from app.models.knowledge_base import Business

        business = self.db.query(Business).first()
        business_name = (business.name if business and business.name else None) or "the business"
        system_prompt = _HUMANIZE_SYSTEM_PROMPT.format(business_name=business_name)
        if self.channel == "voice":
            system_prompt += (
                " This is a live VOICE call, not text: keep it to 1 short sentence, like a "
                "quick spoken reply — mention at most 2-3 items if it's a list, then ask what "
                "they're most interested in rather than reading everything."
            )
        try:
            rephrased = self.llm.generate(system_prompt, raw_answer, max_tokens=220, temperature=0.7)
            rephrased = (rephrased or "").strip()
            if rephrased and _looks_complete(rephrased):
                return rephrased
            if rephrased:
                salvaged = _salvage_incomplete(rephrased)
                if salvaged:
                    logger.warning("Humanized answer was truncated; salvaged to last full sentence")
                    return salvaged
                logger.warning("Humanized answer looked truncated with no salvageable sentence, using raw database text: %r", rephrased)
        except Exception:
            logger.exception("Fast-path answer humanization failed; using raw database text")
        return raw_answer

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
        intent = None
        if not reason:
            intent = _fast_route_intent(question)

        if not reason and intent is None:
            escalate, intent = self._classify_turn(question, history)
            if escalate:
                reason = "Customer indicated they want a human, or showed clear frustration (LLM-detected)."

        if not reason and intent == "knowledge":
            fast_answer = self._try_fast_knowledge_answer(question)
            if fast_answer:
                fast_answer = self._humanize_fast_answer(fast_answer)
                self._maybe_capture_contact_info(question)
                session.unresolved_streak = 0
                self.db.commit()
                if persist:
                    sessions.append_message(session, "assistant", fast_answer, agent="knowledge", channel=self.channel, message_type="assistant_text")
                return ChatResponse(
                    answer=fast_answer, sources=[], session_id=session.id, needs_human=False, agent="knowledge",
                )

        if reason:
            return self._start_escalation(reason, session, sessions, tickets, persist)

        # Route to the responsible agent.
        self._maybe_capture_contact_info(question)
        history_dicts = [{"role": t.role, "content": t.content} for t in history]

        if intent == "booking":
            agent = BookingAgent(self.db, browser_id=self.browser_id, customer=self.customer, channel=self.channel)
        else:
            agent = KnowledgeAgent(self.db, customer=self.customer, channel=self.channel)

        reply = agent.handle(question, history_dicts)

        session.unresolved_streak = 0 if reply.resolved else session.unresolved_streak + 1
        self.db.commit()

        if persist:
            sessions.append_message(session, "assistant", reply.answer, agent=reply.agent, channel=self.channel, message_type="assistant_text")

        return ChatResponse(
            answer=reply.answer, sources=[], session_id=session.id, needs_human=False, agent=reply.agent,
        )