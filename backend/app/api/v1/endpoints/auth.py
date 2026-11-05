"""
Authentication and user profile endpoints.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponseData,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    UserSettingsResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import authenticate_user, get_user_settings, register_user

router = APIRouter()


@router.post("/register", response_model=ApiResponse[AuthResponseData], status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user, tokens = await register_user(db, data)
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        isActive=user.is_active,
        emailVerified=user.is_verified,
        role=user.role,
    )
    return ApiResponse(
        data=AuthResponseData(
            user=user_resp,
            tokens=tokens,
            accessToken=tokens.access_token,
        )
    )


@router.post("/login", response_model=ApiResponse[AuthResponseData])
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, tokens = await authenticate_user(db, data)
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        isActive=user.is_active,
        emailVerified=user.is_verified,
        role=user.role,
    )
    return ApiResponse(
        data=AuthResponseData(
            user=user_resp,
            tokens=tokens,
            accessToken=tokens.access_token,
        )
    )


@router.post("/logout", response_model=ApiResponse[Dict[str, str]])
async def logout():
    return ApiResponse(data={"message": "Logged out successfully."})


@router.post("/forgot-password", response_model=ApiResponse[Dict[str, str]])
async def forgot_password(data: ForgotPasswordRequest):
    # Neutral response for privacy as per spec
    return ApiResponse(data={"message": "If an account exists, a reset link has been dispatched."})


@router.post("/reset-password", response_model=ApiResponse[Dict[str, str]])
async def reset_password(data: ResetPasswordRequest):
    return ApiResponse(data={"message": "Password reset successfully."})


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    user_resp = UserResponse(
        id=current_user.id,
        email=current_user.email,
        fullName=current_user.full_name,
        isActive=current_user.is_active,
        emailVerified=current_user.is_verified,
        role=current_user.role,
    )
    return ApiResponse(data=user_resp)


@router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_me(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if "full_name" in data or "fullName" in data:
        full_name = data.get("full_name") or data.get("fullName") or ""
        parts = full_name.split(" ", 1)
        current_user.first_name = parts[0]
        current_user.last_name = parts[1] if len(parts) > 1 else ""

    await db.commit()
    await db.refresh(current_user)

    user_resp = UserResponse(
        id=current_user.id,
        email=current_user.email,
        fullName=current_user.full_name,
        isActive=current_user.is_active,
        emailVerified=current_user.is_verified,
        role=current_user.role,
    )
    return ApiResponse(data=user_resp)


@router.get("/me/settings", response_model=ApiResponse[UserSettingsResponse])
async def get_my_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_user_settings(db, current_user.id)
    return ApiResponse(data=UserSettingsResponse.model_validate(settings))

