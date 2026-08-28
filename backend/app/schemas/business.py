from pydantic import BaseModel, Field

from app.schemas.faq_policy import FAQOut, PolicyOut


class OpeningHourOut(BaseModel):
    id: str
    day_of_week: str
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool = False

    model_config = {"from_attributes": True}


class OpeningHourUpdate(BaseModel):
    day_of_week: str
    open_time: str | None = None
    close_time: str | None = None
    is_closed: bool = False


class BusinessOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    opening_hours: list[OpeningHourOut] = []
    faqs: list[FAQOut] = []
    policies: list[PolicyOut] = []

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    opening_hours: list[OpeningHourUpdate] | None = None