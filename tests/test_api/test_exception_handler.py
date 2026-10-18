from http import HTTPStatus
from unittest.mock import ANY

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from rest_framework.exceptions import NotAuthenticated, ValidationError

from bookit.api.common.exception_handler import VALIDATION_FAILED, problem_details_exception_handler as handle
from bookit.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    PermissionDeniedError,
)


class _Probe(BaseModel):
    age: int


@pytest.mark.parametrize(
    "error, status_code",
    [
        (NotFoundError("Business not found."), 404),
        (PermissionDeniedError("Not yours."), 403),
        (ConflictError("Slot taken."), 409),
        (BusinessRuleError("In the past."), 400),
        (InvalidCredentialsError("Bad password."), 401),
    ],
)
def test_domain_errors_map_to_http_status(error, status_code):
    response = handle(error, {})
    assert response.status_code == status_code
    assert response.data["detail"] == error.message
    assert response.data["title"] == HTTPStatus(status_code).phrase
    assert response.content_type == "application/problem+json"


def test_pydantic_errors_become_a_field_list():
    with pytest.raises(PydanticValidationError) as caught:
        _Probe.model_validate({"age": "x"})
    response = handle(caught.value, {})
    assert response.status_code == 400
    assert response.data["detail"] == VALIDATION_FAILED
    assert response.data["errors"] == [{"field": "age", "message": ANY}]


def test_drf_errors_keep_the_problem_shape():
    response = handle(NotAuthenticated(), {})
    assert response.status_code == 401
    assert response.data["detail"] == "Authentication credentials were not provided."


def test_drf_field_errors_are_listed():
    response = handle(ValidationError({"limit": ["bad"]}), {})
    assert response.status_code == 400
    assert response.data["errors"] == {"limit": ["bad"]}


def test_unknown_errors_are_left_for_the_500_middleware():
    assert handle(RuntimeError("boom"), {}) is None
