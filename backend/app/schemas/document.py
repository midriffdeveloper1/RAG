from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentStatus
class DocumentOut(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size_bytes: int
    status: DocumentStatus
    error_message: Optional[str] = None
    chunk_count: int
    version: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int


class DocumentActionResponse(BaseModel):
    id: int
    status: DocumentStatus
    message: str