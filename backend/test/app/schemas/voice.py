from pydantic import BaseModel, Field


class VoiceSessionRequest(BaseModel):
    browser_id: str = Field(..., min_length=8)
    session_id: str | None = Field(
        default=None, description="Existing chat/voice conversation to continue."
    )
    customer_email: str | None = None


class DeepgramStreamConfig(BaseModel):
    url: str
    params: dict[str, str]


class VoiceSessionResponse(BaseModel):
    conversation_id: str
    voice_session_id: str
    ws_url: str
    deepgram_token: str
    deepgram_token_expires_in_seconds: int
    stt: DeepgramStreamConfig
    tts: DeepgramStreamConfig