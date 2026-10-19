from datetime import UTC, datetime, timedelta

import pytest

from bookit.models import Appointment, AppointmentStatus, UserRole
from bookit.services.appointment_service import AppointmentService
from bookit.services.exceptions import BusinessRuleError, ConflictError, PermissionDeniedError
from tests.factories import make_appointment, make_business, make_service, make_user

pytestmark = pytest.mark.django_db
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


def at(hours: float) -> datetime:
    return NOW + timedelta(hours=hours)


@pytest.fixture
def appointments():
    return AppointmentService(clock=lambda: NOW)


@pytest.fixture
def haircut(owner_user):
    return make_service(business=make_business(owner=owner_user), duration_minutes=60, price="80.00")


def test_book_creates_a_pending_appointment_with_end_time(appointments, client_user, haircut):
    appointment = appointments.book(client=client_user, service_id=haircut.id, start_time=at(2))
    assert appointment.status == AppointmentStatus.PENDING
    assert (appointment.start_time, appointment.end_time) == (at(2), at(3))
    assert appointment.client == client_user
    assert Appointment.objects.count() == 1


@pytest.mark.parametrize("hours", [0, -1])
def test_book_rejects_a_start_time_that_is_not_in_the_future(appointments, client_user, haircut, hours):
    with pytest.raises(BusinessRuleError):
        appointments.book(client=client_user, service_id=haircut.id, start_time=at(hours))


def test_book_rejects_an_unknown_service(appointments, client_user):
    with pytest.raises(BusinessRuleError):
        appointments.book(client=client_user, service_id=999_999, start_time=at(2))


def test_book_rejects_a_business_owner(appointments, owner_user, haircut):
    with pytest.raises(PermissionDeniedError):
        appointments.book(client=owner_user, service_id=haircut.id, start_time=at(2))


@pytest.mark.parametrize("start_hours", [2, 2.5, 1.5])
def test_book_rejects_an_overlapping_slot(appointments, client_user, haircut, start_hours):
    make_appointment(service=haircut, client=make_user(), start_time=at(2))
    with pytest.raises(ConflictError):
        appointments.book(client=client_user, service_id=haircut.id, start_time=at(start_hours))


@pytest.mark.parametrize("start_hours", [3, 1])
def test_book_allows_back_to_back_slots(appointments, client_user, haircut, start_hours):
    make_appointment(service=haircut, client=make_user(), start_time=at(2))
    assert appointments.book(client=client_user, service_id=haircut.id, start_time=at(start_hours))


def test_book_ignores_cancelled_appointments(appointments, client_user, haircut):
    make_appointment(service=haircut, client=make_user(), start_time=at(2), status=AppointmentStatus.CANCELLED)
    assert appointments.book(client=client_user, service_id=haircut.id, start_time=at(2))


def test_book_allows_the_same_time_on_another_service(appointments, client_user, haircut):
    make_appointment(service=haircut, client=make_user(), start_time=at(2))
    other = make_service(business=haircut.business)
    assert appointments.book(client=client_user, service_id=other.id, start_time=at(2))


def test_client_sees_only_own_appointments(appointments, client_user, haircut):
    mine = make_appointment(service=haircut, client=client_user, start_time=at(2))
    make_appointment(service=haircut, client=make_user(), start_time=at(5))
    assert list(appointments.list_for_user(user=client_user)) == [mine]


def test_owner_sees_appointments_of_owned_businesses_only(appointments, owner_user, client_user, haircut):
    first = make_appointment(service=haircut, client=client_user, start_time=at(2))
    second = make_appointment(service=haircut, client=make_user(), start_time=at(4))
    foreign = make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)))
    make_appointment(service=foreign, client=client_user, start_time=at(2))
    assert list(appointments.list_for_user(user=owner_user)) == [first, second]


def test_list_range_is_inclusive(appointments, client_user, haircut):
    first = make_appointment(service=haircut, client=client_user, start_time=at(2))
    second = make_appointment(service=haircut, client=client_user, start_time=at(4))
    make_appointment(service=haircut, client=client_user, start_time=at(6))
    result = appointments.list_for_user(user=client_user, start_from=at(2), start_to=at(4))
    assert list(result) == [first, second]


def test_list_filters_by_status(appointments, client_user, haircut):
    make_appointment(service=haircut, client=client_user, start_time=at(2))
    cancelled = make_appointment(
        service=haircut, client=client_user, start_time=at(4), status=AppointmentStatus.CANCELLED
    )
    assert list(appointments.list_for_user(user=client_user, status=AppointmentStatus.CANCELLED)) == [cancelled]


def test_list_preloads_service_business_and_client(appointments, client_user, haircut, django_assert_num_queries):
    for hours in (2, 4, 6):
        make_appointment(service=haircut, client=client_user, start_time=at(hours))
    with django_assert_num_queries(1):
        rows = list(appointments.list_for_user(user=client_user))
        assert all(row.service.business.name and row.client.full_name for row in rows)
