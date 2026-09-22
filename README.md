# Student Records REST API

[![CI](https://github.com/Shaheer12345678/Student-Records-REST-API-Course-Project-/actions/workflows/ci.yml/badge.svg)](https://github.com/Shaheer12345678/Student-Records-REST-API-Course-Project-/actions/workflows/ci.yml)

A REST API for managing student records: students, courses, and the enrollments
that link them. It covers full CRUD on every resource, validates all input, and
returns one consistent JSON error shape for every failure.

The project ships with 159 tests, a container image that runs under Gunicorn,
and a CI pipeline that runs the suite and builds the image on every push.

## Tech stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.11 |
| Web framework | FastAPI (ASGI) |
| Validation | Pydantic v2 request and response models |
| Persistence | SQLModel over SQLAlchemy 2, SQLite by default |
| Server | Gunicorn supervising Uvicorn workers |
| Tests | pytest with FastAPI's `TestClient` |
| Container | Docker, plus Docker Compose for one command startup |
| CI | GitHub Actions |

Because the database URL is read from the environment, the same image runs
against SQLite for a demo or against PostgreSQL by setting `DATABASE_URL`.

## Endpoints

| Method | Path | Description | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | `/health` | Liveness probe used by Docker and load balancers | 200 | |
| POST | `/students` | Create a student | 201 | 400, 409 |
| GET | `/students` | List students, optional `?q=` name or email filter | 200 | 400 |
| GET | `/students/{id}` | Fetch one student | 200 | 400, 404 |
| PUT | `/students/{id}` | Replace a student's details | 200 | 400, 404, 409 |
| DELETE | `/students/{id}` | Delete a student and their enrollments | 204 | 400, 404 |
| GET | `/students/{id}/enrollments` | List one student's enrollments | 200 | 400, 404 |
| POST | `/courses` | Create a course | 201 | 400, 409 |
| GET | `/courses` | List courses, optional `?q=` code or title filter | 200 | 400 |
| GET | `/courses/{id}` | Fetch one course | 200 | 400, 404 |
| PUT | `/courses/{id}` | Replace a course's details | 200 | 400, 404, 409 |
| DELETE | `/courses/{id}` | Delete a course and its enrollments | 204 | 400, 404 |
| POST | `/enrollments` | Enrol a student in a course | 201 | 400, 409 |
| GET | `/enrollments` | List enrollments, optional `?student_id=` and `?course_id=` filters | 200 | 400 |
| GET | `/enrollments/{id}` | Fetch one enrollment | 200 | 400, 404 |
| PATCH | `/enrollments/{id}` | Record or clear a grade | 200 | 400, 404 |
| DELETE | `/enrollments/{id}` | Delete an enrollment | 204 | 400, 404 |

Interactive documentation generated from the code is served at `/docs`, and the
OpenAPI schema at `/openapi.json`.

### Status codes

| Code | Meaning in this API |
| --- | --- |
| 200 | Read or update succeeded |
| 201 | Resource created, body contains the stored record with its new `id` |
| 204 | Delete succeeded, no body |
| 400 | The request body, path, or query string failed validation, or it referenced an id that does not exist |
| 404 | The resource addressed in the path does not exist |
| 405 | The path exists but not for that method |
| 409 | The request clashes with stored data: duplicate email, duplicate course code, or duplicate enrollment |

### Validation rules

| Field | Rule |
| --- | --- |
| `name` | 1 to 100 characters after trimming whitespace |
| `email` | Valid address, at most 254 characters, stored lowercase, unique across students |
| `code` | Two to four letters followed by three digits, for example `CS101`, stored uppercase, unique across courses |
| `title` | 1 to 200 characters after trimming whitespace |
| `credits` | Integer from 1 to 6, defaults to 3 |
| `grade` | One of `A`, `B`, `C`, `D`, `F`, or `null` |
| `student_id`, `course_id` | Positive integers that must reference existing records |

Unknown fields are rejected rather than ignored, and a client cannot supply its
own `id` on a create.

## Example requests

Create a student:

```bash
curl -i -X POST http://localhost:8000/students \
  -H 'Content-Type: application/json' \
  -d '{"name": "Alex Chen", "email": "alex.chen@example.com"}'
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id": 1, "name": "Alex Chen", "email": "alex.chen@example.com"}
```

Enrol that student in a course:

```bash
curl -X POST http://localhost:8000/enrollments \
  -H 'Content-Type: application/json' \
  -d '{"student_id": 1, "course_id": 1}'
```

```json
{"id": 1, "student_id": 1, "course_id": 1, "grade": null}
```

Record a grade:

```bash
curl -X PATCH http://localhost:8000/enrollments/1 \
  -H 'Content-Type: application/json' \
  -d '{"grade": "A"}'
```

```json
{"id": 1, "student_id": 1, "course_id": 1, "grade": "A"}
```

Every error uses the same envelope, so a client only parses one shape:

```bash
curl -i -X POST http://localhost:8000/students \
  -H 'Content-Type: application/json' \
  -d '{"name": "", "email": "not-an-email"}'
```

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [
      {"field": "name", "message": "String should have at least 1 character"},
      {"field": "email", "message": "value is not a valid email address: An email address must have an @-sign."}
    ]
  }
}
```

A duplicate email returns 409:

```json
{
  "error": {
    "code": "duplicate_email",
    "message": "A student with email alex.chen@example.com already exists"
  }
}
```

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is then on <http://localhost:8000>, with documentation at
<http://localhost:8000/docs>. Tables are created on startup, and by default the
data lands in `students.db` beside the project.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./students.db` | SQLAlchemy connection URL |
| `SQL_ECHO` | `0` | Set to `1` to log every SQL statement |
| `PORT` | `8000` | Port the container binds to |
| `WEB_CONCURRENCY` | `2` | Number of Gunicorn workers |

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

Every test runs against its own SQLite database held in memory, created and
thrown away by the fixtures in `tests/conftest.py`. Nothing touches
`students.db`, and the suite passes in any order.

```bash
pytest -q                     # short output
pytest --collect-only -q      # list every test
pytest tests/test_students.py # one module
pytest -k enrollment          # one area
```

## Running with Docker

One command, using Compose:

```bash
docker compose up --build
```

Or with Docker directly:

```bash
docker build -t student-records-api .
docker run --rm -p 8000:8000 student-records-api
curl http://localhost:8000/health
```

The image runs Gunicorn with Uvicorn workers rather than the development server,
installs pinned dependencies, drops to a non-root user, takes its port and
database URL from the environment, and declares a `HEALTHCHECK` against
`/health`. Compose keeps the database in a named volume so records survive a
rebuild.

SQLite serialises writes, so for real concurrent traffic point `DATABASE_URL` at
PostgreSQL and raise `WEB_CONCURRENCY`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

1. Install pinned dependencies on Python 3.11.
2. Run the full pytest suite.
3. Build the Docker image.
4. Start the container and check that `/health` responds and that a student can
   be created and listed back through the running container.

## Project layout

```
app/
  main.py               create_app() factory, /health, router wiring
  config.py             settings read from environment variables
  database.py           engine creation and the request scoped session
  models.py             SQLModel tables and constraints
  schemas.py            request and response models
  errors.py             one JSON error envelope for every failure
  routers/
    students.py         student routes
    courses.py          course routes
    enrollments.py      enrollment routes
tests/
  conftest.py           per test in-memory database and test client fixtures
  test_meta.py          health, error envelope, routing
  test_students.py      student endpoints
  test_courses.py       course endpoints
  test_enrollments.py   enrollment endpoints
  test_startup.py       configuration, engine and startup behaviour
  test_isolation.py     proof the fixtures isolate each test
```
