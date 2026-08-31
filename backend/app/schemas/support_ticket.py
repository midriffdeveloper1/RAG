from datetime import datetime

from pydantic import BaseModel


class TicketStatusOut(BaseModel):
   
    ticket_number: str
    status: str  # "open" | "resolved"
    opened_at: datetime | None = None
    resolved_at: datetime | None = None