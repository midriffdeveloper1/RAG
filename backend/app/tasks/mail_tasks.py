import logging

from app.core.celery_app import celery_app
from app.services.mail_service import send_email

logger = logging.getLogger(__name__)


@celery_app.task(name="mail.send", bind=True, max_retries=3, default_retry_delay=20)
def send_email_task(self, to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    try:
        return send_email(to_email, subject, html_body, text_body)
    except Exception as exc:
        logger.exception("send_email_task failed for %s, will retry", to_email)
        raise self.retry(exc=exc)