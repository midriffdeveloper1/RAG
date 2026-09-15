from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    invoice_number: Mapped[str] = mapped_column(String(120), nullable=True)
    invoice_date: Mapped[str] = mapped_column(String(20), nullable=True)  # normalized "YYYY-MM-DD" when parseable
    due_date: Mapped[str] = mapped_column(String(20), nullable=True)
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=True)
    vendor_address: Mapped[str] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=True)
    customer_address: Mapped[str] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="invoice")
    line_items = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.position",
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    description: Mapped[str] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)

    invoice = relationship("Invoice", back_populates="line_items")