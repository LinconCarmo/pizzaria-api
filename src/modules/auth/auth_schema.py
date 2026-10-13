from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

PASSWORD_MAX_LENGTH = 128

_EXAMPLE_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."


class LoginDto(BaseModel):
    email: EmailStr = Field(..., description="User email address", examples=["ana@example.com"])
    password: str = Field(
        ...,
        min_length=1,
        max_length=PASSWORD_MAX_LENGTH,
        description="Plain-text password",
        examples=["s3nh@forte"],
    )


class RefreshTokenDto(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token returned by /auth/login",
        examples=[_EXAMPLE_JWT],
    )


class LoginUserResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="User ID (UUID)",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    name: str = Field(..., description="Full name", examples=["Ana Silva"])
    role: str = Field(..., description="User role", examples=["CUSTOMER"])


class LoginResponseDto(BaseModel):
    user: LoginUserResponse = Field(..., description="Authenticated user")
    access_token: str = Field(
        ..., description="Bearer token for authenticated requests", examples=[_EXAMPLE_JWT]
    )
    refresh_token: str = Field(
        ..., description="Token used to obtain a new access token", examples=[_EXAMPLE_JWT]
    )
    expires_in: int = Field(..., description="Access token lifetime in seconds", examples=[900])


class ForgotPasswordDto(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Email that receives the reset instructions",
        examples=["ana@example.com"],
    )


class ResetPasswordDto(BaseModel):
    token: str = Field(
        ...,
        description="Token received by email",
        examples=["3f0c1a52-7d0e-4c4e-9b1a-2f6f1d0c9e11"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=PASSWORD_MAX_LENGTH,
        description="New plain-text password (hashed before persistence)",
        examples=["n0v@s3nh@"],
    )
