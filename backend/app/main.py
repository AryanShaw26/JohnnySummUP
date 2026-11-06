import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import get_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    if settings.openai_api_key is None:
        logger.info("Optional future-phase OpenAI integration is not configured")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    frontend_origins = [settings.frontend_origin]
    development_origins = {"http://localhost:5173", "http://127.0.0.1:5173"}
    if settings.frontend_origin in development_origins:
        frontend_origins = sorted(development_origins)

    app = FastAPI(
        title="JohnnySummUP API",
        description="Phase 1 account and authentication API.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
