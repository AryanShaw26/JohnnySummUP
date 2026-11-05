"""
Authentication and user schemas.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = Field(default=None, alias="fullName")
    accept_terms: bool = Field(default=True, alias="acceptTerms")
    accept_privacy: bool = Field(default=True, alias="acceptPrivacy")

    model_config = ConfigDict(populate_by_name=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    email: str
    full_name: str = Field(alias="fullName")
    is_active: bool = Field(default=True, alias="isActive")
    is_verified: bool = Field(default=False, alias="emailVerified")
    role: str = "patient"


class AuthTokens(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_in: int = Field(default=86400, alias="expiresIn")


class AuthResponseData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user: UserResponse
    tokens: AuthTokens
    accessToken: Optional[str] = None  # for camelCase frontend direct access


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    timezone: str = "UTC"
    preferred_unit_system: str = Field(default="metric", alias="preferredUnitSystem")
    language: str = "en"
    default_export_format: str = Field(default="pdf", alias="defaultExportFormat")

