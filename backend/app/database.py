"""SQLite setup.

What this file does:
    Opens the local database file and creates tables that do not exist yet.

What enters:
    No user data. The API calls init_db() when the process starts.

What happens inside:
    SQLAlchemy connects to backend/turning_point.db. create_all() adds the
    profile and life-event tables. An existing file is left in place.

What it returns:
    A session factory. Other services use session_scope() to read and write rows.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = BACKEND_DIR / "turning_point.db"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    """Shared base class for the SQLAlchemy models."""


def database_path() -> Path:
    """Return the SQLite file path. Tests can override it with TURNING_POINT_DB."""

    override = os.environ.get("TURNING_POINT_DB")
    if override:
        return Path(override)
    return DEFAULT_DATABASE_PATH


def close_db() -> None:
    """Close the current connection. Tests call this before deleting a temp file."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def init_db() -> None:
    """Create the database file and tables. Safe to call more than once."""

    global _engine, _session_factory

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if _engine is not None:
        _engine.dispose()

    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Import models here so their tables are registered before create_all().
    from app.models.profile import LifeEvent, UserProfile  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _restrict_database_file(path)
    _engine = engine
    _session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _restrict_database_file(path: Path) -> None:
    """Keep birth details and life events readable only by this user."""

    if path.exists():
        os.chmod(path, 0o600)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a database session, commit on success, and roll back on failure."""

    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    db = _session_factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
