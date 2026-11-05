"""
Medical capabilities endpoint exposing runtime limits and supported file types.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import ApiResponse
from app.schemas.medical_document import CapabilitiesData

router = APIRouter()


@router.get("/capabilities", response_model=ApiResponse[CapabilitiesData])
async def get_capabilities():
    return ApiResponse(
        data=CapabilitiesData(
            supportedMimeTypes=settings.ALLOWED_MIME_TYPES,
            maxFileSizeBytes=settings.MAX_FILE_SIZE_BYTES,
            maxPages=settings.MAX_PAGE_COUNT,
            supportedDocumentTypes=[
                "lab_report",
                "prescription",
                "imaging_report",
                "discharge_summary",
                "other",
            ],
        )
    )

