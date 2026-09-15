from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.models.business_documents.upload import BusinessDocumentStatus, BusinessDocumentType


class ValidationIssue(BaseModel):
    field: str
    message: str


class BusinessDocumentOut(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size_bytes: int

    document_type: BusinessDocumentType
    type_confidence: Optional[float] = None
    requested_document_type: Optional[str] = None

    status: BusinessDocumentStatus
    error_message: Optional[str] = None

    extracted_data: Optional[dict[str, Any]] = None
    field_confidence: Optional[dict[str, float]] = None
    confidence_score: Optional[float] = None

    is_valid: bool
    validation_errors: Optional[list[ValidationIssue]] = None
    missing_fields: Optional[list[str]] = None
    reviewed: bool

    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class BusinessDocumentListResponse(BaseModel):
    documents: list[BusinessDocumentOut]
    total: int
    page: int = 1
    page_size: int = 10
    total_pages: int = 1


class BusinessDocumentUpdate(BaseModel):
    fields: dict[str, Any]


class BusinessDocumentActionResponse(BaseModel):
    id: str
    status: BusinessDocumentStatus
    message: str


class DocumentTypeSummary(BaseModel):
    document_type: BusinessDocumentType
    label: str
    total: int
    needs_review: int
    failed: int


class BusinessDocumentSummaryResponse(BaseModel):
    total_documents: int
    by_type: list[DocumentTypeSummary]


class FieldSchemaEntry(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    item_fields: Optional[list["FieldSchemaEntry"]] = None