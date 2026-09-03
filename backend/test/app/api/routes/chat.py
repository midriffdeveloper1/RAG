import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from groq import GroqError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_session_service import ChatSessionService
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])
settings = get_settings()


def _purge_stale_sessions_task() -> None:
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        removed = ChatSessionService(db).purge_stale_sessions(settings.chat_session_retention_hours)
        if removed:
            logger.info("Purged %s stale chat session(s)", removed)
    finally:
        db.close()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(_purge_stale_sessions_task)

    conversation = ConversationService(db)
    session = conversation.get_or_create_session(payload.browser_id, payload.session_id, channel="chat")

    try:
        return conversation.handle_turn(
            payload.question,
            session,
            browser_id=payload.browser_id,
            customer_email=payload.customer_email,
            channel="chat",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GroqError as exc:
        logger.error("Groq API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        )