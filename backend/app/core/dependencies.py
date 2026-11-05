"""
FastAPI dependency callables: database sessions, authenticated user, etc.
"""

from __future__ import annotations

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.errors import AuthenticationError, ErrorCode, ForbiddenError
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Database session ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Current authenticated user ──────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Bearer token."""
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationError(
                message="Token payload missing subject.",
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
            )
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as exc:
        raise AuthenticationError(
            message="Could not validate credentials.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError(
            message="User not found.",
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
        )

    if not user.is_active:
        raise ForbiddenError(
            message="User account is disabled.",
            error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias ensuring the user is active (already checked, kept for clarity)."""
    return current_user
