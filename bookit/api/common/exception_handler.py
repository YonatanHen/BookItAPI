"""DRF exception handler: maps domain, Pydantic and DRF errors to Problem Details."""
from typing import Any

from django.conf import settings
from django_ratelimit.exceptions import Ratelimited
from pydantic import ValidationError as PydanticValidationError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from bookit.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    DomainError,
    InvalidCredentialsError,
    NotFoundError,
    PermissionDeniedError,
)

from .problem import PROBLEM_CONTENT_TYPE, problem_body
from .rate_limit import RATE_LIMITED_DETAIL, rate_period_seconds

VALIDATION_FAILED = "Request validation failed."


class ConflictException(exceptions.APIException):
    """HTTP 409 for domain conflicts."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state."
    default_code = "conflict"


class BusinessRuleException(exceptions.APIException):
    """HTTP 400 for broken business rules."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request breaks a business rule."
    default_code = "business_rule"


_DOMAIN_TO_API = {
    NotFoundError: exceptions.NotFound,
    PermissionDeniedError: exceptions.PermissionDenied,
    ConflictError: ConflictException,
    BusinessRuleError: BusinessRuleException,
    InvalidCredentialsError: exceptions.AuthenticationFailed,
}


def problem_details_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Return a Problem Details response, or None so unknown errors reach the 500 middleware."""
    if isinstance(exc, PydanticValidationError):
        body = problem_body(status.HTTP_400_BAD_REQUEST, VALIDATION_FAILED, _pydantic_errors(exc))
        return Response(body, status=status.HTTP_400_BAD_REQUEST, content_type=PROBLEM_CONTENT_TYPE)
    if isinstance(exc, DomainError):
        exc = _to_api_exception(exc)
    if isinstance(exc, Ratelimited):  # subclass of PermissionDenied: map before DRF turns it into 403
        exc = exceptions.Throttled(wait=rate_period_seconds(settings.LOGIN_RATE_LIMIT), detail=RATE_LIMITED_DETAIL)
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail, errors = _split_drf_data(response.data)
    response.data = problem_body(response.status_code, detail, errors)
    response.content_type = PROBLEM_CONTENT_TYPE
    return response


def _to_api_exception(exc: DomainError) -> exceptions.APIException:
    """Translate a domain error into the matching DRF exception."""
    for domain_type, api_type in _DOMAIN_TO_API.items():
        if isinstance(exc, domain_type):
            return api_type(detail=exc.message)
    return exceptions.APIException(detail=exc.message)


def _pydantic_errors(exc: PydanticValidationError) -> list[dict[str, str]]:
    """Flatten Pydantic errors into [{field, message}] using the request field names."""
    return [
        {"field": ".".join(str(part) for part in error["loc"]) or "request", "message": error["msg"]}
        for error in exc.errors(include_url=False)
    ]


def _split_drf_data(data: Any) -> tuple[str, Any]:
    """Return the detail text and optional field errors from DRF error data."""
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"]), None
    return VALIDATION_FAILED, data
