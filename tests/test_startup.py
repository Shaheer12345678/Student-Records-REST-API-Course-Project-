"""Engine and startup behaviour, including the parallel worker table race."""

import threading

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlmodel import SQLModel, create_engine

from app.config import DEFAULT_DATABASE_URL, Settings, get_settings
from app.database import build_engine, create_tables, get_engine, reset_engine


def test_settings_fall_back_to_the_default_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_settings().database_url == DEFAULT_DATABASE_URL


def test_settings_read_the_database_url_from_the_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./somewhere-else.db")
    assert get_settings().database_url == "sqlite:///./somewhere-else.db"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("true", True), ("YES", True), ("0", False), ("off", False)],
)
def test_sql_echo_is_read_from_the_environment(monkeypatch, value, expected):
    monkeypatch.setenv("SQL_ECHO", value)
    assert get_settings().echo_sql is expected


def test_engine_is_cached_between_calls(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    reset_engine()
    try:
        assert get_engine() is get_engine()
    finally:
        reset_engine()


def test_resetting_the_engine_picks_up_a_new_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    reset_engine()
    try:
        first = get_engine()
        reset_engine()
        assert get_engine() is not first
    finally:
        reset_engine()


def test_build_engine_lets_a_sqlite_connection_cross_threads(tmp_path):
    """The server hands requests to a thread pool, so this has to be allowed."""
    engine = build_engine(Settings(database_url=f"sqlite:///{tmp_path / 'threads.db'}", echo_sql=False))
    create_tables(engine)
    connection = engine.connect()
    failures: list[Exception] = []

    def read_from_another_thread() -> None:
        try:
            connection.exec_driver_sql("select count(*) from student").scalar()
        except Exception as exc:  # noqa: BLE001 - the failure itself is the result
            failures.append(exc)

    thread = threading.Thread(target=read_from_another_thread)
    thread.start()
    thread.join()
    connection.close()
    engine.dispose()

    assert failures == []


def test_create_tables_creates_every_model_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'startup.db'}")
    create_tables(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"student", "course", "enrollment"} <= tables
    engine.dispose()


def test_create_tables_is_safe_to_call_twice(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'startup.db'}")
    create_tables(engine)
    create_tables(engine)
    assert "student" in inspect(engine).get_table_names()
    engine.dispose()


def test_create_tables_tolerates_a_losing_race_when_the_tables_exist(tmp_path, monkeypatch):
    """A second worker that loses the create race must not crash the process."""
    engine = create_engine(f"sqlite:///{tmp_path / 'startup.db'}")
    create_tables(engine)

    def raise_already_exists(*_args, **_kwargs):
        raise OperationalError("CREATE TABLE student", {}, Exception("table student already exists"))

    monkeypatch.setattr(SQLModel.metadata, "create_all", raise_already_exists)
    create_tables(engine)
    engine.dispose()


def test_create_tables_still_raises_when_the_tables_are_missing(tmp_path, monkeypatch):
    """A genuine database failure must not be swallowed by that tolerance."""
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")

    def raise_operational_error(*_args, **_kwargs):
        raise OperationalError("CREATE TABLE student", {}, Exception("disk I/O error"))

    monkeypatch.setattr(SQLModel.metadata, "create_all", raise_operational_error)
    with pytest.raises(OperationalError):
        create_tables(engine)
    engine.dispose()
