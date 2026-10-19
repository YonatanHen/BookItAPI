import pytest
from django.core.checks import run_checks
from django.urls import resolve, reverse

ROUTES = [
    ("v1:root", {}, "/api/v1/"),
    ("v1:health", {}, "/api/v1/health"),
    ("v1:auth-register", {}, "/api/v1/auth/register"),
    ("v1:auth-login", {}, "/api/v1/auth/login"),
    ("v1:auth-refresh", {}, "/api/v1/auth/refresh"),
    ("v1:business-list", {}, "/api/v1/businesses"),
    ("v1:business-summary", {"business_id": 7}, "/api/v1/businesses/7/summary"),
    ("v1:appointment-list", {}, "/api/v1/appointments"),
]


@pytest.mark.parametrize(("name", "kwargs", "expected"), ROUTES)
def test_route_names_resolve_to_unchanged_paths(name, kwargs, expected):
    assert reverse(name, kwargs=kwargs) == expected
    assert resolve(expected).view_name == name


def test_url_checks_report_no_warnings():
    assert run_checks(tags=["urls"]) == []
