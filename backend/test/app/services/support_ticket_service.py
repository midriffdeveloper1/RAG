import json
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.chat_session import ChatMessage, ChatSession
from app.models.support_ticket import SupportTicket

_TICKET_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
_TICKET_LENGTH = 8


class SupportTicketService:

    def __init__(self, db: Session) -> None:
        self.db = db

    def _generate_ticket_number(self) -> str:
        while True:
            code = "TCK-" + "".join(secrets.choice(_TICKET_ALPHABET) for _ in range(_TICKET_LENGTH))
            exists = self.db.query(SupportTicket.id).filter(SupportTicket.ticket_number == code).first()
            if not exists:
                return code

    def create_from_session(self, session: ChatSession, reason: str) -> SupportTicket:
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        transcript = [
            {
                "role": m.role,
                "content": m.content,
                "agent": m.agent,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

        customer = session.customer
        ticket = SupportTicket(
            ticket_number=self._generate_ticket_number(),
            session_id=session.id,
            customer_email=customer.email if customer else None,
            customer_name=customer.name if customer else None,
            customer_phone=customer.phone if customer else None,
            escalation_reason=reason,
            transcript_json=json.dumps(transcript),
            status="open",
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        self.db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
        self.db.commit()

        return ticket

    def append_message(self, ticket: SupportTicket, role: str, content: str, agent: str | None = None) -> None:
        try:
            messages = json.loads(ticket.transcript_json)
        except (TypeError, ValueError):
            messages = []
        messages.append(
            {
                "role": role,
                "content": content,
                "agent": agent,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
        ticket.transcript_json = json.dumps(messages)
        ticket.updated_at = datetime.utcnow()
        self.db.commit()

    def get_transcript(self, ticket: SupportTicket) -> list[dict]:
        try:
            return json.loads(ticket.transcript_json)
        except (TypeError, ValueError):
            return []

    def get_by_ticket_number(self, ticket_number: str) -> SupportTicket | None:
        return self.db.query(SupportTicket).filter(SupportTicket.ticket_number == ticket_number).first()

    def resolve(self, ticket_number: str) -> SupportTicket | None:
        ticket = self.get_by_ticket_number(ticket_number)
        if ticket is None:
            return None
        ticket.status = "resolved"
        ticket.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def reopen(self, ticket_number: str) -> SupportTicket | None:
        ticket = self.get_by_ticket_number(ticket_number)
        if ticket is None:
            return None
        ticket.status = "open"
        ticket.resolved_at = None
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def delete_by_number(self, ticket_number: str) -> bool:
        ticket = self.get_by_ticket_number(ticket_number)
        if ticket is None:
            return False
        self.db.delete(ticket)
        self.db.commit()
        return True