import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.errors import error_response


logger = logging.getLogger(__name__)

SENSITIVE_ROUTES = (
    ("POST", "/suppliers/upload"),
    ("POST", "/catalogs/upload"),
    ("POST", "/emails/send"),
    ("POST", "/emails/campaigns"),
    ("POST", "/products/enrich-apify"),
    ("POST", "/products/analyze"),
    ("POST", "/webhooks/events"),
    ("PUT", "/settings/scoring"),
    ("PUT", "/settings/fees"),
    ("GET", "/exports/"),
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._is_sensitive(request):
            return await call_next(request)

        now = time.time()
        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.method}:{request.url.path}"
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_requests = settings.RATE_LIMIT_REQUESTS
        timestamps = self.requests[key]

        while timestamps and now - timestamps[0] > window:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            return error_response(429, "Rate limit exceeded", "Too many requests. Please try again later.")

        timestamps.append(now)
        return await call_next(request)

    @staticmethod
    def _is_sensitive(request: Request) -> bool:
        path = request.url.path
        for method, route in SENSITIVE_ROUTES:
            if request.method != method:
                continue
            if route.endswith("/") and path.startswith(route):
                return True
            if path == route or path.startswith(f"{route}/"):
                return True
        return False
