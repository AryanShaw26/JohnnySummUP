from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import JWTError, decode_access_token
from app.models.user import User


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not access_token:
        raise unauthorized

    try:
        user_id: UUID = decode_access_token(access_token)
    except (JWTError, ValueError, KeyError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    from app.core.config import get_settings

    settings = get_settings()
    admin_list = [e.lower().strip() for e in settings.admin_emails]
    user_email = current_user.email.lower().strip()

    is_admin = user_email in admin_list or user_email.startswith("admin@")
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required to access diagnostic endpoints.",
        )
    return current_user
