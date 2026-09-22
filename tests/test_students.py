"""Student endpoints: create, read, list, replace, delete."""

import pytest

from .conftest import post_course, post_enrollment, post_student


def test_create_student_returns_201_with_generated_id(client):
    response = client.post("/students", json={"name": "Alex Chen", "email": "alex@example.com"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "Alex Chen"
    assert body["email"] == "alex@example.com"


def test_created_student_is_persisted_and_retrievable(client):
    created = post_student(client)
    fetched = client.get(f"/students/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_create_student_lowercases_the_email(client):
    body = post_student(client, email="Alex.Chen@Example.COM")
    assert body["email"] == "alex.chen@example.com"


def test_create_student_strips_surrounding_whitespace(client):
    body = post_student(client, name="  Alex Chen  ")
    assert body["name"] == "Alex Chen"


def test_create_student_rejects_duplicate_email_with_409(client):
    post_student(client, email="dup@example.com")
    response = client.post("/students", json={"name": "Other", "email": "dup@example.com"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


def test_duplicate_email_check_ignores_case(client):
    post_student(client, email="dup@example.com")
    response = client.post("/students", json={"name": "Other", "email": "DUP@EXAMPLE.COM"})
    assert response.status_code == 409


def test_duplicate_email_does_not_create_a_second_record(client):
    post_student(client, email="dup@example.com")
    client.post("/students", json={"name": "Other", "email": "dup@example.com"})
    assert len(client.get("/students").json()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"email": "a@example.com"}, id="name-missing"),
        pytest.param({"name": "Alex"}, id="email-missing"),
        pytest.param({}, id="both-missing"),
    ],
)
def test_create_student_requires_every_field(client, payload):
    response = client.post("/students", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("name", ["", "   ", "\t"], ids=["empty", "spaces", "tab"])
def test_create_student_rejects_blank_name(client, name):
    response = client.post("/students", json={"name": name, "email": "a@example.com"})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "missing-domain@",
        "@example.com",
        "two@@example.com",
        "spaced out@example.com",
    ],
)
def test_create_student_rejects_malformed_email(client, email):
    response = client.post("/students", json={"name": "Alex", "email": email})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "email"


@pytest.mark.parametrize(
    ("payload", "bad_field"),
    [
        pytest.param({"name": 123, "email": "a@example.com"}, "name", id="name-number"),
        pytest.param({"name": None, "email": "a@example.com"}, "name", id="name-null"),
        pytest.param({"name": ["Alex"], "email": "a@example.com"}, "name", id="name-list"),
        pytest.param({"name": "Alex", "email": 42}, "email", id="email-number"),
    ],
)
def test_create_student_rejects_wrong_types(client, payload, bad_field):
    response = client.post("/students", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == bad_field


def test_create_student_rejects_unknown_fields(client):
    response = client.post(
        "/students", json={"name": "Alex", "email": "a@example.com", "gpa": 4.0}
    )
    assert response.status_code == 400
    assert "gpa" in response.text


def test_create_student_rejects_a_client_supplied_id(client):
    response = client.post(
        "/students", json={"id": 999, "name": "Alex", "email": "a@example.com"}
    )
    assert response.status_code == 400


def test_create_student_rejects_an_over_long_name(client):
    response = client.post("/students", json={"name": "a" * 101, "email": "a@example.com"})
    assert response.status_code == 400


def test_create_student_rejects_malformed_json(client):
    response = client.post(
        "/students",
        content=b'{"name": "Alex", ',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_validation_errors_name_the_offending_field(client):
    response = client.post("/students", json={"email": "a@example.com"})
    details = response.json()["error"]["details"]
    assert {"field": "name", "message": "Field required"} in details


def test_list_students_is_empty_before_anything_is_created(client):
    response = client.get("/students")
    assert response.status_code == 200
    assert response.json() == []


def test_list_students_returns_records_in_id_order(client):
    first = post_student(client, name="First", email="first@example.com")
    second = post_student(client, name="Second", email="second@example.com")
    assert [row["id"] for row in client.get("/students").json()] == [first["id"], second["id"]]


def test_list_students_filters_on_name(client):
    post_student(client, name="Alex Chen", email="alex@example.com")
    post_student(client, name="Bea Novak", email="bea@example.com")
    results = client.get("/students", params={"q": "novak"}).json()
    assert [row["name"] for row in results] == ["Bea Novak"]


def test_list_students_filters_on_email(client):
    post_student(client, name="Alex Chen", email="alex@example.com")
    post_student(client, name="Bea Novak", email="bea@other.org")
    results = client.get("/students", params={"q": "other.org"}).json()
    assert [row["email"] for row in results] == ["bea@other.org"]


def test_list_students_filter_is_case_insensitive(client):
    post_student(client, name="Alex Chen", email="alex@example.com")
    results = client.get("/students", params={"q": "ALEX"}).json()
    assert len(results) == 1


def test_list_students_filter_with_no_match_returns_an_empty_list(client):
    post_student(client)
    assert client.get("/students", params={"q": "nobody"}).json() == []


def test_get_unknown_student_returns_404_naming_the_id(client):
    response = client.get("/students/4242")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "4242" in error["message"]


def test_get_student_with_a_non_numeric_id_returns_400(client):
    response = client.get("/students/not-a-number")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_replace_student_updates_both_fields(client, student):
    response = client.put(
        f"/students/{student['id']}",
        json={"name": "Alexandra Chen", "email": "new@example.com"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": student["id"],
        "name": "Alexandra Chen",
        "email": "new@example.com",
    }


def test_replace_student_change_is_visible_on_the_next_read(client, student):
    client.put(f"/students/{student['id']}", json={"name": "Renamed", "email": "r@example.com"})
    assert client.get(f"/students/{student['id']}").json()["name"] == "Renamed"


def test_replace_student_requires_the_full_body(client, student):
    response = client.put(f"/students/{student['id']}", json={"name": "Only Name"})
    assert response.status_code == 400


def test_replace_student_may_keep_its_own_email(client, student):
    response = client.put(
        f"/students/{student['id']}", json={"name": "Renamed", "email": student["email"]}
    )
    assert response.status_code == 200


def test_replace_student_rejects_another_students_email(client, student):
    other = post_student(client, name="Bea", email="bea@example.com")
    response = client.put(
        f"/students/{other['id']}", json={"name": "Bea", "email": student["email"]}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


def test_replace_unknown_student_returns_404(client):
    response = client.put("/students/4242", json={"name": "Ghost", "email": "g@example.com"})
    assert response.status_code == 404


def test_delete_student_returns_204_with_an_empty_body(client, student):
    response = client.delete(f"/students/{student['id']}")
    assert response.status_code == 204
    assert response.content == b""


def test_deleted_student_can_no_longer_be_fetched(client, student):
    client.delete(f"/students/{student['id']}")
    assert client.get(f"/students/{student['id']}").status_code == 404


def test_deleting_the_same_student_twice_returns_404(client, student):
    assert client.delete(f"/students/{student['id']}").status_code == 204
    assert client.delete(f"/students/{student['id']}").status_code == 404


def test_deleting_a_student_removes_their_enrollments(client, student, course):
    post_enrollment(client, student["id"], course["id"])
    client.delete(f"/students/{student['id']}")
    assert client.get("/enrollments").json() == []


def test_deleting_a_student_leaves_other_students_alone(client, student):
    keeper = post_student(client, name="Bea", email="bea@example.com")
    client.delete(f"/students/{student['id']}")
    assert [row["id"] for row in client.get("/students").json()] == [keeper["id"]]


def test_student_enrollments_lists_only_that_students_records(client, student, course):
    other_student = post_student(client, name="Bea", email="bea@example.com")
    other_course = post_course(client, code="MA200", title="Linear Algebra")
    mine = post_enrollment(client, student["id"], course["id"])
    post_enrollment(client, other_student["id"], other_course["id"])

    response = client.get(f"/students/{student['id']}/enrollments")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [mine["id"]]


def test_student_enrollments_is_empty_for_a_student_with_none(client, student):
    assert client.get(f"/students/{student['id']}/enrollments").json() == []


def test_student_enrollments_for_an_unknown_student_returns_404(client):
    assert client.get("/students/4242/enrollments").status_code == 404
