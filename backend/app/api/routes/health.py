from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import get_settings
router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Basic liveness check. Extend this to also ping Postgres / Qdrant if needed."""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
