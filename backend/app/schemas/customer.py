from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CustomerIdentifyRequest(BaseModel):
    email: EmailStr
    browser_id: str = Field(..., min_length=8)


class CustomerOut(BaseModel):
    id: str
    email: str
    name: str | None = None
    phone: str | None = None


class CustomerIdentifyResponse(BaseModel):
    is_returning: bool
    customer: CustomerOut


class CustomerAdminOut(BaseModel):
    id: str
    email: str
    name: str | None = None
    phone: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerAdminOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class CustomerAdminCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    phone: str | None = None


class CustomerAdminUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    phone: str | None = None
