from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import generate_id


class SupportTicket(Base):


    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    ticket_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    escalation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # "open" | "resolved"

    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )