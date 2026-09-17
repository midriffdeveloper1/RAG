from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class ApplicationForm(Base):
    __tablename__ = "application_forms"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    applicant_name: Mapped[str] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(Text, nullable=True)
    phone: Mapped[str] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[str] = mapped_column(Text, nullable=True)
    position_applied_for: Mapped[str] = mapped_column(Text, nullable=True)
    submission_date: Mapped[str] = mapped_column(Text, nullable=True)
    # Application forms vary too widely to model every possible field as a
    # column — whatever doesn't map to the named fields above lands here.
    additional_fields: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="application_form")