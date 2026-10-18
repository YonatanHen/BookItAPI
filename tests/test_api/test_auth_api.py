from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from bookit.services.auth_service import AuthService
from tests.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db
REGISTER, LOGIN, REFRESH, ROOT = "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/"


def test_register_returns_201_and_the_user(api_client):
    response = api_client.post(
        REGISTER,
        {"email": "New@Bookit-Test.io", "password": DEFAULT_PASSWORD, "full_name": "New", "role": "BusinessOwner"},
    )
    assert response.status_code == 201
    assert response.json() | {"id": 0} == {
        "id": 0, "email": "new@bookit-test.io", "full_name": "New", "role": "BusinessOwner"
    }


def test_register_invalid_body_returns_400_problem(api_client):
    response = api_client.post(REGISTER, {"email": "bad"})
    assert response.status_code == 400
    assert response["Content-Type"] == "application/problem+json"
    assert {"email", "password", "full_name", "role"} <= {e["field"] for e in response.json()["errors"]}


def test_register_duplicate_email_returns_409(api_client, client_user):
    body = {"email": client_user.email.upper(), "password": DEFAULT_PASSWORD, "full_name": "X", "role": "Client"}
    assert api_client.post(REGISTER, body).status_code == 409


def test_login_returns_200_and_a_token_pair(api_client, client_user):
    response = api_client.post(LOGIN, {"email": client_user.email, "password": DEFAULT_PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "Bearer"
    assert AccessToken(response.json()["access"])["role"] == "Client"


def test_login_with_wrong_password_returns_401(api_client, client_user):
    assert api_client.post(LOGIN, {"email": client_user.email, "password": "wrong-pass"}).status_code == 401


def test_login_ignores_a_bad_bearer_header(api_client, client_user):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer garbage")
    assert api_client.post(LOGIN, {"email": client_user.email, "password": DEFAULT_PASSWORD}).status_code == 200


def test_refresh_returns_200_and_a_new_access_token(api_client, client_user):
    response = api_client.post(REFRESH, {"refresh": AuthService().issue_tokens(client_user).refresh})
    assert response.status_code == 200
    assert AccessToken(response.json()["access"])["role"] == "Client"


def test_refresh_with_invalid_token_returns_401(api_client):
    assert api_client.post(REFRESH, {"refresh": "not-a-token"}).status_code == 401


def test_protected_endpoint_rejects_missing_and_expired_tokens(api_client, client_user):
    assert api_client.get(ROOT).status_code == 401
    expired = AccessToken.for_user(client_user)
    expired.set_exp(lifetime=-timedelta(seconds=1))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
    response = api_client.get(ROOT)
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


def test_protected_endpoint_accepts_a_valid_token(auth_client, client_user):
    assert auth_client(client_user).get(ROOT).status_code == 200
