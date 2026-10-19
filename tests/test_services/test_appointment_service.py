import threading
from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection

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


@pytest.mark.parametrize(("start_minutes", "booked"), [(44, False), (45, True)])
def test_book_handles_an_odd_minute_duration(appointments, client_user, owner_user, start_minutes, booked):
    short = make_service(business=make_business(owner=owner_user), duration_minutes=38)
    make_appointment(service=short, client=make_user(), start_time=at(2) + timedelta(minutes=7))
    start = at(2) + timedelta(minutes=start_minutes)
    if booked:
        assert appointments.book(client=client_user, service_id=short.id, start_time=start).end_time == start + timedelta(
            minutes=38
        )
    else:
        with pytest.raises(ConflictError):
            appointments.book(client=client_user, service_id=short.id, start_time=start)


def test_book_detects_overlap_with_a_long_service(appointments, client_user, owner_user):
    long_service = make_service(business=make_business(owner=owner_user), duration_minutes=150)
    make_appointment(service=long_service, client=make_user(), start_time=at(2))
    with pytest.raises(ConflictError):
        appointments.book(client=client_user, service_id=long_service.id, start_time=at(4))


def test_book_ignores_cancelled_appointments(appointments, client_user, haircut):
    make_appointment(service=haircut, client=make_user(), start_time=at(2), status=AppointmentStatus.CANCELLED)
    assert appointments.book(client=client_user, service_id=haircut.id, start_time=at(2))


def test_book_allows_the_same_time_on_another_service(appointments, client_user, haircut):
    make_appointment(service=haircut, client=make_user(), start_time=at(2))
    other = make_service(business=haircut.business)
    assert appointments.book(client=client_user, service_id=other.id, start_time=at(2))


@pytest.mark.django_db(transaction=True)
def test_parallel_bookings_of_one_slot_let_only_one_win():
    threads_count = 8
    service = make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)), duration_minutes=60)
    clients = [make_user() for _ in range(threads_count)]
    barrier = threading.Barrier(threads_count)
    outcomes = []

    def book(client, offset_minutes):
        try:
            barrier.wait()
            AppointmentService(clock=lambda: NOW).book(
                client=client, service_id=service.id, start_time=at(2) + timedelta(minutes=offset_minutes)
            )
            outcomes.append("booked")
        except ConflictError:
            outcomes.append("conflict")
        finally:
            connection.close()

    # Each thread gets its own DB connection, so the requests really race in Postgres.
    threads = [threading.Thread(target=book, args=(client, i * 5)) for i, client in enumerate(clients)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["booked"] + ["conflict"] * (threads_count - 1)
    assert Appointment.objects.filter(service=service).count() == 1


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
