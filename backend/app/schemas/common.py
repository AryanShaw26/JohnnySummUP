"""
Common response envelopes and pagination schemas matching JohnnySummUP API spec.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResponseMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    requestId: Optional[str] = Field(default=None, alias="requestId")
    timestamp: str = Field(default_factory=_utcnow_iso)


class ApiResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = True
    data: T
    meta: Optional[ResponseMeta] = Field(default_factory=ResponseMeta)


class PaginationInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: int = 1
    pageSize: int = 20
    totalItems: int = 0
    totalPages: int = 1


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = True
    data: List[T]
    pagination: PaginationInfo
    meta: Optional[ResponseMeta] = Field(default_factory=ResponseMeta)

