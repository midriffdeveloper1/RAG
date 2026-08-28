import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from groq import GroqError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agents.orchestrator import OrchestratorService
from app.services.chat_session_service import ChatSessionService
from app.services.customer_service import CustomerService
from app.services.onboarding_service import OnboardingService

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

    sessions = ChatSessionService(db)
    session = sessions.get_or_create(payload.browser_id, payload.session_id)

    if payload.customer_email:
        current_email = session.customer.email if session.customer_id else None
        if current_email != payload.customer_email.strip().lower():
            result = CustomerService(db).identify(payload.customer_email)
            if "error" not in result:
                session.customer_id = result["customer"]["id"]
                db.commit()

    if session.customer_id is None:
        is_first_turn = not sessions.get_history(session.id, max_exchanges=1)
        onboarding = OnboardingService(db)
        result = onboarding.handle(payload.question, session, payload.browser_id, is_first_turn)
        db.commit()

        sessions.append_message(session, "user", payload.question)

        answer = result.reply
        if result.identified and result.remainder and len(result.remainder) > 3:
            try:
                orchestrator = OrchestratorService(db, browser_id=payload.browser_id, customer=session.customer)
                follow_up = orchestrator.answer(result.remainder, session, [])
                answer = f"{answer}\n\n{follow_up.answer}"
            except (RuntimeError, GroqError):
                pass  

        sessions.append_message(session, "assistant", answer)
        return ChatResponse(answer=answer, sources=[], session_id=session.id)

    history = sessions.get_history(session.id, settings.max_history_exchanges)
    sessions.append_message(session, "user", payload.question)

    try:
        orchestrator = OrchestratorService(db, browser_id=payload.browser_id, customer=session.customer)
        response = orchestrator.answer(payload.question, session, history)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except GroqError as exc:
        logger.error("Groq API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        )

    sessions.append_message(session, "assistant", response.answer, agent=response.agent)
    response.session_id = session.id
    return response