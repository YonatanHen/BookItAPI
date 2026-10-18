import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection

from config.settings import env


@pytest.mark.django_db
def test_database_is_reachable_postgresql():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
    assert connection.vendor == "postgresql"


def test_secret_key_is_loaded_from_the_environment():
    assert len(settings.SECRET_KEY) >= 50


def test_missing_required_setting_fails_fast(monkeypatch):
    monkeypatch.delenv("BOOKIT_TEST_MISSING", raising=False)
    with pytest.raises(ImproperlyConfigured, match="BOOKIT_TEST_MISSING"):
        env("BOOKIT_TEST_MISSING")


def test_empty_required_setting_fails_fast(monkeypatch):
    monkeypatch.setenv("BOOKIT_TEST_EMPTY", "")
    with pytest.raises(ImproperlyConfigured, match="BOOKIT_TEST_EMPTY"):
        env("BOOKIT_TEST_EMPTY")


def test_optional_setting_uses_its_default(monkeypatch):
    monkeypatch.delenv("BOOKIT_TEST_OPTIONAL", raising=False)
    assert env("BOOKIT_TEST_OPTIONAL", "fallback") == "fallback"
