import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.models.analyst_session import AnalystMessage, AnalystSession
from app.schemas.analyst import (
    AnalystAskRequest,
    AnalystAskResponse,
    AnalystMessageOut,
    AnalystScopeResponse,
    AnalystSessionDetail,
    AnalystSessionListResponse,
    AnalystSessionSummary,
    SuggestedQuestion,
)
from app.schemas.common import PageParams
from app.services.analyst.analyst_service import AnalystService

logger = logging.getLogger(__name__)

# Admin-only by construction: every route depends on get_current_admin, and
# there is deliberately no public/customer-facing counterpart to this router.
router = APIRouter(prefix="/admin/analyst", tags=["Admin Data Analyst"])

HISTORY_TURNS = 8

SUGGESTIONS = [
    SuggestedQuestion(
        label="Invoice totals last month",
        question="How many invoices did we receive last month and what was their total value?",
    ),
    SuggestedQuestion(
        label="Top vendors",
        question="Which vendor has invoiced us the most in the last 6 months?",
    ),
    SuggestedQuestion(
        label="Top products by revenue",
        question="Which product generated the most revenue across all invoices in the last 6 months?",
    ),
    SuggestedQuestion(
        label="Expenses by category",
        question="What is our total expense amount by category this year?",
    ),
    SuggestedQuestion(
        label="Contracts expiring",
        question="Which contracts expire in the next 90 days?",
    ),
    SuggestedQuestion(
        label="Candidate pipeline",
        question="How many resumes have we received, and what are the most common skills?",
    ),
]


def _get_session_or_404(session_id: str, admin: Admin, db: Session) -> AnalystSession:
    session = (
        db.query(AnalystSession)
        .filter(
            AnalystSession.id == session_id,
            # Scoped to the requesting admin so one admin can't read another's
            # threads by guessing an ID.
            AnalystSession.admin_id == admin.id,
        )
        .first()
    )

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return session


def _build_history(session: AnalystSession) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []

    for message in session.messages[-HISTORY_TURNS:]:
        entry = {"role": message.role, "content": message.content}

        if message.sql:
            entry["sql"] = message.sql

        history.append(entry)

    return history


@router.get("/scope", response_model=AnalystScopeResponse)
def get_analyst_scope(admin: Admin = Depends(get_current_admin)):
    """What the agent can answer, plus starter questions for an empty thread."""
    return AnalystScopeResponse(
        document_types=[
            "Invoices",
            "Receipts",
            "Purchase orders",
            "Resumes",
            "Expense reports",
            "Application forms",
            "Contracts",
        ],
        suggestions=SUGGESTIONS,
    )


@router.post("/ask", response_model=AnalystAskResponse)
def ask_analyst(
    payload: AnalystAskRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    if payload.session_id:
        session = _get_session_or_404(payload.session_id, admin, db)
    else:
        session = AnalystSession(
            admin_id=admin.id,
            # First question doubles as the thread title.
            title=payload.question[:120],
        )
        db.add(session)
        db.flush()

    db.add(
        AnalystMessage(
            session_id=session.id,
            role="user",
            content=payload.question,
        )
    )
    db.flush()

    history = _build_history(session)
    # Drop the turn we just added — it's the question being asked, not context.
    history = [turn for turn in history if turn.get("content") != payload.question] or history[:-1]

    service = AnalystService()

    try:
        result = service.ask(payload.question, history)
    except RuntimeError as exc:
        # LLMService raises this when OPENAI_API_KEY isn't configured.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    assistant_message = AnalystMessage(
        session_id=session.id,
        role="assistant",
        content=result.answer,
        status=result.status,
        sql=result.sql,
        intent=result.intent,
        result_columns=result.columns or None,
        result_rows=result.rows or None,
        row_count=result.row_count,
        truncated=result.truncated,
        duration_ms=result.duration_ms,
        chart=(
            {
                "type": result.chart.type,
                "label_column": result.chart.label_column,
                "value_column": result.chart.value_column,
            }
            if result.chart
            else None
        ),
    )

    db.add(assistant_message)
    session.updated_at = func.now()
    db.commit()
    db.refresh(assistant_message)

    return AnalystAskResponse(
        session_id=session.id,
        message=AnalystMessageOut.model_validate(assistant_message),
    )


@router.get("/sessions", response_model=AnalystSessionListResponse)
def list_analyst_sessions(
    page_params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    base = db.query(AnalystSession).filter(AnalystSession.admin_id == admin.id)
    total = base.count()

    sessions = (
        base.order_by(AnalystSession.updated_at.desc())
        .offset(page_params.offset)
        .limit(page_params.page_size)
        .all()
    )

    summaries = [
        AnalystSessionSummary(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
        )
        for session in sessions
    ]

    return AnalystSessionListResponse(
        sessions=summaries,
        total=total,
        page=page_params.page,
        page_size=page_params.page_size,
        total_pages=max(1, math.ceil(total / page_params.page_size)),
    )


@router.get("/sessions/{session_id}", response_model=AnalystSessionDetail)
def get_analyst_session(
    session_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    session = _get_session_or_404(session_id, admin, db)
    return AnalystSessionDetail.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analyst_session(
    session_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    session = _get_session_or_404(session_id, admin, db)
    db.delete(session)
    db.commit()
