from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.appointment import Appointment, AppointmentStatus
from app.models.chat_session import ChatSession
from app.models.customer import Customer
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import Service
from app.models.staff import Staff
from app.schemas.analytics import AnalyticsOverview, AppointmentsByStatus

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    total_documents = db.query(func.count(Document.id)).scalar() or 0
    documents_failed = (
        db.query(func.count(Document.id)).filter(Document.status == DocumentStatus.FAILED).scalar() or 0
    )
    total_services = db.query(func.count(Service.id)).scalar() or 0
    total_staff = db.query(func.count(Staff.id)).scalar() or 0
    active_staff = db.query(func.count(Staff.id)).filter(Staff.is_active.is_(True)).scalar() or 0
    total_customers = db.query(func.count(Customer.id)).scalar() or 0

    total_appointments = db.query(func.count(Appointment.id)).scalar() or 0
    by_status = dict(
        db.query(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status).all()
    )
    appointments_last_7_days = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.created_at >= seven_days_ago)
        .scalar()
        or 0
    )

    total_chat_sessions = db.query(func.count(ChatSession.id)).scalar() or 0
    chat_sessions_last_7_days = (
        db.query(func.count(ChatSession.id))
        .filter(ChatSession.created_at >= seven_days_ago)
        .scalar()
        or 0
    )
    escalated_chat_sessions = (
        db.query(func.count(ChatSession.id)).filter(ChatSession.needs_human.is_(True)).scalar() or 0
    )

    return AnalyticsOverview(
        total_documents=total_documents,
        total_services=total_services,
        total_staff=total_staff,
        active_staff=active_staff,
        total_customers=total_customers,
        total_appointments=total_appointments,
        appointments_by_status=AppointmentsByStatus(
            booked=by_status.get(AppointmentStatus.BOOKED, 0),
            completed=by_status.get(AppointmentStatus.COMPLETED, 0),
            cancelled=by_status.get(AppointmentStatus.CANCELLED, 0),
        ),
        appointments_last_7_days=appointments_last_7_days,
        total_chat_sessions=total_chat_sessions,
        chat_sessions_last_7_days=chat_sessions_last_7_days,
        documents_failed=documents_failed,
        escalated_chat_sessions=escalated_chat_sessions,
    )