from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.business_documents.upload import (
    BusinessDocumentStatus,
    BusinessDocumentType,
    BusinessDocumentUpload,
)
from app.services.business_documents import extraction, persistence
from app.services.business_documents.scoring import compute_confidence
from app.services.business_documents.validation import validate_fields

logger = logging.getLogger(__name__)
settings = get_settings()

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
TEXT_EXTENSIONS = {"pdf", "docx", "doc"}

_MIME_BY_EXTENSION = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class UnreadableDocumentError(ValueError):
    pass


class BusinessDocumentService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.upload_dir = Path(settings.business_document_upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _infer_file_type(filename: str) -> str:
        from app.services.document_processor import infer_file_type

        return infer_file_type(filename)

    @staticmethod
    def _extract_text(file_path: str, file_type: str) -> str:
        from app.services.document_processor import extract_text

        return extract_text(file_path, file_type)

    
    def save_upload(self, file: UploadFile) -> tuple[Path, str, int, str]:
        file_type = self._infer_file_type(file.filename)
        if f".{file_type}" not in settings.business_document_allowed_extensions_list:
            raise ValueError(
                f"'.{file_type}' files aren't supported here. "
                f"Allowed: {settings.business_document_allowed_extensions}"
            )

        stored_name = f"{uuid.uuid4().hex}.{file_type}"
        dest_path = self.upload_dir / stored_name

        hasher = hashlib.sha256()
        size_bytes = 0
        with open(dest_path, "wb") as out_file:
            while chunk := file.file.read(1024 * 1024):
                hasher.update(chunk)
                size_bytes += len(chunk)
                out_file.write(chunk)

        max_bytes = settings.business_document_max_upload_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            dest_path.unlink(missing_ok=True)
            raise ValueError(
                f"File exceeds the {settings.business_document_max_upload_size_mb}MB limit."
            )
        if size_bytes == 0:
            dest_path.unlink(missing_ok=True)
            raise ValueError("The uploaded file is empty.")

        return dest_path, hasher.hexdigest(), size_bytes, file_type

    def create_document_record(
        self,
        file: UploadFile,
        dest_path: Path,
        content_hash: str,
        size_bytes: int,
        file_type: str,
        requested_document_type: str | None = None,
    ) -> BusinessDocumentUpload:
        document = BusinessDocumentUpload(
            original_filename=file.filename,
            stored_filename=dest_path.name,
            file_path=str(dest_path),
            file_type=file_type,
            file_size_bytes=size_bytes,
            content_hash=content_hash,
            status=BusinessDocumentStatus.PENDING,
            requested_document_type=requested_document_type,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    # ---- Processing (runs inside a Celery worker) ----------------------

    def process_document(self, document: BusinessDocumentUpload) -> BusinessDocumentUpload:
        document.status = BusinessDocumentStatus.PROCESSING
        self.db.commit()

        expected_type: BusinessDocumentType | None = None
        if document.requested_document_type:
            try:
                expected_type = BusinessDocumentType(document.requested_document_type)
            except ValueError:
                expected_type = None

        try:
            result = self._run_extraction(document, expected_type)

            if result.document_type == BusinessDocumentType.UNKNOWN:
                document.document_type = BusinessDocumentType.UNKNOWN
                document.type_confidence = result.type_confidence
                document.status = BusinessDocumentStatus.FAILED
                document.error_message = (
                    "Couldn't confidently match this file to a supported document type "
                    "(invoice, receipt, purchase order, resume, expense report, "
                    "application form, or contract)."
                )
                document.field_confidence = {}
                document.is_valid = False
                document.validation_errors = []
                document.missing_fields = []
                document.confidence_score = result.type_confidence
            else:
                is_valid, errors, missing = validate_fields(result.document_type, result.fields)
                confidence = compute_confidence(
                    result.document_type, result.fields, result.field_confidence, missing
                )

                document.document_type = result.document_type
                document.type_confidence = result.type_confidence
                document.field_confidence = result.field_confidence
                document.confidence_score = confidence
                document.is_valid = is_valid
                document.validation_errors = errors
                document.missing_fields = missing
                document.status = (
                    BusinessDocumentStatus.COMPLETED if is_valid else BusinessDocumentStatus.NEEDS_REVIEW
                )
                document.error_message = None

                persistence.apply_fields(self.db, document, result.document_type, result.fields)

            document.processed_at = datetime.utcnow()

        except Exception as exc:
            logger.exception("Failed to process business_document_id=%s", document.id)
           
            self.db.rollback()
            self.db.refresh(document)

            document.status = BusinessDocumentStatus.FAILED
            document.error_message = _describe_error(exc)

        self.db.commit()
        self.db.refresh(document)
        return document

    def _run_extraction(
        self, document: BusinessDocumentUpload, expected_type: BusinessDocumentType | None
    ) -> extraction.ExtractionResult:
        if document.file_type in TEXT_EXTENSIONS:
            raw_text = self._extract_text(document.file_path, document.file_type)
            if not raw_text.strip():
                raise UnreadableDocumentError(
                    "No extractable text found in this file. If it's a scanned document, "
                    "upload it as an image (JPG/PNG) instead."
                )
            return extraction.extract_from_text(raw_text, expected_type)

        if document.file_type in IMAGE_EXTENSIONS:
            image_bytes = Path(document.file_path).read_bytes()
            mime_type = _MIME_BY_EXTENSION.get(document.file_type, "image/jpeg")
            return extraction.extract_from_image(image_bytes, mime_type, expected_type)

        raise ValueError(f"Unsupported file type for extraction: {document.file_type}")

    # ---- Corrections / lifecycle (Admin CRUD) ---------------------------

    def apply_manual_correction(
        self, document: BusinessDocumentUpload, field_updates: dict
    ) -> BusinessDocumentUpload:
        persistence.apply_fields(self.db, document, document.document_type, field_updates)
        merged_fields = persistence.serialize_fields(document)

        merged_confidence = dict(document.field_confidence or {})
        for key in field_updates:
            merged_confidence[key] = 1.0

        is_valid, errors, missing = validate_fields(document.document_type, merged_fields)
        confidence = compute_confidence(document.document_type, merged_fields, merged_confidence, missing)

        document.field_confidence = merged_confidence
        document.is_valid = is_valid
        document.validation_errors = errors
        document.missing_fields = missing
        document.confidence_score = confidence
        document.reviewed = True
        document.status = (
            BusinessDocumentStatus.COMPLETED if is_valid else BusinessDocumentStatus.NEEDS_REVIEW
        )

        self.db.commit()
        self.db.refresh(document)
        return document

    def set_review_status(
        self, document: BusinessDocumentUpload, new_status: BusinessDocumentStatus
    ) -> BusinessDocumentUpload:
     
        if new_status not in (BusinessDocumentStatus.COMPLETED, BusinessDocumentStatus.NEEDS_REVIEW):
            raise ValueError("Status can only be set to 'completed' or 'needs_review'.")

        if document.status not in (BusinessDocumentStatus.COMPLETED, BusinessDocumentStatus.NEEDS_REVIEW):
            raise ValueError(
                f"Can't change status while the document is '{document.status.value}' — "
                "wait for processing to finish, or reprocess it first."
            )

        document.status = new_status
        document.reviewed = True

        self.db.commit()
        self.db.refresh(document)
        return document

    def find_completed_duplicate(self, content_hash: str) -> BusinessDocumentUpload | None:
        return (
            self.db.query(BusinessDocumentUpload)
            .filter(
                BusinessDocumentUpload.content_hash == content_hash,
                BusinessDocumentUpload.status.in_(
                    [BusinessDocumentStatus.COMPLETED, BusinessDocumentStatus.NEEDS_REVIEW]
                ),
            )
            .first()
        )

    def delete_document(self, document: BusinessDocumentUpload) -> None:
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
        self.db.delete(document)  # cascades to the type-specific row + its children
        self.db.commit()


_MAX_ERROR_MESSAGE_LENGTH = 500


def _describe_error(exc: Exception) -> str:

    if isinstance(exc, SQLAlchemyError):
        return (
            "Something about the extracted data didn't fit the database as-is "
            f"({type(getattr(exc, 'orig', exc)).__name__}). This has been logged "
            "for review — try reprocessing, and if it keeps happening the "
            "document may need a manual look."
        )

    message = str(exc).strip() or type(exc).__name__

    if len(message) > _MAX_ERROR_MESSAGE_LENGTH:
        message = message[:_MAX_ERROR_MESSAGE_LENGTH].rstrip() + "…"

    return message