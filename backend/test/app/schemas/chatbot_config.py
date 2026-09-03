from pydantic import BaseModel, Field

TONE_OPTIONS = ["friendly", "professional", "casual", "formal", "playful", "empathetic"]

VOICE_NAME_OPTIONS = [
    "aura-asteria-en",  # warm, friendly (default)
    "aura-luna-en",     # calm, approachable
    "aura-stella-en",   # upbeat, clear
    "aura-orion-en",    # confident, male
    "aura-arcas-en",    # casual, male
]


class ChatbotConfigOut(BaseModel):
    widget_title: str
    tagline: str
    avatar_emoji: str
    primary_color: str
    accent_color: str
    tone: str
    persona_instructions: str | None = None
    greeting_message: str
    fallback_message: str
    max_reply_words: int
    temperature: float
    enable_appointment_booking: bool
    enable_knowledge_base: bool
    enable_email_gate: bool
    show_suggested_questions: bool
    suggested_questions: list[str] = []
    voice_enabled: bool
    voice_name: str
    voice_greeting_message: str | None = None

    model_config = {"from_attributes": True}


class ChatbotConfigUpdate(BaseModel):
    widget_title: str | None = Field(default=None, min_length=1, max_length=120)
    tagline: str | None = Field(default=None, max_length=160)
    avatar_emoji: str | None = Field(default=None, max_length=8)
    primary_color: str | None = None
    accent_color: str | None = None
    tone: str | None = None
    persona_instructions: str | None = None
    greeting_message: str | None = None
    fallback_message: str | None = None
    max_reply_words: int | None = Field(default=None, ge=20, le=300)
    temperature: float | None = Field(default=None, ge=0.0, le=1.0)
    enable_appointment_booking: bool | None = None
    enable_knowledge_base: bool | None = None
    enable_email_gate: bool | None = None
    show_suggested_questions: bool | None = None
    suggested_questions: list[str] | None = None
    voice_enabled: bool | None = None
    voice_name: str | None = Field(default=None, max_length=60)
    voice_greeting_message: str | None = None