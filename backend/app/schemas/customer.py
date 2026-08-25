from pydantic import BaseModel, EmailStr, Field


class CustomerIdentifyRequest(BaseModel):
    email: EmailStr
    browser_id: str = Field(..., min_length=8)


class CustomerOut(BaseModel):
    id: int
    email: str
    name: str | None = None
    phone: str | None = None


class CustomerIdentifyResponse(BaseModel):
    is_returning: bool
    customer: CustomerOut 