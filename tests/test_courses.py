"""Course endpoints: create, read, list, replace, delete."""

import pytest

from .conftest import post_course, post_enrollment, post_student


def test_create_course_returns_201_with_generated_id(client):
    response = client.post(
        "/courses", json={"code": "CS101", "title": "Intro to Computing", "credits": 4}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["code"] == "CS101"
    assert body["title"] == "Intro to Computing"
    assert body["credits"] == 4


def test_create_course_uppercases_the_code(client):
    assert post_course(client, code="cs101")["code"] == "CS101"


def test_create_course_defaults_credits_to_three(client):
    response = client.post("/courses", json={"code": "CS102", "title": "Data Structures"})
    assert response.status_code == 201
    assert response.json()["credits"] == 3


def test_create_course_strips_whitespace_from_the_title(client):
    assert post_course(client, title="  Intro to Computing  ")["title"] == "Intro to Computing"


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("C101", id="one-letter-prefix"),
        pytest.param("COMPSCI101", id="prefix-too-long"),
        pytest.param("CS10", id="two-digits"),
        pytest.param("CS1011", id="four-digits"),
        pytest.param("101CS", id="digits-first"),
        pytest.param("CS-101", id="separator"),
        pytest.param("", id="empty"),
    ],
)
def test_create_course_rejects_codes_that_do_not_match_the_format(client, code):
    response = client.post("/courses", json={"code": code, "title": "Something"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "code"


def test_create_course_rejects_a_duplicate_code_with_409(client):
    post_course(client, code="CS101")
    response = client.post("/courses", json={"code": "CS101", "title": "Duplicate"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_code"


def test_duplicate_course_code_check_ignores_case(client):
    post_course(client, code="CS101")
    response = client.post("/courses", json={"code": "cs101", "title": "Duplicate"})
    assert response.status_code == 409


@pytest.mark.parametrize("credits", [0, -1, 7, 100], ids=["zero", "negative", "seven", "hundred"])
def test_create_course_rejects_credits_outside_the_allowed_range(client, credits):
    response = client.post(
        "/courses", json={"code": "CS101", "title": "Intro", "credits": credits}
    )
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "credits"


@pytest.mark.parametrize(
    "credits",
    [pytest.param("three", id="word"), pytest.param(3.5, id="fraction"), pytest.param(None, id="null")],
)
def test_create_course_rejects_credits_of_the_wrong_type(client, credits):
    response = client.post(
        "/courses", json={"code": "CS101", "title": "Intro", "credits": credits}
    )
    assert response.status_code == 400


def test_create_course_requires_a_title(client):
    response = client.post("/courses", json={"code": "CS101"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "title"


def test_create_course_rejects_a_blank_title(client):
    response = client.post("/courses", json={"code": "CS101", "title": "   "})
    assert response.status_code == 400


def test_create_course_rejects_unknown_fields(client):
    response = client.post(
        "/courses", json={"code": "CS101", "title": "Intro", "department": "Science"}
    )
    assert response.status_code == 400
    assert "department" in response.text


def test_list_courses_is_empty_before_anything_is_created(client):
    assert client.get("/courses").json() == []


def test_list_courses_returns_records_in_id_order(client):
    first = post_course(client, code="CS101", title="Intro")
    second = post_course(client, code="MA200", title="Linear Algebra")
    assert [row["id"] for row in client.get("/courses").json()] == [first["id"], second["id"]]


def test_list_courses_filters_on_code(client):
    post_course(client, code="CS101", title="Intro")
    post_course(client, code="MA200", title="Linear Algebra")
    results = client.get("/courses", params={"q": "ma2"}).json()
    assert [row["code"] for row in results] == ["MA200"]


def test_list_courses_filters_on_title(client):
    post_course(client, code="CS101", title="Intro to Computing")
    post_course(client, code="MA200", title="Linear Algebra")
    results = client.get("/courses", params={"q": "algebra"}).json()
    assert [row["code"] for row in results] == ["MA200"]


def test_get_course_returns_the_stored_record(client, course):
    response = client.get(f"/courses/{course['id']}")
    assert response.status_code == 200
    assert response.json() == course


def test_get_unknown_course_returns_404(client):
    response = client.get("/courses/4242")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_replace_course_updates_every_field(client, course):
    response = client.put(
        f"/courses/{course['id']}",
        json={"code": "CS999", "title": "Capstone", "credits": 6},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": course["id"],
        "code": "CS999",
        "title": "Capstone",
        "credits": 6,
    }


def test_replace_course_may_keep_its_own_code(client, course):
    response = client.put(
        f"/courses/{course['id']}", json={"code": course["code"], "title": "Renamed"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


def test_replace_course_rejects_another_courses_code(client, course):
    other = post_course(client, code="MA200", title="Linear Algebra")
    response = client.put(
        f"/courses/{other['id']}", json={"code": course["code"], "title": "Clash"}
    )
    assert response.status_code == 409


def test_replace_unknown_course_returns_404(client):
    response = client.put("/courses/4242", json={"code": "CS101", "title": "Ghost"})
    assert response.status_code == 404


def test_replace_course_validates_the_body(client, course):
    response = client.put(f"/courses/{course['id']}", json={"code": "bad", "title": "Intro"})
    assert response.status_code == 400


def test_delete_course_returns_204_and_removes_it(client, course):
    assert client.delete(f"/courses/{course['id']}").status_code == 204
    assert client.get(f"/courses/{course['id']}").status_code == 404


def test_deleting_the_same_course_twice_returns_404(client, course):
    client.delete(f"/courses/{course['id']}")
    assert client.delete(f"/courses/{course['id']}").status_code == 404


def test_deleting_a_course_removes_its_enrollments_but_keeps_the_student(client, student, course):
    post_enrollment(client, student["id"], course["id"])
    client.delete(f"/courses/{course['id']}")
    assert client.get("/enrollments").json() == []
    assert client.get(f"/students/{student['id']}").status_code == 200


def test_deleting_a_course_leaves_other_courses_alone(client, course):
    keeper = post_course(client, code="MA200", title="Linear Algebra")
    client.delete(f"/courses/{course['id']}")
    assert [row["id"] for row in client.get("/courses").json()] == [keeper["id"]]


def test_courses_and_students_use_separate_id_sequences(client):
    student = post_student(client)
    course = post_course(client)
    assert student["id"] == course["id"] == 1
