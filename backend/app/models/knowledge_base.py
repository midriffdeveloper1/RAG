from datetime import date as date_, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id

class Business(Base):
    __tablename__ = "business"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    services: Mapped[list["Service"]] = relationship(back_populates="business")
    faqs: Mapped[list["FAQ"]] = relationship(back_populates="business")
    policies: Mapped[list["Policy"]] = relationship(back_populates="business")
    opening_hours: Mapped[list["OpeningHour"]] = relationship(back_populates="business")
    holidays: Mapped[list["Holiday"]] = relationship(back_populates="business")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    business_id: Mapped[str] = mapped_column(String(16), ForeignKey("business.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(nullable=True)

    business: Mapped["Business"] = relationship(back_populates="services")
    staff: Mapped[list["Staff"]] = relationship(
        secondary="staff_services", back_populates="services"
    )


class OpeningHour(Base):
    __tablename__ = "opening_hours"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    business_id: Mapped[str] = mapped_column(String(16), ForeignKey("business.id"))
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False) 
    open_time: Mapped[str] = mapped_column(String(20), nullable=True)  
    close_time: Mapped[str] = mapped_column(String(20), nullable=True)  
    is_closed: Mapped[bool] = mapped_column(default=False)

    business: Mapped["Business"] = relationship(back_populates="opening_hours")


class FAQ(Base):
    __tablename__ = "faqs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    business_id: Mapped[str] = mapped_column(String(16), ForeignKey("business.id"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), nullable=True
    ) 

    business: Mapped["Business"] = relationship(back_populates="faqs")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    business_id: Mapped[str] = mapped_column(String(16), ForeignKey("business.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)  
    content: Mapped[str] = mapped_column(Text, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="policies")


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    business_id: Mapped[str] = mapped_column(String(16), ForeignKey("business.id"))

    date: Mapped[date_ | None] = mapped_column(Date, nullable=True, index=True)
    day_of_week: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    is_full_day: Mapped[bool] = mapped_column(default=True)
    start_time: Mapped[str] = mapped_column(String(20), nullable=True)
    end_time: Mapped[str] = mapped_column(String(20), nullable=True)

    note: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    business: Mapped["Business"] = relationship(back_populates="holidays")