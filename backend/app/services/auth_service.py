"""
Authentication and user account service.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, ConflictError, NotFoundError
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.auth import AuthResponseData, AuthTokens, LoginRequest, RegisterRequest, UserResponse

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, data: RegisterRequest) -> Tuple[User, AuthTokens]:
    """Register a new user account."""
    existing = await db.execute(select(User).where(User.email == data.email.lower()))
    if existing.scalar_one_or_none():
        raise ConflictError(message="An account with this email already exists.")

    names = (data.full_name or "").split(" ", 1)
    first_name = names[0] if names else ""
    last_name = names[1] if len(names) > 1 else ""

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        first_name=first_name,
        last_name=last_name,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    # Create default settings
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    await db.commit()
    await db.refresh(user)

    tokens = AuthTokens(
        accessToken=create_access_token(user.id),
        refreshToken=create_refresh_token(user.id),
    )
    return user, tokens


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> Tuple[User, AuthTokens]:
    """Authenticate existing user credentials."""
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise AuthenticationError(message="Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError(message="Account is deactivated.")

    tokens = AuthTokens(
        accessToken=create_access_token(user.id),
        refreshToken=create_refresh_token(user.id),
    )
    return user, tokens


async def get_user_settings(db: AsyncSession, user_id: UUID) -> UserSettings:
    """Retrieve settings for a user."""
    res = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = res.scalar_one_or_none()
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings

