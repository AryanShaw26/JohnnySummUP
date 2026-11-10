from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    frontend_origin: str = "http://127.0.0.1:5173"
    cookie_secure: bool = False
    openai_api_key: SecretStr | None = None
<<<<<<< HEAD
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = Field(default="gpt-4o-mini", min_length=1, max_length=120)
=======
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-1.5-flash"
    default_ai_provider: Literal["openai", "gemini"] = "openai"
    tesseract_cmd: str | None = None
>>>>>>> aryan
    medical_storage_path: Path = BACKEND_ROOT / "private_uploads"
    medical_max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    medical_allowed_mime_types: list[str] = ["application/pdf", "image/jpeg", "image/png"]
    medical_allowed_extensions: list[str] = [".pdf", ".jpg", ".jpeg", ".png"]

    @field_validator("jwt_secret_key")
    @classmethod
    def require_strong_jwt_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or secret.startswith("REPLACE_WITH_"):
            raise ValueError("JWT_SECRET_KEY must be a randomly generated secret of at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def require_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must not be empty")
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_optional_openai_key(cls, value):
        if value is None or not str(value).strip():
            return None
        return value

<<<<<<< HEAD
    @field_validator("openai_base_url")
    @classmethod
    def validate_openai_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("OPENAI_BASE_URL must be an HTTP(S) base URL without a query or fragment")
        return value
=======
    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def normalize_optional_gemini_key(cls, value):
        if value is not None and str(value).strip():
            return str(value).strip()
        import os
        google_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if google_key:
            return google_key
        return None
>>>>>>> aryan


@lru_cache
def get_settings() -> Settings:
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    load_dotenv(PROJECT_ROOT / "api.txt", override=False)
    return Settings()
