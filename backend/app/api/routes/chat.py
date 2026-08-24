import logging

from fastapi import APIRouter, Depends, HTTPException, status
from groq import GroqError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.chat_session_service import ChatSessionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])
settings = get_settings()


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    sessions = ChatSessionService(db)
    session = sessions.get_or_create(payload.browser_id, payload.session_id)
    history = sessions.get_history(session.id, settings.max_history_exchanges)
    sessions.append_message(session, "user", payload.question)

    try:
        agent = AgentService(db)
        response = agent.answer(payload.question, session.id, history)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GroqError as exc:
        logger.error("Groq API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        )

    sessions.append_message(session, "assistant", response.answer)
    response.session_id = session.id
    return response