from datetime import UTC, datetime, timedelta

import pytest

from bookit.models import IdempotencyRecord
from bookit.services.idempotency_service import IdempotencyService
from tests.factories import make_appointment, make_business, make_service

pytestmark = pytest.mark.django_db
START = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock():
    return FakeClock(START)


@pytest.fixture
def idempotency(clock):
    return IdempotencyService(clock=clock, ttl_seconds=600, purge_interval_seconds=300)


def _expired(user, key: str) -> IdempotencyRecord:
    return IdempotencyRecord.objects.create(key=key, user=user, expires_at=START - timedelta(seconds=1))


def test_first_claim_stores_the_key_with_its_ttl(idempotency, client_user):
    record = idempotency.claim(key="k1", user=client_user)
    assert record.expires_at == START + timedelta(seconds=600)
    assert record.appointment_id is None


def test_second_claim_within_the_ttl_is_rejected(idempotency, client_user):
    idempotency.claim(key="k1", user=client_user)
    assert idempotency.claim(key="k1", user=client_user) is None


def test_claim_after_the_ttl_is_accepted_again(idempotency, clock, client_user):
    idempotency.claim(key="k1", user=client_user)
    clock.now += timedelta(seconds=601)
    assert idempotency.claim(key="k1", user=client_user) is not None
    assert IdempotencyRecord.objects.count() == 1


def test_release_allows_an_immediate_retry(idempotency, client_user):
    idempotency.release(idempotency.claim(key="k1", user=client_user))
    assert idempotency.claim(key="k1", user=client_user) is not None


def test_complete_links_the_created_appointment(idempotency, client_user, owner_user):
    service = make_service(business=make_business(owner=owner_user))
    appointment = make_appointment(service=service, client=client_user, start_time=START + timedelta(hours=2))
    record = idempotency.claim(key="k1", user=client_user)
    idempotency.complete(record, appointment_id=appointment.id)
    assert IdempotencyRecord.objects.get(pk=record.pk).appointment == appointment


def test_complete_without_an_id_leaves_the_link_empty(idempotency, client_user):
    record = idempotency.claim(key="k1", user=client_user)
    idempotency.complete(record, appointment_id=None)
    assert IdempotencyRecord.objects.get(pk=record.pk).appointment_id is None


def test_purge_expired_deletes_only_expired_keys(idempotency, client_user):
    idempotency.claim(key="fresh", user=client_user)
    _expired(client_user, "old")
    assert idempotency.purge_expired() == 1
    assert list(IdempotencyRecord.objects.values_list("key", flat=True)) == ["fresh"]


def test_claim_purges_expired_keys_at_most_once_per_interval(idempotency, clock, client_user):
    _expired(client_user, "old-1")
    idempotency.claim(key="a", user=client_user)
    assert not IdempotencyRecord.objects.filter(key="old-1").exists()
    _expired(client_user, "old-2")
    clock.now += timedelta(seconds=60)
    idempotency.claim(key="b", user=client_user)
    assert IdempotencyRecord.objects.filter(key="old-2").exists()
    clock.now += timedelta(seconds=300)
    idempotency.claim(key="c", user=client_user)
    assert not IdempotencyRecord.objects.filter(key="old-2").exists()
