from pydantic import BaseModel

from app.schemas.service import ServiceOut


class StaffBase(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool = True


class StaffCreate(StaffBase):
    service_ids: list[int] = []


class StaffUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    service_ids: list[int] | None = None


class StaffOut(StaffBase):
    id: int
    services: list[ServiceOut] = []

    model_config = {"from_attributes": True}