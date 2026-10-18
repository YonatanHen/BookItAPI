"""Logs one line per request: method, path, status code and duration."""
import logging
import time

from .correlation import get_correlation_id

logger = logging.getLogger("bookit.requests")


class RequestLoggingMiddleware:
    """Measures each request and logs its outcome."""

    def __init__(self, get_response):
        """Store the next handler in the chain."""
        self.get_response = get_response

    def __call__(self, request):
        """Time the inner chain and log the result with structured extra fields."""
        started = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "%s %s -> %s (%.2f ms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "correlation_id": get_correlation_id(),
            },
        )
        return response
