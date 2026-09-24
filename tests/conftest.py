"""Isolate test database/files and provide authenticated staff API clients."""

import os
import tempfile
from pathlib import Path

test_root = Path(tempfile.mkdtemp(prefix="arav-tests-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(test_root / 'test.db').as_posix()}",
    STORAGE_PATH=str(test_root / "documents"),
    DEMO_MODE="true",
    SEED_DEMO="false",
    WORKER_ENABLED="false",
    AI_PROVIDER="demo",
    EMBEDDINGS_ENABLED="false",
    APP_ENV="development",
    ADMIN_EMAIL="admin@arav.local",
    ADMIN_PASSWORD="ChangeMe-Demo-2026!",
    COOKIE_SECURE="false",
)

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import auth_attempts
from database.models import Base
from database.session import engine


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    auth_attempts.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app, headers={"X-Arav-Request": "1"}) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "admin@arav.local", "password": "ChangeMe-Demo-2026!"},
        )
        assert response.status_code == 200
        yield client
