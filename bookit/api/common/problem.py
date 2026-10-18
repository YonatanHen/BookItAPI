"""RFC 9457 Problem Details helpers shared by the exception handler and the middlewares."""
from http import HTTPStatus
from typing import Any

from django.http import JsonResponse

from bookit.middleware.correlation import get_correlation_id

PROBLEM_CONTENT_TYPE = "application/problem+json"


def problem_body(status_code: int, detail: str, errors: Any = None) -> dict[str, Any]:
    """Build a Problem Details body tagged with the current correlation id."""
    body = {
        "type": "about:blank",
        "title": HTTPStatus(status_code).phrase,
        "status": status_code,
        "detail": detail,
        "correlation_id": get_correlation_id(),
    }
    if errors is not None:
        body["errors"] = errors
    return body


def problem_response(status_code: int, detail: str, errors: Any = None) -> JsonResponse:
    """Return a Problem Details response for code paths outside DRF views."""
    return JsonResponse(
        problem_body(status_code, detail, errors), status=status_code, content_type=PROBLEM_CONTENT_TYPE
    )
