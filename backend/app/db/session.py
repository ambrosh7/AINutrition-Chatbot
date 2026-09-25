"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    raw = url.removeprefix("sqlite:///")
    # Ignore SQLAlchemy sqlite:///:memory: style if ever used
    if raw == ":memory:" or raw.startswith("file:"):
        return
    path = Path(raw)
    if path.parent and str(path.parent) not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)


def reset_engine() -> None:
    """Clear cached engine (tests that swap DATABASE_URL)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db(database_url: str | None = None) -> Engine:
    """Create tables and install the process-wide session factory."""
    global _engine, _SessionLocal
    reset_engine()
    url = database_url or get_settings().database_url
    _ensure_sqlite_parent(url)

    connect_args = {}
    if url.startswith("sqlite:"):
        connect_args["check_same_thread"] = False

    engine = create_engine(url, future=True, connect_args=connect_args)

    if url.startswith("sqlite:"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    _engine = engine
    _SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
