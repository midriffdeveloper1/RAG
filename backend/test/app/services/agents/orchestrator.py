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

_TURN_CLASSIFIER_SYSTEM_PROMPT = """You are a routing classifier in front of a salon's chat assistant. Look at the customer's LATEST message, using the conversation for context, and decide two things:

1. escalate — true if the customer is clearly asking to speak with a human/agent/manager/support, asking to "raise a ticket" or be "connected" to someone, or is expressing real frustration, anger, sarcasm, or insults directed at the assistant (not just a neutral "no" or mild disagreement). This should catch it regardless of exact phrasing, typos, or how it's worded — use your judgement the way a person reading the message would. False otherwise.
2. intent — "booking" (checking availability, booking, rescheduling, cancelling, or anything about their own appointment/profile) or "knowledge" (services, pricing, hours, holidays/closures, policies, FAQs, location, contact details). Only meaningful when escalate is false — still fill it in either way.

Reply with EXACTLY this JSON shape and nothing else — no markdown, no code fences, no explanation, just the raw JSON object on its own:
{"escalate": true or false, "intent": "booking" or "knowledge"}"""

_HUMANIZE_SYSTEM_PROMPT = """You're the front-desk assistant for {business_name}, replying to a customer in a live chat. You've been given a fact to convey — rephrase it briefly and naturally, the way a real person texting back would, not someone reading off a printout.

Rules:
- 1-2 short sentences for a simple fact. No markdown tables, no line-by-line charts — if the fact lists several similar items (e.g. hours that are the same most days), summarize the pattern in a sentence instead of listing each one.
- Never add, remove, or change any fact — only reword what's given, faithfully.
- Vary your phrasing — don't default to the same sentence structure every time.
- Don't mention that you're rephrasing anything, or reference "the database" — just answer naturally, as if you already knew this."""

_CONTACT_EXTRACTION_SYSTEM_PROMPT = """Extract a customer's name and phone number from their message, if present.

Reply with EXACTLY this JSON shape and nothing else — no markdown, no explanation:
{"name": "<name or null>", "phone": "<phone or null>"}
Use JSON null (not the text "null") for anything not clearly stated. Do not guess — only extract what's explicitly given."""

_PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s().]{7,14}\d")
_NAME_STRIP_PATTERN = re.compile(
    r"\b(my name'?s|my name is|i'?m|this is|call me|you can call me|name is|"
    r"phone( number)? is|number is|reach me at|contact me at|and|is|the|at)\b",
    re.IGNORECASE,
)
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

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


def _extract_json_object(raw: str) -> str:
    match = _JSON_OBJECT_PATTERN.search(raw)
    return match.group(0) if match else raw


def _looks_complete(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", '"', "'", ")", "]", ":"))


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
            raw = self.llm.generate(_TURN_CLASSIFIER_SYSTEM_PROMPT, user_prompt, max_tokens=40, temperature=0)
            data = json.loads(_extract_json_object(raw))
            escalate = bool(data.get("escalate"))
            intent = data.get("intent")
            if intent not in ("booking", "knowledge"):
                intent = _classify_intent_keywords(question, history)
            return escalate, intent
        except Exception:  
            logger.exception("LLM turn classification failed; falling back to keyword routing")
            return False, _classify_intent_keywords(question, history)

    def _extract_contact_info(self, message: str) -> tuple[str | None, str | None]:
        name, phone = _regex_extract_contact_info(message)
        if name and phone:
            return name, phone

        try:
            raw = self.llm.generate(_CONTACT_EXTRACTION_SYSTEM_PROMPT, message, max_tokens=60, temperature=0)
            data = json.loads(_extract_json_object(raw))

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
            f"Your ticket {session.ticket_number} is already with our team \u2014 no need to keep "
            "chatting here, they'll follow up with you directly. Let me know if there's anything "
            "else I can help with while you wait."
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
        try:
            rephrased = self.llm.generate(system_prompt, raw_answer, max_tokens=120, temperature=0.7)
            rephrased = (rephrased or "").strip()
            if rephrased and _looks_complete(rephrased):
                return rephrased
            if rephrased:
                logger.warning("Humanized answer looked truncated, using raw database text: %r", rephrased)
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
            agent = BookingAgent(self.db, browser_id=self.browser_id, customer=self.customer)
        else:
            agent = KnowledgeAgent(self.db, customer=self.customer)

        reply = agent.handle(question, history_dicts)

        session.unresolved_streak = 0 if reply.resolved else session.unresolved_streak + 1
        self.db.commit()

        if persist:
            sessions.append_message(session, "assistant", reply.answer, agent=reply.agent, channel=self.channel, message_type="assistant_text")

        return ChatResponse(
            answer=reply.answer, sources=[], session_id=session.id, needs_human=False, agent=reply.agent,
        )