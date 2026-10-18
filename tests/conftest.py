import pytest
from rest_framework.test import APIClient

from bookit.models import UserRole
from bookit.services.auth_service import AuthService
from tests.factories import make_user


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def client_user(db):
    return make_user(role=UserRole.CLIENT, full_name="Clara Client")


@pytest.fixture
def owner_user(db):
    return make_user(role=UserRole.BUSINESS_OWNER, full_name="Oscar Owner")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client():
    def _make(user):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AuthService().issue_tokens(user).access}")
        return client

    return _make
