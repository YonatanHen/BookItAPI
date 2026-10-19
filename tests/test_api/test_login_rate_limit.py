import time
from unittest import mock

import pytest

from tests.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db
LOGIN = "/api/v1/auth/login"
LIMIT = 5


def _login(api_client, email, password="wrong-pass", ip="10.0.0.1"):
    return api_client.post(LOGIN, {"email": email, "password": password}, REMOTE_ADDR=ip)


def test_sixth_login_attempt_within_a_minute_is_rate_limited(api_client, client_user):
    statuses = [_login(api_client, client_user.email).status_code for _ in range(LIMIT + 1)]
    assert statuses == [401] * LIMIT + [429]


def test_rate_limited_response_is_a_problem_with_retry_after(api_client, client_user):
    for _ in range(LIMIT):
        _login(api_client, client_user.email)
    response = _login(api_client, client_user.email)
    assert response["Content-Type"] == "application/problem+json"
    assert response["Retry-After"] == "60"
    assert response.json()["status"] == 429


def test_correct_password_is_also_blocked_after_the_limit(api_client, client_user):
    for _ in range(LIMIT):
        _login(api_client, client_user.email)
    assert _login(api_client, client_user.email, password=DEFAULT_PASSWORD).status_code == 429


def test_successful_logins_count_toward_the_limit(api_client, client_user):
    statuses = [_login(api_client, client_user.email, password=DEFAULT_PASSWORD).status_code for _ in range(LIMIT + 1)]
    assert statuses == [200] * LIMIT + [429]


def test_limit_is_counted_per_ip(api_client, client_user):
    for _ in range(LIMIT):
        _login(api_client, client_user.email, ip="10.0.0.1")
    assert _login(api_client, client_user.email, ip="10.0.0.2").status_code == 401


def test_limit_resets_in_the_next_minute(api_client, client_user):
    for _ in range(LIMIT + 1):
        _login(api_client, client_user.email)
    with mock.patch("django_ratelimit.core.time.time", return_value=time.time() + 61):
        assert _login(api_client, client_user.email).status_code == 401


def test_other_auth_endpoints_are_not_rate_limited(api_client):
    statuses = {api_client.post("/api/v1/auth/refresh", {"refresh": "bad"}).status_code for _ in range(LIMIT + 2)}
    assert statuses == {401}
