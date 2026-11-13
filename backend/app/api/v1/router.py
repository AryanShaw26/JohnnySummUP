from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.medical import router as medical_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.workspace_documents import router as workspace_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(medical_router)
api_router.include_router(workspace_router)
