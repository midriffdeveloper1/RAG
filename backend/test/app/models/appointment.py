import enum
from datetime import date as date_, datetime
from datetime import time as time_

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    reference_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True, index=True)
    service_id: Mapped[str] = mapped_column(String(16), ForeignKey("services.id"), nullable=False)
    staff_id: Mapped[str] = mapped_column(String(16), ForeignKey("staff.id"), nullable=False)

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    appointment_date: Mapped[date_] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time_] = mapped_column(Time, nullable=False)
    end_time: Mapped[time_] = mapped_column(Time, nullable=False)

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    service: Mapped["Service"] = relationship()
    staff: Mapped["Staff"] = relationship(back_populates="appointments")