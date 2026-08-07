"""Global RFC 9457 (ProblemDetails) error handling.

The Python analog of the .NET baseline's global ``UseExceptionHandler`` that returns a
``ProblemDetails`` payload. Every error response uses the ``application/problem+json``
media type with a consistent shape, so API callers get a machine-readable error instead
of a stack trace or an inconsistent body.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger("app.errors")

PROBLEM_JSON = "application/problem+json"


def problem_response(status: int, title: str, detail: str | None = None, **extra) -> JSONResponse:
    body: dict[str, object] = {"type": "about:blank", "title": title, "status": status}
    if detail is not None:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def add_problem_details_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else None
        return problem_response(exc.status_code, "HTTP error", detail=detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            422,
            "Validation failed",
            detail="One or more validation errors occurred.",
            errors=jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception processing %s %s", request.method, request.url.path)
        return problem_response(500, "Internal Server Error")
