import logging

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.schemas.chat import ChatResponse
from app.services.agents.orchestrator import OrchestratorService
from app.services.chat_session_service import ChatSessionService
from app.services.customer_service import CustomerService
from app.services.onboarding_service import OnboardingService

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = ChatSessionService(db)

    def get_or_create_session(
        self, browser_id: str, session_id: str | None, channel: str = "chat"
    ) -> ChatSession:
        session = self.sessions.get_or_create(browser_id, session_id)
        if session_id is None:
            session.channel = channel
        return session

    def handle_turn(
        self,
        question: str,
        session: ChatSession,
        browser_id: str,
        customer_email: str | None = None,
        channel: str = "chat",
    ) -> ChatResponse:
        sessions = self.sessions

        if customer_email:
            current_email = session.customer.email if session.customer_id else None
            if current_email != customer_email.strip().lower():
                result = CustomerService(self.db).identify(customer_email)
                if "error" not in result:
                    session.customer_id = result["customer"]["id"]
                    self.db.commit()

        if session.customer_id is None:
            return self._handle_onboarding_turn(question, session, browser_id, channel)

        history = sessions.get_history(session.id, self._max_history_exchanges())
        sessions.append_message(session, "user", question, channel=channel, message_type=self._user_message_type(channel))

        orchestrator = OrchestratorService(
            self.db, browser_id=browser_id, customer=session.customer, channel=channel
        )
        response = orchestrator.answer(question, session, history)
        response.session_id = session.id
        return response

    # --- internals ---

    def _max_history_exchanges(self) -> int:
        from app.core.config import get_settings

        return get_settings().max_history_exchanges

    def _user_message_type(self, channel: str) -> str:
        return "voice_transcript" if channel == "voice" else "text"

    def _handle_onboarding_turn(
        self, question: str, session: ChatSession, browser_id: str, channel: str
    ) -> ChatResponse:
        from groq import GroqError

        sessions = self.sessions
        is_first_turn = not sessions.get_history(session.id, max_exchanges=1)
        onboarding = OnboardingService(self.db)
        result = onboarding.handle(question, session, browser_id, is_first_turn)
        self.db.commit()

        sessions.append_message(
            session, "user", question, channel=channel, message_type=self._user_message_type(channel)
        )

        answer = result.reply
        follow_up = None
        if result.identified and result.remainder and len(result.remainder) > 3:
            try:
                orchestrator = OrchestratorService(
                    self.db, browser_id=browser_id, customer=session.customer, channel=channel
                )
                follow_up = orchestrator.answer(result.remainder, session, [], persist=False)
                answer = f"{answer}\n\n{follow_up.answer}"
            except (RuntimeError, GroqError):
                pass

        sessions.append_message(session, "assistant", answer, channel=channel, message_type="assistant_text")
        return ChatResponse(
            answer=answer,
            sources=[],
            session_id=session.id,
            needs_human=bool(follow_up and follow_up.needs_human),
            ticket_number=follow_up.ticket_number if follow_up else None,
        )
