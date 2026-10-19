from io import StringIO

import pytest
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


def test_seed_command_seeds_once_with_the_password_from_settings(settings):
    settings.SEED_USER_PASSWORD = "Seed-Passw0rd!"
    out = StringIO()
    call_command("seed", stdout=out)
    assert "Seeded 10 users, 20 businesses, 50 services, 200 appointments." in out.getvalue()
    call_command("seed", stdout=out)
    assert "already seeded" in out.getvalue()


def test_seed_command_fails_without_a_password(settings):
    settings.SEED_USER_PASSWORD = ""
    with pytest.raises(CommandError, match="SEED_USER_PASSWORD"):
        call_command("seed")
