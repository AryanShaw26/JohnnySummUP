from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


def is_duplicate_email_error(error: IntegrityError) -> bool:
    original = error.orig
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    constraint_name = getattr(getattr(original, "diag", None), "constraint_name", None)
    if sqlstate == "23505" and constraint_name == "uq_users_email":
        return True
    err_str = str(error).lower()
    return "unique constraint" in err_str and "users.email" in err_str


def set_auth_cookie(response: Response, user_id) -> None:
    settings = get_settings()
    response.set_cookie(
        key="access_token",
        value=create_access_token(user_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        if not is_duplicate_email_error(error):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from error

    set_auth_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    set_auth_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
