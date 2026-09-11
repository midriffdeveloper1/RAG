from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.services.chat_session_service import ChatSessionService
from app.services.customer_service import CustomerService


class PhoneCallSessionService:
    """Telephony equivalent of VoiceSessionService (browser calls) — maps
    an inbound phone call to a ChatSession so it shows up in the same admin
    Conversations view, reuses the same escalation/ticketing, etc. Calls are
    keyed by the caller's phone number instead of a browser_id."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = ChatSessionService(db)
        self.customers = CustomerService(db)

    @staticmethod
    def browser_id_for_phone(phone: str) -> str:
        digits = "".join(ch for ch in phone if ch.isdigit())
        return f"phone:{digits}"[:36]

    def start_call(self, caller_phone: str, call_sid: str) -> tuple[ChatSession, str]:
        browser_id = self.browser_id_for_phone(caller_phone)
        session = self.sessions.get_or_create(browser_id, None)
        session.channel = "voice"
        session.voice_session_id = call_sid

        # Unlike browser voice (which needs the caller to type/say an
        # email), a phone call carries real Caller ID — if it matches a
        # customer already on file, skip onboarding entirely.
        if session.customer_id is None:
            existing = self.customers.get_by_phone(caller_phone)
            if existing is not None:
                session.customer_id = existing.id

        self.db.commit()
        return session, browser_id

    def end_call(self, session: ChatSession) -> None:
        session.voice_session_id = None
        self.db.commit()
