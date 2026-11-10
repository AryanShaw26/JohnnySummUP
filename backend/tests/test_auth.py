from collections.abc import Generator
import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import get_db, get_engine, get_session_factory
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.core.security import verify_password

from sqlalchemy.pool import StaticPool

db_url = os.environ["TEST_DATABASE_URL"]
if "sqlite" in db_url:
    test_engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    test_engine = create_engine(db_url, pool_pre_ping=True)
TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def test_settings_reject_placeholder_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://user:password@localhost:5432/test_db",
            jwt_secret_key="REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS",
        )


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(test_engine)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    with TestSession() as session:
        session.execute(delete(User))
        session.commit()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def test_registration_login_profile_and_logout(client: TestClient) -> None:
    registration = client.post(
        "/api/auth/register",
        json={"full_name": "  Ada   Lovelace ", "email": "ADA@example.com", "password": "secure-pass-123"},
    )
    assert registration.status_code == 201
    assert registration.json()["full_name"] == "Ada Lovelace"
    assert registration.json()["email"] == "ada@example.com"
    assert "password_hash" not in registration.json()
    assert "access_token" in client.cookies
    assert "httponly" in registration.headers["set-cookie"].lower()
    assert "samesite=lax" in registration.headers["set-cookie"].lower()
    assert "secure" not in registration.headers["set-cookie"].lower()

    with TestSession() as session:
        stored_user = session.get(User, registration.json()["id"])
        assert stored_user is not None
        assert stored_user.password_hash.startswith("$argon2id$")
        assert verify_password("secure-pass-123", stored_user.password_hash)

    profile = client.get("/api/users/me")
    assert profile.status_code == 200
    assert profile.json()["email"] == "ada@example.com"

    duplicate = client.post(
        "/api/auth/register",
        json={"full_name": "Another Ada", "email": "ada@example.com", "password": "secure-pass-123"},
    )
    assert duplicate.status_code == 409

    client.post("/api/auth/logout")
    assert client.get("/api/users/me").status_code == 401


def test_login_uses_generic_error_and_protected_profile(client: TestClient) -> None:
    assert client.get("/api/users/me").status_code == 401

    client.post(
        "/api/auth/register",
        json={"full_name": "Grace Hopper", "email": "grace@example.com", "password": "secure-pass-123"},
    )
    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"email": "grace@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

    response = client.post(
        "/api/auth/login",
        json={"email": "grace@example.com", "password": "secure-pass-123"},
    )
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/api/users/me").status_code == 200


def test_cors_allows_local_vite_origins(client: TestClient) -> None:
    for origin in ("http://127.0.0.1:5173", "http://localhost:5173"):
        response = client.options(
            "/api/auth/register",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
