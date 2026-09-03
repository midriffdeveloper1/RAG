import uuid

from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.services.chat_session_service import ChatSessionService


class VoiceSessionService:
  
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sessions = ChatSessionService(db)

    def start_call(self, browser_id: str, session_id: str | None) -> tuple[ChatSession, str]:
        session = self.sessions.get_or_create(browser_id, session_id)
        if session_id is None:
            session.channel = "voice"

        voice_session_id = str(uuid.uuid4())
        session.voice_session_id = voice_session_id
        self.db.commit()
        return session, voice_session_id

    def get_active_call(self, session_id: str, voice_session_id: str) -> ChatSession | None:
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.voice_session_id == voice_session_id,
            )
            .first()
        )

    def end_call(self, session: ChatSession) -> None:
        session.voice_session_id = None
        self.db.commit()