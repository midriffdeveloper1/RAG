from datetime import datetime

from pydantic import BaseModel


class ChatSessionOut(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionOut]


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    id: str
    title: str | None = None
    messages: list[ChatMessageOut]


class ChatMessageAdminOut(BaseModel):
    role: str
    content: str
    agent: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionAdminOut(BaseModel):
    id: str
    title: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    needs_human: bool
    ticket_number: str | None = None
    escalation_reason: str | None = None
    escalated_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionAdminListResponse(BaseModel):
    items: list[ChatSessionAdminOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ChatSessionAdminDetailResponse(ChatSessionAdminOut):
    messages: list[ChatMessageAdminOut]