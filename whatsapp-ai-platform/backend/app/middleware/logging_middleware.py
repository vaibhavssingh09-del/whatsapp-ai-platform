"""
Binds a request_id + basic request metadata to structlog's contextvars for
the duration of each request, so every log line emitted anywhere during that
request (in any service/repository, without passing the id around manually)
is automatically tagged. This is what makes it possible to grep one
request's entire call chain out of the logs by request_id alone.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger

logger = get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_request_error")
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
        response.headers["X-Request-ID"] = request_id
        return response
