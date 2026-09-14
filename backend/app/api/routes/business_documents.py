import math

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.models.business_document import (
    BusinessDocument,
    BusinessDocumentStatus,
    BusinessDocumentType,
)
from app.schemas.business_document import (
    BusinessDocumentActionResponse,
    BusinessDocumentListResponse,
    BusinessDocumentOut,
    BusinessDocumentSummaryResponse,
    BusinessDocumentUpdate,
    DocumentTypeSummary,
)
from app.schemas.common import PageParams
from app.services.business_documents.field_schemas import DOCUMENT_TYPE_LABELS
from app.services.business_documents.service import BusinessDocumentService

router = APIRouter(prefix="/admin/business-documents", tags=["Admin Business Documents"])

MAX_FILES_PER_BATCH = 15


def _get_document_or_404(document_id: str, db: Session) -> BusinessDocument:
    document = db.query(BusinessDocument).filter(BusinessDocument.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post("/upload", response_model=list[BusinessDocumentOut], status_code=status.HTTP_201_CREATED)
def upload_business_documents(
    files: list[UploadFile],
    document_type: str | None = Query(
        default=None,
        description="Optional expected type hint (e.g. uploading from the Invoices page).",
    ),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):


    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded.")
    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload at most {MAX_FILES_PER_BATCH} files at a time.",
        )

    requested_type: str | None = None
    if document_type:
        try:
            requested_type = BusinessDocumentType(document_type).value
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown document_type '{document_type}'.",
            )

    service = BusinessDocumentService(db)
    results: list[BusinessDocument] = []

    for file in files:
        try:
            dest_path, content_hash, size_bytes, file_type = service.save_upload(file)
        except ValueError as exc:
            results.append(
                _failed_placeholder(db, file.filename or "unknown", str(exc))
            )
            continue

        duplicate = service.find_completed_duplicate(content_hash)
        if duplicate is not None:
            dest_path.unlink(missing_ok=True)
            results.append(duplicate)
            continue

        document = service.create_document_record(
            file, dest_path, content_hash, size_bytes, file_type, requested_type
        )
        document = service.process_document(document)
        results.append(document)

    return results


def _failed_placeholder(db: Session, filename: str, message: str) -> BusinessDocument:
    
    placeholder = BusinessDocument(
        original_filename=filename,
        stored_filename="",
        file_path="",
        file_type=filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown",
        file_size_bytes=0,
        content_hash="",
        status=BusinessDocumentStatus.FAILED,
        error_message=message,
        extracted_data={},
        field_confidence={},
        is_valid=False,
        validation_errors=[],
        missing_fields=[],
    )
    db.add(placeholder)
    db.commit()
    db.refresh(placeholder)
    return placeholder


@router.get("", response_model=BusinessDocumentListResponse)
def list_business_documents(
    document_type: BusinessDocumentType | None = Query(default=None),
    status_filter: BusinessDocumentStatus | None = Query(default=None, alias="status"),
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(BusinessDocument)
    if document_type is not None:
        query = query.filter(BusinessDocument.document_type == document_type)
    if status_filter is not None:
        query = query.filter(BusinessDocument.status == status_filter)

    query = query.order_by(BusinessDocument.uploaded_at.desc())
    total = query.count()
    documents = query.offset(params.offset).limit(params.page_size).all()

    return BusinessDocumentListResponse(
        documents=documents,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@router.get("/summary", response_model=BusinessDocumentSummaryResponse)
def get_summary(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    by_type: list[DocumentTypeSummary] = []
    total_documents = db.query(BusinessDocument).count()

    for doc_type in BusinessDocumentType:
        if doc_type == BusinessDocumentType.UNKNOWN:
            continue
        base_query = db.query(BusinessDocument).filter(BusinessDocument.document_type == doc_type)
        by_type.append(
            DocumentTypeSummary(
                document_type=doc_type,
                label=DOCUMENT_TYPE_LABELS[doc_type],
                total=base_query.count(),
                needs_review=base_query.filter(
                    BusinessDocument.status == BusinessDocumentStatus.NEEDS_REVIEW
                ).count(),
                failed=base_query.filter(
                    BusinessDocument.status == BusinessDocumentStatus.FAILED
                ).count(),
            )
        )

    return BusinessDocumentSummaryResponse(total_documents=total_documents, by_type=by_type)


@router.get("/{document_id}", response_model=BusinessDocumentOut)
def get_business_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return _get_document_or_404(document_id, db)


@router.patch("/{document_id}", response_model=BusinessDocumentOut)
def update_business_document(
    document_id: str,
    payload: BusinessDocumentUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    document = _get_document_or_404(document_id, db)
    if document.document_type == BusinessDocumentType.UNKNOWN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document's type couldn't be identified, so its fields can't be edited.",
        )
    service = BusinessDocumentService(db)
    return service.apply_manual_correction(document, payload.fields)


@router.post("/{document_id}/reprocess", response_model=BusinessDocumentOut)
def reprocess_business_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    document = _get_document_or_404(document_id, db)
    service = BusinessDocumentService(db)
    return service.process_document(document)


@router.delete("/{document_id}", response_model=BusinessDocumentActionResponse)
def delete_business_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    document = _get_document_or_404(document_id, db)
    service = BusinessDocumentService(db)
    service.delete_document(document)
    return BusinessDocumentActionResponse(
        id=document_id,
        status=BusinessDocumentStatus.COMPLETED,
        message="Document deleted.",
    )