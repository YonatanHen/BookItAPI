from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from bookit.api.v1.schemas.appointments import AppointmentCreateRequest, AppointmentListQuery, AppointmentOut
from bookit.models import Appointment, AppointmentStatus, Business, Service, User

TS = 1_893_456_000  # 2030-01-01T00:00:00Z
TS_DATETIME = datetime(2030, 1, 1, tzinfo=UTC)


def test_create_request_parses_unix_seconds_to_utc():
    payload = AppointmentCreateRequest.model_validate({"service_id": 3, "start_time": TS})
    assert payload.start_time == TS_DATETIME
    assert payload.start_time.tzinfo is UTC


@pytest.mark.parametrize(
    "body",
    [
        {"service_id": 3, "start_time": "tomorrow"},
        {"service_id": 3, "start_time": 1.5},
        {"service_id": 3, "start_time": True},
        {"service_id": 3, "start_time": 0},
        {"service_id": 3, "start_time": -60},
        {"service_id": 3, "start_time": "-60"},
        {"service_id": 0, "start_time": TS},
        {"service_id": 3, "start_time": TS, "status": "Confirmed"},
        {"start_time": TS},
    ],
)
def test_invalid_create_requests_are_rejected(body):
    with pytest.raises(ValidationError):
        AppointmentCreateRequest.model_validate(body)


def test_list_query_reads_from_to_aliases_and_status_in_any_case():
    query = AppointmentListQuery.model_validate({"from": str(TS), "to": str(TS + 3600), "status": " pending "})
    assert query.start_from == TS_DATETIME
    assert query.start_to == TS_DATETIME + timedelta(hours=1)
    assert query.status is AppointmentStatus.PENDING


@pytest.mark.parametrize(
    "params",
    [
        {"from": "abc"},
        {"from": "1.5"},
        {"from": "-5"},
        {"to": "0"},
        {"from": "99999999999999999"},
        {"to": ""},
        {"status": "Done"},
        {"from": str(TS + 10), "to": str(TS)},
    ],
)
def test_invalid_list_filters_are_rejected(params):
    with pytest.raises(ValidationError):
        AppointmentListQuery.model_validate(params)


def test_appointment_out_renders_unix_timestamps_and_display_names():
    business = Business(id=2, name="Cut Shop")
    service = Service(id=3, name="Haircut", price=Decimal("80.00"), duration_minutes=60, business=business)
    client = User(id=4, full_name="Clara")
    appointment = Appointment(
        id=1,
        service=service,
        client=client,
        start_time=TS_DATETIME,
        end_time=TS_DATETIME + timedelta(hours=1),
        status=AppointmentStatus.PENDING,
    )
    assert AppointmentOut.from_model(appointment).model_dump(mode="json") == {
        "id": 1,
        "status": "Pending",
        "start_time": TS,
        "end_time": TS + 3600,
        "service_id": 3,
        "service_name": "Haircut",
        "price": "80.00",
        "business_id": 2,
        "business_name": "Cut Shop",
        "client_id": 4,
        "client_name": "Clara",
    }
