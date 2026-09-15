from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class ExpenseReport(Base):
    __tablename__ = "expense_reports"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    employee_name: Mapped[str] = mapped_column(String(255), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(80), nullable=True)
    department: Mapped[str] = mapped_column(String(255), nullable=True)
    report_date: Mapped[str] = mapped_column(String(20), nullable=True)
    expense_period_start: Mapped[str] = mapped_column(String(20), nullable=True)
    expense_period_end: Mapped[str] = mapped_column(String(20), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    approver_name: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="expense_report")
    expenses = relationship(
        "ExpenseReportItem",
        back_populates="expense_report",
        cascade="all, delete-orphan",
        order_by="ExpenseReportItem.position",
    )


class ExpenseReportItem(Base):
    __tablename__ = "expense_report_items"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    expense_report_id: Mapped[str] = mapped_column(
        ForeignKey("expense_reports.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0)

    date: Mapped[str] = mapped_column(String(20), nullable=True)
    category: Mapped[str] = mapped_column(String(120), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)

    expense_report = relationship("ExpenseReport", back_populates="expenses")