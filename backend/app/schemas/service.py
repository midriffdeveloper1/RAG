from pydantic import BaseModel, Field


class ServiceBase(BaseModel):
    name: str
    description: str | None = None
    price: float = Field(ge=0)
    duration_minutes: int = Field(gt=0)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0)


class ServiceOut(ServiceBase):
    id: int

    model_config = {"from_attributes": True}


class ServiceListResponse(BaseModel):
    items: list[ServiceOut]
    total: int
    page: int
    page_size: int
    total_pages: int