from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jose import JWTError
from loguru import logger

from app.core import messages


# ── Custom exception classes ──────────────────────────────────────────────────

class AppError(Exception):
    """Base class for all application-level errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str = "An unexpected error occurred."):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"


# ── Error response helper ─────────────────────────────────────────────────────

def _error_body(code: str, detail: str | list, request_id: str | None = None) -> dict:
    body: dict = {"error": {"code": code, "detail": detail}}
    if request_id:
        body["request_id"] = request_id
    return body


# ── Handler registration ──────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning(
            "AppError",
            code=exc.code,
            detail=exc.detail,
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.detail, request_id),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning(
            "HTTPException",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", exc.detail, request_id),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        errors = [
            {"field": " → ".join(str(l) for l in e["loc"]), "msg": e["msg"]}
            for e in exc.errors()
        ]
        logger.warning(
            "ValidationError",
            errors=errors,
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("VALIDATION_ERROR", errors, request_id),
        )

    @app.exception_handler(JWTError)
    async def jwt_error_handler(request: Request, exc: JWTError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning("JWTError", detail=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_error_body("INVALID_TOKEN", messages.TOKEN_INVALID_OR_EXPIRED, request_id),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", messages.INTERNAL_ERROR, request_id),
        )
