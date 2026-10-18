"""Correlation id middleware and the logging filter that stamps it on every record."""
import logging
import re
import uuid
from contextvars import ContextVar

HEADER = "X-Correlation-ID"
_META_KEY = "HTTP_X_CORRELATION_ID"
_SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    """Return the correlation id of the current request, or '-' outside a request."""
    return _correlation_id.get()


class CorrelationIdMiddleware:
    """Gives every request a correlation id and echoes it in the response header."""

    def __init__(self, get_response):
        """Store the next handler in the chain."""
        self.get_response = get_response

    def __call__(self, request):
        """Bind the id for the duration of the request and add it to the response."""
        incoming = request.META.get(_META_KEY, "")
        correlation_id = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = _correlation_id.set(correlation_id)
        try:
            response = self.get_response(request)
        finally:
            _correlation_id.reset(token)
        response[HEADER] = correlation_id
        return response


class CorrelationIdFilter(logging.Filter):
    """Adds `correlation_id` to log records that do not already have one."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the current correlation id and keep the record."""
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        return True
