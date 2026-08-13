from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What time do you close on Sunday?"])
    session_id: Optional[str] = Field(
        default=None, description="Client-generated ID to group a conversation."
    )


class SourceChunk(BaseModel):
    """A retrieved knowledge-base chunk that backed the answer (for citations/debugging)."""

    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = Field(default_factory=list)
    session_id: Optional[str] = None
