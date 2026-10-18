import pytest

from bookit.models import UserRole
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
