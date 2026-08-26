from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat_session import ChatSessionDetailResponse, ChatSessionListResponse
from app.services.chat_session_service import ChatSessionService
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/chat/sessions", tags=["Chat Sessions"])


class DiscardSessionRequest(BaseModel):
    browser_id: str


def _resolve_customer_id(customer_email: str, db: Session) -> str:
    customer = CustomerService(db).get_by_email(customer_email)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile found for that email.")
    return customer.id


@router.get("", response_model=ChatSessionListResponse)
def list_sessions(
    browser_id: str = Query(..., min_length=8),
    customer_email: str = Query(..., description="The identified customer's email"),
    db: Session = Depends(get_db),
):
    customer_id = _resolve_customer_id(customer_email, db)
    sessions = ChatSessionService(db).list_sessions(browser_id, customer_id)
    return ChatSessionListResponse(sessions=sessions)


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: str,
    browser_id: str = Query(..., min_length=8),
    customer_email: str = Query(..., description="The identified customer's email"),
    db: Session = Depends(get_db),
):
    customer_id = _resolve_customer_id(customer_email, db)
    session = ChatSessionService(db).get_session(session_id, browser_id, customer_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return ChatSessionDetailResponse(id=session.id, title=session.title, messages=session.messages)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    browser_id: str = Query(..., min_length=8),
    customer_email: str = Query(..., description="The identified customer's email"),
    db: Session = Depends(get_db),
):
    customer_id = _resolve_customer_id(customer_email, db)
    deleted = ChatSessionService(db).delete_session(session_id, browser_id, customer_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


@router.post("/{session_id}/discard", status_code=status.HTTP_204_NO_CONTENT)
def discard_session(session_id: str, payload: DiscardSessionRequest, db: Session = Depends(get_db)):
    
    ChatSessionService(db).discard_session(session_id, payload.browser_id)