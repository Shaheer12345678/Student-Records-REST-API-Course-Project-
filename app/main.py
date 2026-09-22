"""Application entry point.

`create_app()` is a factory so tests can build an isolated instance of the API
instead of importing a module level singleton wired to the real database.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__
from .database import create_tables, get_engine
from .errors import register_error_handlers
from .routers import courses, enrollments, students

DESCRIPTION = "CRUD API for students, courses and the enrollments that link them."


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Make sure the tables exist before the first request is served."""
    create_tables(get_engine())
    yield


def create_app() -> FastAPI:
    """Build and configure the application."""
    app = FastAPI(
        title="Student Records REST API",
        description=DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
    )

    register_error_handlers(app)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe for containers and load balancers."""
        return {"status": "ok", "version": __version__}

    app.include_router(students.router)
    app.include_router(courses.router)
    app.include_router(enrollments.router)
    return app


app = create_app()
