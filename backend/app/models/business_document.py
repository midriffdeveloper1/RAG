import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import generate_id


class BusinessDocumentType(str, enum.Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    RESUME = "resume"
    EXPENSE_REPORT = "expense_report"
    APPLICATION_FORM = "application_form"
    CONTRACT = "contract"
    UNKNOWN = "unknown"


class BusinessDocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"      # extracted and fully valid
    NEEDS_REVIEW = "needs_review"  # extracted, but missing/invalid fields
    FAILED = "failed"            


class BusinessDocument(Base):
  
    __tablename__ = "business_documents"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)

    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, jpg, png, docx, doc
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # sha256

    # Classification
    document_type: Mapped[BusinessDocumentType] = mapped_column(
        Enum(BusinessDocumentType), default=BusinessDocumentType.UNKNOWN, nullable=False, index=True
    )
    type_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    requested_document_type: Mapped[str] = mapped_column(String(30), nullable=True)
    
    status: Mapped[BusinessDocumentStatus] = mapped_column(
        Enum(BusinessDocumentStatus), default=BusinessDocumentStatus.PENDING, nullable=False, index=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Extraction results
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    field_confidence: Mapped[dict] = mapped_column(JSON, nullable=True)  
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)  

    # Validation results
    is_valid: Mapped[bool] = mapped_column(default=False)
    validation_errors: Mapped[list] = mapped_column(JSON, nullable=True) 
    missing_fields: Mapped[list] = mapped_column(JSON, nullable=True)  

    reviewed: Mapped[bool] = mapped_column(default=False)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )