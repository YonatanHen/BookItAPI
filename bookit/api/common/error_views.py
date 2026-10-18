"""JSON replacements for Django's HTML 404/500 pages (used when DEBUG is off)."""
from bookit.middleware.exception_handling import GENERIC_SERVER_ERROR

from .problem import problem_response


def not_found(request, exception=None):
    """Return a Problem Details 404."""
    return problem_response(404, "The requested resource was not found.")


def server_error(request):
    """Return a Problem Details 500 without internal details."""
    return problem_response(500, GENERIC_SERVER_ERROR)
