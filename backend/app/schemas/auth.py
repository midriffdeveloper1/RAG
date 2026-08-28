from pydantic import BaseModel, EmailStr
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
class AdminOut(BaseModel):
    id: str
    email: EmailStr

    model_config = {"from_attributes": True}