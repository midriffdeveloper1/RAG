from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    receipt_number: Mapped[str] = mapped_column(Text, nullable=True)
    merchant_name: Mapped[str] = mapped_column(Text, nullable=True)
    merchant_address: Mapped[str] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[str] = mapped_column(Text, nullable=True)
    transaction_time: Mapped[str] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=True)
    payment_method: Mapped[str] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="receipt")
    items = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptItem.position",
    )


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    description: Mapped[str] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)

    receipt = relationship("Receipt", back_populates="items")