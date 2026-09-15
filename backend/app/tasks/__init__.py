"""Celery tasks live here. Each task opens its own short-lived DB session
via `task_db_session()` rather than reusing FastAPI's request-scoped
`get_db` — a Celery worker is a separate process with no request context.
"""

from contextlib import contextmanager

from app.core.database import SessionLocal


@contextmanager
def task_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()