import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    if settings.gemini_api_key is None:
        logger.info("Gemini AI integration is not configured")
    else:
        logger.info("Gemini AI integration configured with model=%s", settings.gemini_model)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    dev_origins = {"http://localhost:5173", "http://127.0.0.1:5173"}
    configured_raw = [o.strip().rstrip("/") for o in settings.frontend_origin.split(",") if o.strip()]
    allowed_origins = sorted(dev_origins.union(configured_raw))

    app = FastAPI(
        title="JohnnySummUP API",
        description="Phase 1 account and authentication API.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = str(uuid4())
        logger.exception("unhandled_server_exception request_id=%s path=%s exc=%s", request_id, request.url.path, exc)
        origin = request.headers.get("origin")
        headers: dict[str, str] = {}
        if origin and origin in allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Vary"] = "Origin"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please try again.",
                    "request_id": request_id,
                }
            },
            headers=headers,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
