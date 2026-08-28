import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.chat_session import (
    ChatSessionAdminDetailResponse,
    ChatSessionAdminListResponse,
    ChatSessionAdminOut,
)
from app.schemas.common import PageParams
from app.services.chat_session_service import ChatSessionService

router = APIRouter(prefix="/admin/conversations", tags=["Admin Conversations"])


def _to_out(session) -> ChatSessionAdminOut:
    return ChatSessionAdminOut(
        id=session.id,
        title=session.title,
        customer_email=session.customer.email if session.customer else None,
        needs_human=session.needs_human,
        escalation_reason=session.escalation_reason,
        escalated_at=session.escalated_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("", response_model=ChatSessionAdminListResponse)
def list_conversations(
    needs_human: bool = False,
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    items, total = ChatSessionService(db).admin_list_paginated(
        page=params.page, page_size=params.page_size, needs_human_only=needs_human
    )
    return ChatSessionAdminListResponse(
        items=[_to_out(s) for s in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@router.get("/{session_id}", response_model=ChatSessionAdminDetailResponse)
def get_conversation(session_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    session = ChatSessionService(db).admin_get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ChatSessionAdminDetailResponse(**_to_out(session).model_dump(), messages=session.messages)


@router.post("/{session_id}/resolve", response_model=ChatSessionAdminOut)
def resolve_conversation(session_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    session = ChatSessionService(db).admin_resolve(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return _to_out(session)