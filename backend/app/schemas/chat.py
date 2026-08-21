from typing import List, Literal, Optional
from pydantic import BaseModel, Field
class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What time do you close on Sunday?"])
    session_id: Optional[str] = Field(
        default=None, description="Client-generated ID to group a conversation."
    )
    history: List[ChatTurn] = Field(
        default_factory=list,
        description=(
            "Prior turns of this conversation, oldest first. Only the most "
            "recent MAX_HISTORY_EXCHANGES exchanges are used — trimmed "
            "server-side regardless of how much is sent."
        ),
    )


class SourceChunk(BaseModel):
    content: str
    source: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk] = Field(default_factory=list)
    session_id: Optional[str] = None