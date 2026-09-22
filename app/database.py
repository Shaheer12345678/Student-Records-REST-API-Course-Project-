"""Engine and session management."""

from collections.abc import Iterator

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from .config import Settings, get_settings

_engine: Engine | None = None


def build_engine(settings: Settings) -> Engine:
    """Create a new engine for the given settings."""
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite guards connections against cross-thread use; the server needs it off.
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, echo=settings.echo_sql, connect_args=connect_args)


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings())
    return _engine


def reset_engine() -> None:
    """Drop the cached engine so the next call re-reads the environment."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def create_tables(engine: Engine) -> None:
    """Create any missing tables for the registered models.

    Workers boot in parallel, so two of them can pass create_all's "does this
    table exist" check at the same moment and the loser gets an "already exists"
    error. That race is harmless as long as the tables end up present, so it is
    only re-raised when something is genuinely missing.
    """
    try:
        SQLModel.metadata.create_all(engine)
    except OperationalError:
        existing = set(inspect(engine).get_table_names())
        if set(SQLModel.metadata.tables) - existing:
            raise


def get_session() -> Iterator[Session]:
    """Yield a request-scoped session; overridden in tests to point at a temp database."""
    with Session(get_engine()) as session:
        yield session
