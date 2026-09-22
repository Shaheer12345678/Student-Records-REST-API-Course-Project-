"""Shared test fixtures.

Every test gets its own SQLite database held in memory, so tests never touch the
real database file and can run in any order or in isolation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session, reset_engine
from app.main import create_app


@pytest.fixture(scope="session", autouse=True)
def isolated_default_database():
    """Point the app's default engine at memory for the whole run.

    The per-test engine below is what the routes actually use, but the app also
    creates tables on startup. Redirecting the default engine makes it impossible
    for a test run to create or open the production students.db file.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_URL", "sqlite://")
        reset_engine()
        yield
    reset_engine()


@pytest.fixture(name="engine")
def engine_fixture():
    """A fresh in-memory database.

    StaticPool keeps every connection pointed at the same in-memory database;
    without it each new connection would see an empty one.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    """A session on the test database, for assertions that bypass the API."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine):
    """A test client whose requests run against the test database."""
    app = create_app()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def post_student(client, **overrides) -> dict:
    """Create a student through the API and return the response body."""
    payload = {"name": "Alex Chen", "email": "alex.chen@example.com"}
    payload.update(overrides)
    response = client.post("/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def post_course(client, **overrides) -> dict:
    """Create a course through the API and return the response body."""
    payload = {"code": "CS101", "title": "Intro to Computing", "credits": 3}
    payload.update(overrides)
    response = client.post("/courses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def post_enrollment(client, student_id: int, course_id: int, **overrides) -> dict:
    """Enrol a student through the API and return the response body."""
    payload = {"student_id": student_id, "course_id": course_id}
    payload.update(overrides)
    response = client.post("/enrollments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(name="student")
def student_fixture(client) -> dict:
    """An existing student."""
    return post_student(client)


@pytest.fixture(name="course")
def course_fixture(client) -> dict:
    """An existing course."""
    return post_course(client)


@pytest.fixture(name="enrollment")
def enrollment_fixture(client, student, course) -> dict:
    """An existing enrollment linking the student and course fixtures."""
    return post_enrollment(client, student["id"], course["id"])
