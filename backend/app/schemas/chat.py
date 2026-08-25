from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What time do you close on Sunday?"])
    browser_id: str = Field(
        ..., min_length=8, description="Anonymous per-browser ID, generated and stored client-side."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Existing chat session to continue. Omit to start a new one.",
    )
    customer_email: Optional[str] = Field(
        default=None,
        description=(
            "Email the customer already confirmed via the identify step (e.g. a "
            "pre-chat modal). When present, the session is bound to this customer "
            "immediately with no in-chat email handshake needed."
        ),
    )


class SourceChunk(BaseModel):

    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = Field(default_factory=list)
    session_id: str