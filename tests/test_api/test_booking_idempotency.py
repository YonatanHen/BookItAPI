from datetime import timedelta

import pytest
from django.utils import timezone

from bookit.api.common.idempotency import DUPLICATE_DETAIL
from bookit.models import Appointment, IdempotencyRecord
from tests.factories import make_business, make_service, make_user

pytestmark = pytest.mark.django_db
URL = "/api/v1/appointments"


@pytest.fixture
def booking(owner_user):
    service = make_service(business=make_business(owner=owner_user))
    start = (timezone.now() + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    return {"service_id": service.id, "start_time": int(start.timestamp())}


def test_same_booking_twice_is_a_duplicate_and_the_key_is_linked(auth_client, client_user, booking):
    client = auth_client(client_user)
    first, second = client.post(URL, booking), client.post(URL, booking)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second["Content-Type"] == "application/problem+json"
    assert second.json()["detail"] == DUPLICATE_DETAIL
    assert Appointment.objects.count() == 1
    assert IdempotencyRecord.objects.get().appointment_id == first.json()["id"]


def test_other_user_with_the_same_body_gets_the_slot_conflict(auth_client, client_user, booking):
    assert auth_client(client_user).post(URL, booking).status_code == 201
    response = auth_client(make_user()).post(URL, booking)
    assert response.status_code == 409
    assert response.json()["detail"] != DUPLICATE_DETAIL


def test_failed_booking_releases_the_key(auth_client, client_user, booking):
    client = auth_client(client_user)
    bad = {**booking, "service_id": 999_999}
    assert [client.post(URL, bad).status_code for _ in range(2)] == [400, 400]
    assert not IdempotencyRecord.objects.exists()


@pytest.mark.parametrize("raw", ["not json", "[]", '"text"'])
def test_malformed_body_returns_400_and_leaves_no_key(auth_client, client_user, raw):
    response = auth_client(client_user).post(URL, data=raw, content_type="application/json")
    assert response.status_code == 400
    assert not IdempotencyRecord.objects.exists()


def test_unauthenticated_post_stores_nothing(api_client, booking):
    assert api_client.post(URL, booking).status_code == 401
    assert not IdempotencyRecord.objects.exists()


def test_list_requests_are_not_guarded(auth_client, client_user):
    client = auth_client(client_user)
    assert [client.get(URL).status_code for _ in range(2)] == [200, 200]
    assert not IdempotencyRecord.objects.exists()
