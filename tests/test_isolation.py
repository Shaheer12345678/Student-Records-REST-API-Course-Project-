"""Proof that the fixtures really do isolate one test from the next.

These two pairs of tests write the same rows. They only pass if each test gets a
fresh database, which is also what lets the suite run in any order.
"""

from sqlmodel import select

from app.models import Student

from .conftest import post_student


def test_first_write_of_the_shared_email_succeeds(client):
    assert post_student(client, email="shared@example.com")["id"] == 1


def test_second_write_of_the_shared_email_also_succeeds(client):
    assert post_student(client, email="shared@example.com")["id"] == 1


def test_database_is_empty_at_the_start_of_a_test(client):
    assert client.get("/students").json() == []
    assert client.get("/courses").json() == []
    assert client.get("/enrollments").json() == []


def test_rows_written_through_the_api_are_visible_to_the_session_fixture(client, session):
    created = post_student(client)
    stored = session.exec(select(Student).where(Student.id == created["id"])).one()
    assert stored.email == created["email"]


def test_rows_written_through_the_session_are_visible_to_the_api(client, session):
    session.add(Student(name="Direct Write", email="direct@example.com"))
    session.commit()
    assert [row["name"] for row in client.get("/students").json()] == ["Direct Write"]
