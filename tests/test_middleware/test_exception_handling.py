import json
import logging

import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse

from bookit.api.common.error_views import not_found, server_error
from bookit.middleware.exception_handling import GENERIC_SERVER_ERROR, ExceptionHandlingMiddleware


def _middleware():
    return ExceptionHandlingMiddleware(lambda request: HttpResponse())


def test_unexpected_error_becomes_a_generic_problem_500(rf, caplog):
    with caplog.at_level(logging.ERROR, logger="bookit.errors"):
        response = _middleware().process_exception(rf.get("/x"), RuntimeError("secret internal detail"))
    body = json.loads(response.content)
    assert response.status_code == 500
    assert response["Content-Type"] == "application/problem+json"
    assert body["detail"] == GENERIC_SERVER_ERROR
    assert "secret internal detail" not in response.content.decode()
    record = next(r for r in caplog.records if r.name == "bookit.errors")
    assert "secret internal detail" in str(record.exc_info[1])


@pytest.mark.parametrize("error", [Http404(), PermissionDenied()])
def test_django_http_errors_are_left_to_django(rf, error):
    assert _middleware().process_exception(rf.get("/x"), error) is None


def test_json_error_views(rf):
    assert not_found(rf.get("/x")).status_code == 404
    response = server_error(rf.get("/x"))
    assert response.status_code == 500
    assert json.loads(response.content)["detail"] == GENERIC_SERVER_ERROR
