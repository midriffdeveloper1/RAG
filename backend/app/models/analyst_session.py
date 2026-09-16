from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class AnalystSession(Base):
    """
    One conversation thread with the SQL analyst agent.

    Kept separate from `chat_sessions` on purpose: that table models a
    *customer* support conversation (browser_id, customer_id, escalation,
    ticket_number) and is surfaced in the admin Conversations page. An analyst
    thread is an internal admin tool with none of those concerns, and mixing
    them would put SQL queries into the customer conversation review UI.
    """

    __tablename__ = "analyst_sessions"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    admin_id: Mapped[str] = mapped_column(
        ForeignKey("admins.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )

    messages: Mapped[list["AnalystMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AnalystMessage.created_at",
    )


class AnalystMessage(Base):
    __tablename__ = "analyst_messages"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analyst_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # "ok" | "out_of_scope" | "needs_clarification" | "blocked" | "error"
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # The generated SQL is stored so the admin can audit what ran, and so
    # follow-up questions ("break that down by month") can extend the actual
    # previous query rather than re-deriving it from the prose answer.
    sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Result snapshot, so reopening a thread shows the same table/chart
    # without re-running the query against data that may have changed.
    result_columns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    result_rows: Mapped[list | None] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truncated: Mapped[bool] = mapped_column(default=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chart: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    session: Mapped["AnalystSession"] = relationship(back_populates="messages")
