"""Last-resort handler that turns unhandled exceptions into a generic 500 response."""
import logging

from django.core.exceptions import BadRequest, PermissionDenied, SuspiciousOperation
from django.http import Http404

from bookit.api.common.problem import problem_response

logger = logging.getLogger("bookit.errors")
GENERIC_SERVER_ERROR = "An unexpected error occurred."
_HANDLED_BY_DJANGO = (Http404, PermissionDenied, BadRequest, SuspiciousOperation)


class ExceptionHandlingMiddleware:
    """Logs unhandled view exceptions server-side and hides their details from the client."""

    def __init__(self, get_response):
        """Store the next handler in the chain."""
        self.get_response = get_response

    def __call__(self, request):
        """Pass the request through; errors are caught in process_exception."""
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Return a generic 500 Problem Details response; let Django handle its own HTTP errors."""
        if isinstance(exception, _HANDLED_BY_DJANGO):
            return None
        logger.error("Unhandled exception on %s %s", request.method, request.path, exc_info=exception)
        return problem_response(500, GENERIC_SERVER_ERROR)
