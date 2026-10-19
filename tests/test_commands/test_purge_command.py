from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from bookit.models import IdempotencyRecord

pytestmark = pytest.mark.django_db


def test_purge_command_deletes_expired_keys_and_reports_the_count(client_user):
    IdempotencyRecord.objects.create(key="old", user=client_user, expires_at=timezone.now() - timedelta(seconds=1))
    IdempotencyRecord.objects.create(key="new", user=client_user, expires_at=timezone.now() + timedelta(hours=1))
    out = StringIO()
    call_command("purge_idempotency_keys", stdout=out)
    assert "Deleted 1 expired idempotency key(s)." in out.getvalue()
    assert list(IdempotencyRecord.objects.values_list("key", flat=True)) == ["new"]
