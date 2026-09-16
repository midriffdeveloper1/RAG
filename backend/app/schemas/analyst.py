from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalystAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(
        default=None,
        description="Continue an existing thread. Omit to start a new one.",
    )


class ChartSpecOut(BaseModel):
    type: str
    label_column: str
    value_column: str


class AnalystMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    status: str | None = None
    sql: str | None = None
    intent: str | None = None
    result_columns: list[str] | None = None
    result_rows: list[list[Any]] | None = None
    row_count: int | None = None
    truncated: bool = False
    duration_ms: int | None = None
    chart: ChartSpecOut | None = None
    created_at: datetime


class AnalystAskResponse(BaseModel):
    session_id: str
    message: AnalystMessageOut


class AnalystSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class AnalystSessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[AnalystMessageOut] = []


class AnalystSessionListResponse(BaseModel):
    sessions: list[AnalystSessionSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class SuggestedQuestion(BaseModel):
    label: str
    question: str


class AnalystScopeResponse(BaseModel):
    document_types: list[str]
    suggestions: list[SuggestedQuestion]
