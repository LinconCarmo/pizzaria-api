from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginDto(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenDto(BaseModel):
    refresh_token: str


class LoginUserResponse(BaseModel):
    id: UUID
    name: str
    role: str


class LoginResponseDto(BaseModel):
    user: LoginUserResponse
    access_token: str
    refresh_token: str
    expires_in: int


class ForgotPasswordDto(BaseModel):
    email: EmailStr


class ResetPasswordDto(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
