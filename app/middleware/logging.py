"""Per-request structured logging middleware (method, path, status, duration)."""
import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths that should NOT be logged (health checks, metrics)
_SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with method, path, status code, duration
    and request-id. Skips noisy health-check paths.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = getattr(request.state, "request_id", "-")
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error during request",
                method=request.method,
                path=request.url.path,
                request_id=request_id,
            )
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        log = logger.info if response.status_code < 400 else logger.warning
        log(
            f"{request.method} {request.url.path} → {response.status_code}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            request_id=request_id,
        )
        return response
