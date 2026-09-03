"""Normalized realtime voice event model.

The frontend and the FastAPI voice layer only ever exchange events shaped
like this — never provider-specific payloads. This is what makes the
realtime provider (currently Deepgram) swappable later without touching the
frontend or the orchestrator integration: only app/realtime/*_provider.py
would need to change.
"""
import enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RealtimeEventType(str, enum.Enum):
    SESSION_CREATED = "session.created"
    CALL_STARTED = "call.started"
    CALL_ENDED = "call.ended"

    USER_SPEECH_STARTED = "user.speech.started"
    USER_SPEECH_STOPPED = "user.speech.stopped"
    USER_TRANSCRIPT_PARTIAL = "user.transcript.partial"
    USER_TRANSCRIPT_FINAL = "user.transcript.final"

    ASSISTANT_RESPONSE_STARTED = "assistant.response.started"
    ASSISTANT_TEXT_DELTA = "assistant.text.delta"
    ASSISTANT_TEXT_COMPLETED = "assistant.text.completed"
    ASSISTANT_AUDIO_STARTED = "assistant.audio.started"
    ASSISTANT_AUDIO_COMPLETED = "assistant.audio.completed"

    TOOL_CALL_STARTED = "tool.call.started"
    TOOL_CALL_COMPLETED = "tool.call.completed"

    CONFIRMATION_REQUIRED = "confirmation.required"
    ERROR = "error"


class RealtimeEvent(BaseModel):
    type: RealtimeEventType
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_wire(self) -> dict[str, Any]:
        return {"type": self.type.value, "data": self.data, "timestamp": self.timestamp}


class VoiceCallState(str, enum.Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"
    ENDED = "ended"
