from pathlib import Path
import os
import tempfile

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

test_database_url = os.environ.get("TEST_DATABASE_URL")
if not test_database_url:
    # Default to SQLite in-memory for zero-dependency local testing
    test_database_url = "sqlite+pysqlite:///:memory:"
    os.environ["TEST_DATABASE_URL"] = test_database_url

if test_database_url.startswith("postgresql"):
    test_url = make_url(test_database_url)
    if "test" not in (test_url.database or "").lower():
        raise RuntimeError("TEST_DATABASE_URL must target a database whose name contains 'test'.")

    backend_env = Path(__file__).resolve().parents[1] / ".env"
    configured_database_url = dotenv_values(backend_env).get("DATABASE_URL")
    if configured_database_url:
        configured_url = make_url(configured_database_url)
        test_host = (test_url.host or "").lower()
        configured_host = (configured_url.host or "").lower()
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        same_host = test_host == configured_host or (
            test_host in local_hosts and configured_host in local_hosts
        )
        if (
            same_host
            and (test_url.port or 5432) == (configured_url.port or 5432)
            and test_url.database == configured_url.database
        ):
            raise RuntimeError("TEST_DATABASE_URL must not point at the configured application database.")

os.environ["DATABASE_URL"] = test_database_url
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("FRONTEND_ORIGIN", "http://127.0.0.1:5173")
os.environ["MEDICAL_STORAGE_PATH"] = tempfile.mkdtemp(prefix="johnnysummup-test-uploads-")
