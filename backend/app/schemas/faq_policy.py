from pydantic import BaseModel, Field


class FAQOut(BaseModel):
    id: int
    question: str
    answer: str
    category: str | None = None

    model_config = {"from_attributes": True}


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str | None = None


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None


class PolicyOut(BaseModel):
    id: int
    title: str
    content: str

    model_config = {"from_attributes": True}


class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class PolicyUpdate(BaseModel):
    title: str | None = None
    content: str | None = None