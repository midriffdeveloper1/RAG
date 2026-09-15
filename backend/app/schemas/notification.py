from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.notification import NotificationSeverity, NotificationType


class NotificationOut(BaseModel):
    id: str
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    link: Optional[str] = None
    related_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationOut]
    total: int
    unread_count: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class UnreadCountResponse(BaseModel):
    unread_count: int