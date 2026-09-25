"""Make ``backend/`` and repo root importable; give each test a fresh SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
for path in (_BACKEND, _ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("MODEL_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("PROMPT_VERSION", "m1-v2")

    from app.config import get_settings
    from app.db.session import init_db, reset_engine
    from app.main import create_app

    get_settings.cache_clear()
    reset_engine()
    application = create_app(database_url=f"sqlite:///{db_path}")
    yield application
    reset_engine()
    get_settings.cache_clear()


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)
