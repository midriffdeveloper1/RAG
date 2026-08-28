from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.ids import generate_id


class ChatbotTone(str):
    """Free-form tone label — kept as plain string column (not a DB enum) so new
    tones can be added from the admin UI without a migration."""


class ChatbotConfig(Base):
   
    __tablename__ = "chatbot_config"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)

    widget_title: Mapped[str] = mapped_column(String(120), default="AI Support Assistant")
    tagline: Mapped[str] = mapped_column(String(160), default="Support Assistant")
    avatar_emoji: Mapped[str] = mapped_column(String(8), default="✦")
    primary_color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    accent_color: Mapped[str] = mapped_column(String(20), default="#22c55e")

    tone: Mapped[str] = mapped_column(String(40), default="friendly")
    persona_instructions: Mapped[str] = mapped_column(Text, nullable=True)
    greeting_message: Mapped[str] = mapped_column(
        Text, default="Hi there! Before we get started, could you share your email address?"
    )
    fallback_message: Mapped[str] = mapped_column(
        Text,
        default="I couldn't quite complete that — could you tell me more about what you need?",
    )
    max_reply_words: Mapped[int] = mapped_column(Integer, default=80)
    temperature: Mapped[float] = mapped_column(Float, default=0.3)

    enable_appointment_booking: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_knowledge_base: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_email_gate: Mapped[bool] = mapped_column(Boolean, default=True)
    show_suggested_questions: Mapped[bool] = mapped_column(Boolean, default=True)

    suggested_questions: Mapped[str] = mapped_column(
        Text,
        default=(
            "What is your business information?|"
            "what is your services and cost?|"
            "what is your opening hours and closing hours?"
        ),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def suggested_questions_list(self) -> list[str]:
        return [q.strip() for q in self.suggested_questions.split("|") if q.strip()]

    def set_suggested_questions(self, questions: list[str]) -> None:
        self.suggested_questions = "|".join(q.strip() for q in questions if q.strip())