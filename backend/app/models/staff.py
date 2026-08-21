from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

staff_services = Table(
    "staff_services",
    Base.metadata,
    Column("staff_id", ForeignKey("staff.id"), primary_key=True),
    Column("service_id", ForeignKey("services.id"), primary_key=True),
)


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    services: Mapped[list["Service"]] = relationship(
        secondary=staff_services, back_populates="staff"
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="staff")