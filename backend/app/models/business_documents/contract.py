from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    contract_title: Mapped[str] = mapped_column(Text, nullable=True)
    contract_type: Mapped[str] = mapped_column(Text, nullable=True)
    party_a: Mapped[str] = mapped_column(Text, nullable=True)
    party_b: Mapped[str] = mapped_column(Text, nullable=True)
    effective_date: Mapped[str] = mapped_column(Text, nullable=True)
    expiration_date: Mapped[str] = mapped_column(Text, nullable=True)
    contract_value: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(Text, nullable=True)
    key_terms: Mapped[list] = mapped_column(JSON, nullable=True)  # list[str]
    governing_law: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="contract")
    signatories = relationship(
        "ContractSignatory",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="ContractSignatory.position",
    )


class ContractSignatory(Base):
    __tablename__ = "contract_signatories"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    name: Mapped[str] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=True)

    contract = relationship("Contract", back_populates="signatories")