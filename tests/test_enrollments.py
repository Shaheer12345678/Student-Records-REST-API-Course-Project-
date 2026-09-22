"""Enrollment endpoints, including referential checks and grade updates."""

import pytest

from .conftest import post_course, post_enrollment, post_student


def test_create_enrollment_returns_201_with_no_grade_yet(client, student, course):
    response = client.post(
        "/enrollments", json={"student_id": student["id"], "course_id": course["id"]}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["student_id"] == student["id"]
    assert body["course_id"] == course["id"]
    assert body["grade"] is None


def test_create_enrollment_accepts_a_grade_up_front(client, student, course):
    body = post_enrollment(client, student["id"], course["id"], grade="B")
    assert body["grade"] == "B"


def test_created_enrollment_is_retrievable(client, enrollment):
    response = client.get(f"/enrollments/{enrollment['id']}")
    assert response.status_code == 200
    assert response.json() == enrollment


def test_enrollment_for_an_unknown_student_returns_400(client, course):
    response = client.post(
        "/enrollments", json={"student_id": 4242, "course_id": course["id"]}
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "unknown_student"
    assert "4242" in error["message"]


def test_enrollment_for_an_unknown_course_returns_400(client, student):
    response = client.post("/enrollments", json={"student_id": student["id"], "course_id": 4242})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_course"


def test_enrollment_with_unknown_ids_creates_nothing(client):
    client.post("/enrollments", json={"student_id": 1, "course_id": 1})
    assert client.get("/enrollments").json() == []


def test_enrolling_the_same_student_twice_in_one_course_returns_409(client, enrollment):
    response = client.post(
        "/enrollments",
        json={"student_id": enrollment["student_id"], "course_id": enrollment["course_id"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_enrollment"


def test_duplicate_enrollment_does_not_create_a_second_row(client, enrollment):
    client.post(
        "/enrollments",
        json={"student_id": enrollment["student_id"], "course_id": enrollment["course_id"]},
    )
    assert len(client.get("/enrollments").json()) == 1


def test_one_student_may_take_several_courses(client, student, course):
    second_course = post_course(client, code="MA200", title="Linear Algebra")
    post_enrollment(client, student["id"], course["id"])
    post_enrollment(client, student["id"], second_course["id"])
    assert len(client.get("/enrollments").json()) == 2


def test_one_course_may_hold_several_students(client, student, course):
    second_student = post_student(client, name="Bea", email="bea@example.com")
    post_enrollment(client, student["id"], course["id"])
    post_enrollment(client, second_student["id"], course["id"])
    assert len(client.get("/enrollments", params={"course_id": course["id"]}).json()) == 2


@pytest.mark.parametrize(
    "grade",
    [
        pytest.param("E", id="unused-letter"),
        pytest.param("a", id="lowercase"),
        pytest.param("AA", id="two-letters"),
        pytest.param("", id="empty"),
        pytest.param("A+", id="modifier"),
    ],
)
def test_create_enrollment_rejects_an_invalid_grade(client, student, course, grade):
    response = client.post(
        "/enrollments",
        json={"student_id": student["id"], "course_id": course["id"], "grade": grade},
    )
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "grade"


@pytest.mark.parametrize("student_id", [0, -5], ids=["zero", "negative"])
def test_create_enrollment_rejects_non_positive_ids(client, course, student_id):
    response = client.post(
        "/enrollments", json={"student_id": student_id, "course_id": course["id"]}
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "course_id",
    [pytest.param("abc", id="word"), pytest.param(None, id="null"), pytest.param(1.5, id="fraction")],
)
def test_create_enrollment_rejects_ids_of_the_wrong_type(client, student, course_id):
    response = client.post(
        "/enrollments", json={"student_id": student["id"], "course_id": course_id}
    )
    assert response.status_code == 400


def test_create_enrollment_requires_both_ids(client):
    response = client.post("/enrollments", json={"student_id": 1})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "course_id"


def test_create_enrollment_rejects_unknown_fields(client, student, course):
    response = client.post(
        "/enrollments",
        json={"student_id": student["id"], "course_id": course["id"], "term": "Fall"},
    )
    assert response.status_code == 400


def test_list_enrollments_is_empty_before_anything_is_created(client):
    assert client.get("/enrollments").json() == []


def test_list_enrollments_filters_by_student(client, student, course):
    other_student = post_student(client, name="Bea", email="bea@example.com")
    mine = post_enrollment(client, student["id"], course["id"])
    post_enrollment(client, other_student["id"], course["id"])

    results = client.get("/enrollments", params={"student_id": student["id"]}).json()
    assert [row["id"] for row in results] == [mine["id"]]


def test_list_enrollments_filters_by_course(client, student, course):
    other_course = post_course(client, code="MA200", title="Linear Algebra")
    post_enrollment(client, student["id"], course["id"])
    target = post_enrollment(client, student["id"], other_course["id"])

    results = client.get("/enrollments", params={"course_id": other_course["id"]}).json()
    assert [row["id"] for row in results] == [target["id"]]


def test_list_enrollments_combines_both_filters(client, student, course):
    other_student = post_student(client, name="Bea", email="bea@example.com")
    other_course = post_course(client, code="MA200", title="Linear Algebra")
    target = post_enrollment(client, student["id"], course["id"])
    post_enrollment(client, other_student["id"], other_course["id"])

    results = client.get(
        "/enrollments", params={"student_id": student["id"], "course_id": course["id"]}
    ).json()
    assert [row["id"] for row in results] == [target["id"]]


def test_list_enrollments_filter_with_no_match_returns_an_empty_list(client, enrollment):
    assert client.get("/enrollments", params={"student_id": 4242}).json() == []


def test_list_enrollments_rejects_an_invalid_filter_value(client):
    response = client.get("/enrollments", params={"student_id": "abc"})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "student_id"


def test_get_unknown_enrollment_returns_404(client):
    response = client.get("/enrollments/4242")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("grade", ["A", "B", "C", "D", "F"])
def test_recording_each_valid_grade_returns_200(client, enrollment, grade):
    response = client.patch(f"/enrollments/{enrollment['id']}", json={"grade": grade})
    assert response.status_code == 200
    assert response.json()["grade"] == grade


def test_recorded_grade_survives_a_reread(client, enrollment):
    client.patch(f"/enrollments/{enrollment['id']}", json={"grade": "A"})
    assert client.get(f"/enrollments/{enrollment['id']}").json()["grade"] == "A"


def test_a_grade_can_be_cleared_with_null(client, enrollment):
    client.patch(f"/enrollments/{enrollment['id']}", json={"grade": "C"})
    response = client.patch(f"/enrollments/{enrollment['id']}", json={"grade": None})
    assert response.status_code == 200
    assert response.json()["grade"] is None


def test_patching_a_grade_leaves_the_ids_untouched(client, enrollment):
    body = client.patch(f"/enrollments/{enrollment['id']}", json={"grade": "A"}).json()
    assert body["student_id"] == enrollment["student_id"]
    assert body["course_id"] == enrollment["course_id"]


def test_patching_a_grade_requires_the_grade_field(client, enrollment):
    response = client.patch(f"/enrollments/{enrollment['id']}", json={})
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "grade"


def test_patching_a_grade_rejects_an_invalid_value(client, enrollment):
    response = client.patch(f"/enrollments/{enrollment['id']}", json={"grade": "Z"})
    assert response.status_code == 400


def test_patching_a_grade_rejects_unknown_fields(client, enrollment):
    response = client.patch(
        f"/enrollments/{enrollment['id']}", json={"grade": "A", "student_id": 99}
    )
    assert response.status_code == 400


def test_patching_an_unknown_enrollment_returns_404(client):
    response = client.patch("/enrollments/4242", json={"grade": "A"})
    assert response.status_code == 404


def test_delete_enrollment_returns_204_and_removes_it(client, enrollment):
    response = client.delete(f"/enrollments/{enrollment['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/enrollments/{enrollment['id']}").status_code == 404


def test_deleting_the_same_enrollment_twice_returns_404(client, enrollment):
    client.delete(f"/enrollments/{enrollment['id']}")
    assert client.delete(f"/enrollments/{enrollment['id']}").status_code == 404


def test_deleting_an_enrollment_keeps_the_student_and_course(client, enrollment):
    client.delete(f"/enrollments/{enrollment['id']}")
    assert client.get(f"/students/{enrollment['student_id']}").status_code == 200
    assert client.get(f"/courses/{enrollment['course_id']}").status_code == 200


def test_unenrolling_then_enrolling_again_is_allowed(client, enrollment):
    client.delete(f"/enrollments/{enrollment['id']}")
    response = client.post(
        "/enrollments",
        json={"student_id": enrollment["student_id"], "course_id": enrollment["course_id"]},
    )
    assert response.status_code == 201
