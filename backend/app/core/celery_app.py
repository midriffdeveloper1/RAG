"""Celery application for background work: business-document extraction,
knowledge-base chunking/embedding, and outbound email.

Run a worker (from backend/):
    celery -A app.core.celery_app.celery_app worker --loglevel=info

On Windows, the default "prefork" pool isn't supported — use:
    celery -A app.core.celery_app.celery_app worker --loglevel=info --pool=solo

See CELERY_SETUP.md at the repo root for the full run book.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_support_agent",
    broker=settings.celery_broker_url_resolved,
    backend=settings.celery_result_backend_resolved,
    include=[
        "app.tasks.business_document_tasks",
        "app.tasks.knowledge_base_tasks",
        "app.tasks.mail_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.business_document_tasks.*": {"queue": "documents"},
        "app.tasks.knowledge_base_tasks.*": {"queue": "documents"},
        "app.tasks.mail_tasks.*": {"queue": "mail"},
    },
    # Long-running LLM extraction calls shouldn't be killed prematurely.
    task_soft_time_limit=300,
    task_time_limit=360,
)