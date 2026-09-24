"""Verify a fresh versioned schema and bounded streaming without a live provider."""

import asyncio
import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect

from backend.body_limit import BodyLimitMiddleware
from database.models import Base


def test_fresh_migration_and_repeated_upgrade(tmp_path):
    path = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{path.as_posix()}"}
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    engine = create_engine(env["DATABASE_URL"])
    assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
    engine.dispose()


def test_chunked_body_limit_rejects_before_application():
    calls, sent = [], []
    messages = iter(
        [
            {"type": "http.request", "body": b"abcd", "more_body": True},
            {"type": "http.request", "body": b"efgh", "more_body": False},
        ]
    )

    async def application(scope, receive, send):
        calls.append(True)

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    asyncio.run(
        BodyLimitMiddleware(application, 5)({"type": "http", "method": "POST"}, receive, send)
    )
    assert not calls
    assert sent[0]["status"] == 413
