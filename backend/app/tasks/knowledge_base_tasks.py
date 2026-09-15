import logging

from app.core.celery_app import celery_app
from app.models.document import Document, DocumentStatus
from app.models.notification import NotificationSeverity, NotificationType
from app.services.document_service import DocumentService
from app.services.notification_service import NotificationService
from app.tasks import task_db_session

logger = logging.getLogger(__name__)


@celery_app.task(name="knowledge_base.process_document", bind=True, max_retries=2, default_retry_delay=15)
def process_kb_document_task(self, document_id: str) -> str:
    with task_db_session() as db:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            logger.warning("process_kb_document_task: document_id=%s not found", document_id)
            return "not_found"

        service = DocumentService(db)
        try:
            service.process_document(document)
        except Exception as exc:
            logger.exception("KB document processing failed, will retry: document_id=%s", document_id)
            raise self.retry(exc=exc)

        _notify(db, document)
        return document.status.value


@celery_app.task(name="knowledge_base.reindex_document", bind=True, max_retries=2, default_retry_delay=15)
def reindex_kb_document_task(self, document_id: str) -> str:
    with task_db_session() as db:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            logger.warning("reindex_kb_document_task: document_id=%s not found", document_id)
            return "not_found"

        service = DocumentService(db)
        try:
            service.reindex_document(document)
        except Exception as exc:
            logger.exception("KB document reindex failed, will retry: document_id=%s", document_id)
            raise self.retry(exc=exc)

        _notify(db, document)
        return document.status.value


def _notify(db, document: Document) -> None:
    notifications = NotificationService(db)
    link = "/admin/knowledge-base"
    if document.status == DocumentStatus.COMPLETED:
        notifications.create(
            type=NotificationType.KB_DOCUMENT_COMPLETED,
            title="Knowledge base updated",
            message=f"\u201c{document.original_filename}\u201d was chunked and indexed ({document.chunk_count} chunks).",
            link=link,
            severity=NotificationSeverity.SUCCESS,
            related_id=document.id,
        )
    else:
        notifications.create(
            type=NotificationType.KB_DOCUMENT_FAILED,
            title="Knowledge base indexing failed",
            message=f"\u201c{document.original_filename}\u201d couldn't be indexed: {document.error_message or 'unknown error'}",
            link=link,
            severity=NotificationSeverity.ERROR,
            related_id=document.id,
        )