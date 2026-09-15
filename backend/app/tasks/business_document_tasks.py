import logging

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.models.business_documents.upload import BusinessDocumentUpload
from app.services.business_documents.service import BusinessDocumentService
from app.services.notification_service import notify_business_document_result
from app.tasks import task_db_session

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="business_documents.process", bind=True, max_retries=2, default_retry_delay=15)
def process_business_document_task(self, upload_id: str) -> str:
    
    with task_db_session() as db:
        document = db.query(BusinessDocumentUpload).filter(BusinessDocumentUpload.id == upload_id).first()
        if document is None:
            logger.warning("process_business_document_task: upload_id=%s not found", upload_id)
            return "not_found"

        service = BusinessDocumentService(db)
        try:
            service.process_document(document)
        except Exception as exc:  # transient errors (LLM timeout, etc.) get retried
            logger.exception("business document processing failed, will retry: upload_id=%s", upload_id)
            raise self.retry(exc=exc)

        notify_business_document_result(db, document, settings.low_confidence_notification_threshold)
        return document.status.value