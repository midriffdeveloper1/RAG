from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationSeverity, NotificationType


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        related_id: str | None = None,
    ) -> Notification:
        notification = Notification(
            type=type,
            severity=severity,
            title=title,
            message=message,
            link=link,
            related_id=related_id,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def list_paginated(
        self, page: int = 1, page_size: int = 20, unread_only: bool = False
    ) -> tuple[list[Notification], int]:
        query = self.db.query(Notification)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        query = query.order_by(Notification.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def unread_count(self) -> int:
        return self.db.query(Notification).filter(Notification.is_read.is_(False)).count()

    def mark_read(self, notification_id: str) -> Notification | None:
        notification = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if notification is None:
            return None
        notification.is_read = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read(self) -> int:
        updated = (
            self.db.query(Notification)
            .filter(Notification.is_read.is_(False))
            .update({Notification.is_read: True})
        )
        self.db.commit()
        return updated

    def delete(self, notification_id: str) -> bool:
        notification = self.db.query(Notification).filter(Notification.id == notification_id).first()
        if notification is None:
            return False
        self.db.delete(notification)
        self.db.commit()
        return True


def notify_business_document_result(db: Session, document, low_confidence_threshold: float) -> None:
    """Given a just-processed BusinessDocumentUpload, fire the right
    notification: failed / needs review / low confidence / completed."""
    from app.models.business_documents.upload import BusinessDocumentStatus

    service = NotificationService(db)
    link = f"/admin/business-management/{_type_path(document.document_type)}?doc={document.id}"
    filename = document.original_filename

    if document.status == BusinessDocumentStatus.FAILED:
        service.create(
            type=NotificationType.BUSINESS_DOCUMENT_FAILED,
            title="Document processing failed",
            message=f"\u201c{filename}\u201d couldn't be processed: {document.error_message or 'unknown error'}",
            link="/admin/business-management/upload",
            severity=NotificationSeverity.ERROR,
            related_id=document.id,
        )
        return

    if document.status == BusinessDocumentStatus.NEEDS_REVIEW:
        missing = document.missing_fields or []
        detail = f"missing: {', '.join(missing)}" if missing else "some fields need a review"
        service.create(
            type=NotificationType.BUSINESS_DOCUMENT_NEEDS_REVIEW,
            title="Document needs review",
            message=f"\u201c{filename}\u201d was extracted but {detail}.",
            link=link,
            severity=NotificationSeverity.WARNING,
            related_id=document.id,
        )
        return

    # Completed and technically valid, but still worth flagging if the
    # model wasn't confident about what it read.
    if document.confidence_score is not None and document.confidence_score < low_confidence_threshold:
        pct = round(document.confidence_score * 100)
        service.create(
            type=NotificationType.BUSINESS_DOCUMENT_LOW_CONFIDENCE,
            title="Low-confidence extraction",
            message=f"\u201c{filename}\u201d was extracted at only {pct}% confidence — worth a quick check.",
            link=link,
            severity=NotificationSeverity.WARNING,
            related_id=document.id,
        )
        return

    service.create(
        type=NotificationType.BUSINESS_DOCUMENT_COMPLETED,
        title="Document processed",
        message=f"\u201c{filename}\u201d was extracted and validated successfully.",
        link=link,
        severity=NotificationSeverity.SUCCESS,
        related_id=document.id,
    )


def _type_path(document_type) -> str:
    mapping = {
        "invoice": "invoices",
        "receipt": "receipts",
        "purchase_order": "purchase-orders",
        "resume": "resumes",
        "expense_report": "expense-reports",
        "application_form": "application-forms",
        "contract": "contracts",
    }
    value = document_type.value if hasattr(document_type, "value") else str(document_type)
    return mapping.get(value, "upload")