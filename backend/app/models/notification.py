import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import generate_id


class NotificationSeverity(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationType(str, enum.Enum):
    BUSINESS_DOCUMENT_COMPLETED = "business_document_completed"
    BUSINESS_DOCUMENT_NEEDS_REVIEW = "business_document_needs_review"
    BUSINESS_DOCUMENT_LOW_CONFIDENCE = "business_document_low_confidence"
    BUSINESS_DOCUMENT_FAILED = "business_document_failed"
    KB_DOCUMENT_COMPLETED = "kb_document_completed"
    KB_DOCUMENT_FAILED = "kb_document_failed"
    APPOINTMENT_BOOKED = "appointment_booked"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    GENERIC = "generic"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)

    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False, index=True)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity), default=NotificationSeverity.INFO, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    link: Mapped[str] = mapped_column(String(500), nullable=True)
    related_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)