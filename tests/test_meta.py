"""Health check, error envelope and routing behaviour."""

from pathlib import Path

from app import __version__


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_health_returns_json_content_type(client):
    response = client.get("/health")
    assert response.headers["content-type"].startswith("application/json")


def test_openapi_schema_documents_every_resource(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in ("/students", "/students/{student_id}", "/courses", "/enrollments"):
        assert path in paths


def test_unknown_route_returns_404_envelope(client):
    response = client.get("/students-typo")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unsupported_method_returns_405_envelope(client, student):
    response = client.patch(f"/students/{student['id']}", json={"name": "New"})
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_every_error_response_uses_the_same_envelope(client):
    responses = [
        client.get("/students/9999"),
        client.post("/students", json={"name": "No Email"}),
        client.post("/enrollments", json={"student_id": 1, "course_id": 1}),
    ]
    for response in responses:
        body = response.json()
        assert response.status_code >= 400
        assert set(body) == {"error"}
        assert isinstance(body["error"]["code"], str)
        assert isinstance(body["error"]["message"], str)


def test_test_run_does_not_create_the_production_database_file():
    assert not Path("students.db").exists()
