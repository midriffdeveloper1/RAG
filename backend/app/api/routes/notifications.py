import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_page_params
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.common import PageParams
from app.schemas.notification import NotificationListResponse, NotificationOut, UnreadCountResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(default=False),
    params: PageParams = Depends(get_page_params),
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    service = NotificationService(db)
    notifications, total = service.list_paginated(
        page=params.page, page_size=params.page_size, unread_only=unread_only
    )
    return NotificationListResponse(
        notifications=notifications,
        total=total,
        unread_count=service.unread_count(),
        page=params.page,
        page_size=params.page_size,
        total_pages=max(1, math.ceil(total / params.page_size)),
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    return UnreadCountResponse(unread_count=NotificationService(db).unread_count())


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    notification = NotificationService(db).mark_read(notification_id)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    updated = NotificationService(db).mark_all_read()
    return {"updated": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    deleted = NotificationService(db).delete(notification_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")