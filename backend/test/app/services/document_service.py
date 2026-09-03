import hashlib
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document, DocumentStatus
from app.services.document_processor import chunk_text, extract_text, infer_file_type
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.vector_store = get_vector_store()
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # Upload

    def save_upload(self, file: UploadFile) -> tuple[Path, str, int]:
        file_type = infer_file_type(file.filename)
        if f".{file_type}" not in settings.allowed_upload_extensions_list:
            raise ValueError(
                f"'.{file_type}' files aren't supported. "
                f"Allowed: {settings.allowed_upload_extensions}"
            )

        stored_name = f"{uuid.uuid4().hex}.{file_type}"
        dest_path = self.upload_dir / stored_name

        hasher = hashlib.sha256()
        size_bytes = 0
        with open(dest_path, "wb") as out_file:
            while chunk := file.file.read(1024 * 1024):  # stream in 1MB pieces
                hasher.update(chunk)
                size_bytes += len(chunk)
                out_file.write(chunk)

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            dest_path.unlink(missing_ok=True)
            raise ValueError(f"File exceeds the {settings.max_upload_size_mb}MB limit.")

        return dest_path, hasher.hexdigest(), size_bytes

    def create_document_record(
        self, file: UploadFile, dest_path: Path, content_hash: str, size_bytes: int
    ) -> Document:
        document = Document(
            original_filename=file.filename,
            stored_filename=dest_path.name,
            file_path=str(dest_path),
            file_type=infer_file_type(file.filename),
            file_size_bytes=size_bytes,
            content_hash=content_hash,
            status=DocumentStatus.PENDING,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def find_completed_duplicate(self, content_hash: str) -> Document | None:

        return (
            self.db.query(Document)
            .filter(
                Document.content_hash == content_hash,
                Document.status == DocumentStatus.COMPLETED,
            )
            .first()
        )


    def process_document(self, document: Document) -> Document:
       
        document.status = DocumentStatus.PROCESSING
        self.db.commit()

        try:
            raw_text = extract_text(document.file_path, document.file_type)
            if not raw_text.strip():
                raise ValueError("No extractable text found in this document.")

            chunks = chunk_text(raw_text)
            if not chunks:
                raise ValueError("Text extraction produced no usable chunks.")

            written = self.vector_store.upsert_document_chunks(
                document_id=document.id,
                chunks=chunks,
                source_filename=document.original_filename,
                version=document.version,
            )

            document.status = DocumentStatus.COMPLETED
            document.chunk_count = written
            document.error_message = None
            document.processed_at = datetime.utcnow()
            self.db.commit()

            try:
                from app.services.document_extraction_service import DocumentExtractionService

                summary = DocumentExtractionService(self.db).extract_and_apply(raw_text)
                document.extraction_summary = summary.to_text()
            except Exception:
                logger.exception(
                    "Document field extraction failed for document_id=%s (RAG indexing already succeeded)",
                    document.id,
                )

        except Exception as exc:  
            logger.exception("Failed to process document_id=%s", document.id)
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)

        self.db.commit()
        self.db.refresh(document)
        return document

    #  Reindex / delete (memory management) 

    def reindex_document(self, document: Document) -> Document:
        self.vector_store.delete_by_document_id(document.id)
        document.version += 1
        document.chunk_count = 0
        self.db.commit()
        return self.process_document(document)

    def delete_document(self, document: Document) -> None:
        self.vector_store.delete_by_document_id(document.id)

        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        self.db.delete(document)
        self.db.commit()