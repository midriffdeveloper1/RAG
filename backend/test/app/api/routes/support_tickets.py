from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.support_ticket import TicketStatusOut
from app.services.support_ticket_service import SupportTicketService

router = APIRouter(prefix="/support/tickets", tags=["Support Tickets"])


@router.get("/{ticket_number}", response_model=TicketStatusOut)
def get_ticket_status(ticket_number: str, db: Session = Depends(get_db)):
    normalized = ticket_number.strip().upper()
    ticket = SupportTicketService(db).get_by_ticket_number(normalized)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ticket found with that number.")
    return TicketStatusOut(
        ticket_number=ticket.ticket_number,
        status=ticket.status,
        opened_at=ticket.opened_at,
        resolved_at=ticket.resolved_at,
    )