from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from bookit.models import AppointmentStatus
from tests.factories import make_appointment, make_business, make_service, make_user

pytestmark = pytest.mark.django_db
URL = "/api/v1/appointments"


def future(days: int = 2):
    return (timezone.now() + timedelta(days=days)).replace(minute=0, second=0, microsecond=0)


@pytest.fixture
def haircut(owner_user):
    business = make_business(owner=owner_user, name="Cut Shop")
    return make_service(business=business, name="Haircut", duration_minutes=60, price="80.00")


def test_book_returns_201_and_the_appointment(auth_client, client_user, haircut):
    start = int(future().timestamp())
    response = auth_client(client_user).post(URL, {"service_id": haircut.id, "start_time": start})
    assert response.status_code == 201
    assert response.json() | {"id": 0} == {
        "id": 0,
        "status": "Pending",
        "start_time": start,
        "end_time": start + 3600,
        "service_id": haircut.id,
        "service_name": "Haircut",
        "price": "80.00",
        "business_id": haircut.business_id,
        "business_name": "Cut Shop",
        "client_id": client_user.id,
        "client_name": "Clara Client",
    }


def test_book_requires_authentication(api_client, haircut):
    assert api_client.post(URL, {"service_id": haircut.id, "start_time": int(future().timestamp())}).status_code == 401


def test_book_as_business_owner_returns_403(auth_client, owner_user, haircut):
    response = auth_client(owner_user).post(URL, {"service_id": haircut.id, "start_time": int(future().timestamp())})
    assert response.status_code == 403


def test_book_in_the_past_returns_400(auth_client, client_user, haircut):
    past = int((timezone.now() - timedelta(hours=1)).timestamp())
    assert auth_client(client_user).post(URL, {"service_id": haircut.id, "start_time": past}).status_code == 400


def test_book_taken_slot_returns_409(auth_client, client_user, haircut):
    make_appointment(service=haircut, client=make_user(), start_time=future())
    response = auth_client(client_user).post(URL, {"service_id": haircut.id, "start_time": int(future().timestamp())})
    assert response.status_code == 409


def test_list_returns_own_appointments_matching_filters(auth_client, client_user, haircut):
    wanted = make_appointment(service=haircut, client=client_user, start_time=future(2))
    make_appointment(service=haircut, client=client_user, start_time=future(2) + timedelta(hours=2),
                     status=AppointmentStatus.CANCELLED)
    params = {"from": int(future(1).timestamp()), "to": int(future(3).timestamp()), "status": "pending"}
    body = auth_client(client_user).get(URL, params).json()
    assert body["count"] == 1
    assert body["results"][0]["id"] == wanted.id


def test_list_with_invalid_filter_returns_400(auth_client, client_user):
    response = auth_client(client_user).get(URL, {"from": "abc"})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "from"


def test_list_query_count_does_not_grow_with_rows(auth_client, client_user, haircut):
    client = auth_client(client_user)

    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert client.get(URL).status_code == 200
        return len(queries)

    make_appointment(service=haircut, client=client_user, start_time=future(1))
    baseline = count_queries()
    for days in range(2, 7):
        other = make_service(business=make_business(owner=make_user(role="BusinessOwner")))
        make_appointment(service=other, client=client_user, start_time=future(days))
    assert count_queries() == baseline
