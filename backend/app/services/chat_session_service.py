from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.chat_session import ChatMessage, ChatSession
from app.schemas.chat import ChatTurn

TITLE_MAX_LENGTH = 60


class ChatSessionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, browser_id: str, session_id: str | None) -> ChatSession:
        if session_id:
            session = (
                self.db.query(ChatSession)
                .filter(ChatSession.id == session_id, ChatSession.browser_id == browser_id)
                .first()
            )
            if session is not None:
                return session

        session = ChatSession(browser_id=browser_id)
        self.db.add(session)
        self.db.flush()
        return session

    def append_message(self, session: ChatSession, role: str, content: str, agent: str | None = None) -> None:
        self.db.add(ChatMessage(session_id=session.id, role=role, content=content, agent=agent))
        if role == "user" and not session.title:
            session.title = content.strip()[:TITLE_MAX_LENGTH]
        session.updated_at = datetime.utcnow()
        self.db.commit()

    def get_history(self, session_id: str, max_exchanges: int) -> list[ChatTurn]:
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        turns = [ChatTurn(role=r.role, content=r.content) for r in rows]
        limit = max_exchanges * 2
        return turns[-limit:] if limit else turns


    def list_sessions(self, browser_id: str, customer_id: str) -> list[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.browser_id == browser_id, ChatSession.customer_id == customer_id)
            .order_by(ChatSession.updated_at.desc())
            .all()
        )

    def get_session(self, session_id: str, browser_id: str, customer_id: str) -> ChatSession | None:
        return (
            self.db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.browser_id == browser_id,
                ChatSession.customer_id == customer_id,
            )
            .first()
        )

    def delete_session(self, session_id: str, browser_id: str, customer_id: str) -> bool:
        session = self.get_session(session_id, browser_id, customer_id)
        if session is None:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def discard_session(self, session_id: str, browser_id: str) -> bool:
        
        session = (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.browser_id == browser_id)
            .first()
        )
        if session is None:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def admin_list_paginated(
        self, page: int, page_size: int, needs_human_only: bool = False
    ) -> tuple[list[ChatSession], int]:
        query = self.db.query(ChatSession)
        if needs_human_only:
            query = query.filter(ChatSession.needs_human.is_(True))
        query = query.order_by(ChatSession.updated_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def admin_get(self, session_id: str) -> ChatSession | None:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def admin_resolve(self, session_id: str) -> ChatSession | None:
        session = self.admin_get(session_id)
        if session is None:
            return None
        session.needs_human = False
        session.unresolved_streak = 0
        self.db.commit()
        self.db.refresh(session)
        return session

    def purge_stale_sessions(self, retention_hours: int) -> int:
        
        cutoff = datetime.utcnow() - timedelta(hours=retention_hours)
        stale = self.db.query(ChatSession).filter(ChatSession.updated_at < cutoff)
        count = stale.count()
        if count:
            for session in stale.all():
                self.db.delete(session)
            self.db.commit()
        return count