from datetime import timedelta

import pytest
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from bookit.models import UserRole
from bookit.services.auth_service import AuthService
from bookit.services.exceptions import ConflictError, InvalidCredentialsError
from tests.factories import DEFAULT_PASSWORD, make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth():
    return AuthService()


def test_register_creates_user_with_normalized_fields(auth):
    user = auth.register(
        email="  Jane@Example-Mail.io ", password=DEFAULT_PASSWORD, full_name=" Jane Doe ", role=UserRole.CLIENT
    )
    assert user.email == "jane@example-mail.io"
    assert user.full_name == "Jane Doe"
    assert user.role == UserRole.CLIENT
    assert user.check_password(DEFAULT_PASSWORD)


def test_register_rejects_duplicate_email_in_any_case(auth):
    make_user(email="jane@bookit-test.io")
    with pytest.raises(ConflictError):
        auth.register(email="JANE@bookit-test.io", password=DEFAULT_PASSWORD, full_name="J", role=UserRole.CLIENT)


def test_login_returns_tokens_with_user_id_and_role_claims(auth, owner_user):
    tokens = auth.login(email=owner_user.email, password=DEFAULT_PASSWORD)
    access = AccessToken(tokens.access)
    assert str(access["user_id"]) == str(owner_user.id)
    assert access["role"] == UserRole.BUSINESS_OWNER
    assert RefreshToken(tokens.refresh)["role"] == UserRole.BUSINESS_OWNER


def test_login_is_case_insensitive_on_email(auth, client_user):
    assert auth.login(email=client_user.email.upper(), password=DEFAULT_PASSWORD).access


def test_login_rejects_wrong_password(auth, client_user):
    with pytest.raises(InvalidCredentialsError):
        auth.login(email=client_user.email, password="wrong-password")


def test_login_rejects_unknown_email(auth):
    with pytest.raises(InvalidCredentialsError):
        auth.login(email="nobody@bookit-test.io", password=DEFAULT_PASSWORD)


def test_refresh_returns_a_new_access_token_with_role(auth, client_user):
    access = AccessToken(auth.refresh(auth.issue_tokens(client_user).refresh))
    assert access["role"] == UserRole.CLIENT
    assert str(access["user_id"]) == str(client_user.id)


def test_refresh_rejects_an_expired_refresh_token(auth, client_user):
    token = RefreshToken.for_user(client_user)
    token.set_exp(lifetime=-timedelta(seconds=1))
    with pytest.raises(InvalidCredentialsError):
        auth.refresh(str(token))


def test_refresh_rejects_an_access_token(auth, client_user):
    with pytest.raises(InvalidCredentialsError):
        auth.refresh(auth.issue_tokens(client_user).access)


def test_refresh_rejects_garbage(auth):
    with pytest.raises(InvalidCredentialsError):
        auth.refresh("not-a-token")
