from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat_session import ChatSessionDetailResponse, ChatSessionListResponse
from app.services.chat_session_service import ChatSessionService

router = APIRouter(prefix="/chat/sessions", tags=["Chat Sessions"])


@router.get("", response_model=ChatSessionListResponse)
def list_sessions(browser_id: str = Query(..., min_length=8), db: Session = Depends(get_db)):
    sessions = ChatSessionService(db).list_sessions(browser_id)
    return ChatSessionListResponse(sessions=sessions)


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: str, browser_id: str = Query(..., min_length=8), db: Session = Depends(get_db)
):
    session = ChatSessionService(db).get_session(session_id, browser_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return ChatSessionDetailResponse(id=session.id, title=session.title, messages=session.messages)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str, browser_id: str = Query(..., min_length=8), db: Session = Depends(get_db)
):
    deleted = ChatSessionService(db).delete_session(session_id, browser_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")