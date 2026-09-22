"""One JSON error shape for every failure the API can return.

Every error response looks like this, so clients only ever parse one envelope:

    {"error": {"code": "not_found", "message": "...", "details": [...]}}
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """An error the API raises deliberately, with the status code it should return."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def not_found(resource: str, resource_id: int) -> ApiError:
    """404 for a resource addressed by id that does not exist."""
    return ApiError(status.HTTP_404_NOT_FOUND, "not_found", f"{resource} {resource_id} was not found")


def conflict(code: str, message: str) -> ApiError:
    """409 for a request that clashes with data already stored."""
    return ApiError(status.HTTP_409_CONFLICT, code, message)


def bad_request(code: str, message: str) -> ApiError:
    """400 for a request whose body cannot be satisfied."""
    return ApiError(status.HTTP_400_BAD_REQUEST, code, message)


def error_response(status_code: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    """Render the error envelope."""
    error: dict = {"code": code, "message": message}
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def _field_path(location: tuple) -> str:
    """Turn a validation error location into a dotted field name the caller recognises."""
    parts = [str(part) for part in location if part not in {"body", "query", "path"}]
    return ".".join(parts) or "body"


def register_error_handlers(app: FastAPI) -> None:
    """Attach the handlers that keep every error response in the same shape."""

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Invalid input is reported as 400 rather than the framework default of 422,
        # so the API exposes a single status code for "your request was malformed".
        details = [
            {"field": _field_path(error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            "validation_error",
            "Request validation failed",
            details,
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        # Safety net: the routes check for duplicates first, but a database level
        # unique violation (two concurrent writers) is still a conflict, not a 500.
        return error_response(
            status.HTTP_409_CONFLICT,
            "conflict",
            "The request conflicts with data that already exists",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {
            status.HTTP_404_NOT_FOUND: "not_found",
            status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        }
        return error_response(
            exc.status_code,
            codes.get(exc.status_code, "http_error"),
            str(exc.detail),
        )
