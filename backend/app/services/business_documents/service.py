from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.business_document import (
    BusinessDocument,
    BusinessDocumentStatus,
    BusinessDocumentType,
)
from app.services.business_documents import extraction
from app.services.business_documents.scoring import compute_confidence
from app.services.business_documents.validation import validate_fields
from app.services.document_processor import extract_text, infer_file_type

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

    # ---- Upload -------------------------------------------------------

    def save_upload(self, file: UploadFile) -> tuple[Path, str, int, str]:
        file_type = infer_file_type(file.filename)
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
    ) -> BusinessDocument:
        document = BusinessDocument(
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

    # ---- Processing -----------------------------------------------------

    def process_document(self, document: BusinessDocument) -> BusinessDocument:
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
                document.extracted_data = {}
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
                document.extracted_data = result.fields
                document.field_confidence = result.field_confidence
                document.confidence_score = confidence
                document.is_valid = is_valid
                document.validation_errors = errors
                document.missing_fields = missing
                document.status = (
                    BusinessDocumentStatus.COMPLETED if is_valid else BusinessDocumentStatus.NEEDS_REVIEW
                )
                document.error_message = None

            document.processed_at = datetime.utcnow()

        except Exception as exc:
            logger.exception("Failed to process business_document_id=%s", document.id)
            document.status = BusinessDocumentStatus.FAILED
            document.error_message = str(exc)

        self.db.commit()
        self.db.refresh(document)
        return document

    def _run_extraction(
        self, document: BusinessDocument, expected_type: BusinessDocumentType | None
    ) -> extraction.ExtractionResult:
        if document.file_type in TEXT_EXTENSIONS:
            raw_text = extract_text(document.file_path, document.file_type)
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

    # ---- Corrections / lifecycle ---------------------------------------

    def apply_manual_correction(
        self, document: BusinessDocument, field_updates: dict
    ) -> BusinessDocument:
        """Admin-edited field values. Treated as ground truth (confidence 1.0)
        and re-validated, but never re-sent to the LLM."""

        merged_fields = dict(document.extracted_data or {})
        merged_fields.update(field_updates)

        merged_confidence = dict(document.field_confidence or {})
        for key in field_updates:
            merged_confidence[key] = 1.0

        is_valid, errors, missing = validate_fields(document.document_type, merged_fields)
        confidence = compute_confidence(document.document_type, merged_fields, merged_confidence, missing)

        document.extracted_data = merged_fields
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

    def find_completed_duplicate(self, content_hash: str) -> BusinessDocument | None:
        return (
            self.db.query(BusinessDocument)
            .filter(
                BusinessDocument.content_hash == content_hash,
                BusinessDocument.status.in_(
                    [BusinessDocumentStatus.COMPLETED, BusinessDocumentStatus.NEEDS_REVIEW]
                ),
            )
            .first()
        )

    def delete_document(self, document: BusinessDocument) -> None:
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
        self.db.delete(document)
        self.db.commit()