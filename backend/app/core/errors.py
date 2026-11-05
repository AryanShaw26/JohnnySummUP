"""
Error catalogue and custom exception classes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


# ── Error codes ──────────────────────────────────────────────────────────────

class ErrorCode:
    """Centralised catalogue of error codes matching the API spec."""

    # Authentication / Authorization
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"
    AUTH_EMAIL_ALREADY_EXISTS = "AUTH_EMAIL_ALREADY_EXISTS"
    AUTH_WEAK_PASSWORD = "AUTH_WEAK_PASSWORD"

    # Resource
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"

    # Document
    DOCUMENT_UPLOAD_FAILED = "DOCUMENT_UPLOAD_FAILED"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"
    DOCUMENT_UNSUPPORTED_TYPE = "DOCUMENT_UNSUPPORTED_TYPE"
    DOCUMENT_PROCESSING_FAILED = "DOCUMENT_PROCESSING_FAILED"

    # Processing
    PROCESSING_QUEUE_FULL = "PROCESSING_QUEUE_FULL"
    PROCESSING_TIMEOUT = "PROCESSING_TIMEOUT"

    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# ── HTTP status → default error code mapping ────────────────────────────────

_STATUS_DEFAULTS: Dict[int, str] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.AUTH_TOKEN_INVALID,
    403: ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
    404: ErrorCode.RESOURCE_NOT_FOUND,
    409: ErrorCode.RESOURCE_CONFLICT,
    413: ErrorCode.DOCUMENT_TOO_LARGE,
    415: ErrorCode.DOCUMENT_UNSUPPORTED_TYPE,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMIT_EXCEEDED,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


# ── Custom exceptions ───────────────────────────────────────────────────────

class AppException(Exception):
    """Base exception that carries an error code and structured detail."""

    def __init__(
        self,
        status_code: int = 500,
        error_code: Optional[str] = None,
        message: str = "An unexpected error occurred.",
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code or _STATUS_DEFAULTS.get(status_code, ErrorCode.INTERNAL_ERROR)
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """401 Unauthorized."""

    def __init__(
        self,
        message: str = "Could not validate credentials.",
        error_code: str = ErrorCode.AUTH_INVALID_CREDENTIALS,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=401, error_code=error_code, message=message, detail=detail)


class ForbiddenError(AppException):
    """403 Forbidden."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        error_code: str = ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=403, error_code=error_code, message=message, detail=detail)


class NotFoundError(AppException):
    """404 Not Found."""

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        error_code: str = ErrorCode.RESOURCE_NOT_FOUND,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=404, error_code=error_code, message=message, detail=detail)


class ConflictError(AppException):
    """409 Conflict."""

    def __init__(
        self,
        message: str = "Resource already exists.",
        error_code: str = ErrorCode.RESOURCE_ALREADY_EXISTS,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=409, error_code=error_code, message=message, detail=detail)


class ValidationError(AppException):
    """422 Validation Error."""

    def __init__(
        self,
        message: str = "Validation failed.",
        error_code: str = ErrorCode.VALIDATION_ERROR,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=422, error_code=error_code, message=message, detail=detail)


# ── Exception handlers ──────────────────────────────────────────────────────

async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """Return a uniform JSON error envelope for AppException subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        },
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap FastAPI's HTTPException into the standard envelope."""
    code = _STATUS_DEFAULTS.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": str(exc.detail),
                "detail": {},
            },
        },
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions – never leak stack traces."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An unexpected error occurred.",
                "detail": {},
            },
        },
    )
