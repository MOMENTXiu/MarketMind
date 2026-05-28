"""Auth-related Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    display_name: str | None = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeResponse(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    status: str


class SseTicketRequest(BaseModel):
    resource_type: str
    resource_id: str
    project_id: str | None = None
    job_id: str | None = None
    stream_type: str | None = None


class SseTicketResponse(BaseModel):
    ticket: str
    expires_at: str | None = None
