import math

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.models.document import Document, DocumentStatus
from app.schemas.common import PageParams
from app.schemas.document import DocumentActionResponse, DocumentListResponse, DocumentOut
from app.services.document_service import DocumentService

router = APIRouter(prefix="/admin/documents", tags=["Admin Documents"])


def _get_document_or_404(document_id: str, db: Session) -> Document:
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
  
    service = DocumentService(db)

    try:
        dest_path, content_hash, size_bytes = service.save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    duplicate = service.find_completed_duplicate(content_hash)
    if duplicate is not None:
        dest_path.unlink(missing_ok=True)  # don't keep a redundant copy on disk
        return duplicate

    document = service.create_document_record(file, dest_path, content_hash, size_bytes)
    document = service.process_document(document)
    return document


@router.get("", response_model=DocumentListResponse)
def list_documents(
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Document).order_by(Document.uploaded_at.desc())
    total = query.count()
    documents = query.offset(params.offset).limit(params.page_size).all()
    return DocumentListResponse(
        documents=documents,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@router.post("/{document_id}/reindex", response_model=DocumentOut)
def reindex_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    
    document = _get_document_or_404(document_id, db)
    service = DocumentService(db)
    return service.reindex_document(document)


@router.delete("/{document_id}", response_model=DocumentActionResponse)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    document = _get_document_or_404(document_id, db)
    service = DocumentService(db)
    service.delete_document(document)
    return DocumentActionResponse(
        id=document_id,
        status=DocumentStatus.COMPLETED,  # nominal — record no longer exists
        message="Document and its vectors were deleted.",
    )