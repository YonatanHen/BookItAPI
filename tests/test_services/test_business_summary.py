from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from bookit.models import AppointmentStatus, UserRole
from bookit.services.business_service import BusinessService
from bookit.services.exceptions import NotFoundError, PermissionDeniedError
from tests.factories import make_appointment, make_business, make_service, make_user

pytestmark = pytest.mark.django_db
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def summaries():
    return BusinessService(clock=lambda: NOW)


@pytest.fixture
def shop(owner_user):
    return make_business(owner=owner_user, name="Cut Shop")


def _rows(summary):
    return {service.name: (service.upcoming_appointments, service.expected_revenue) for service in summary.services}


def test_counts_upcoming_active_appointments_and_revenue(summaries, owner_user, client_user, shop):
    haircut = make_service(business=shop, name="Haircut", price="50.00", duration_minutes=30)
    make_service(business=shop, name="Shave", price="20.00")
    for hours, status in [
        (1, AppointmentStatus.PENDING),
        (2, AppointmentStatus.CONFIRMED),
        (3, AppointmentStatus.CANCELLED),
        (-24, AppointmentStatus.CONFIRMED),
    ]:
        make_appointment(service=haircut, client=client_user, start_time=NOW + timedelta(hours=hours), status=status)
    rows = _rows(summaries.get_summary(user=owner_user, business_id=shop.id))
    assert rows == {"Haircut": (2, Decimal("100.00")), "Shave": (0, Decimal("0.00"))}


def test_appointment_starting_exactly_now_is_not_upcoming(summaries, owner_user, client_user, shop):
    service = make_service(business=shop, name="Haircut")
    make_appointment(service=service, client=client_user, start_time=NOW)
    assert _rows(summaries.get_summary(user=owner_user, business_id=shop.id))["Haircut"][0] == 0


def test_other_businesses_are_not_counted(summaries, owner_user, client_user, shop):
    make_service(business=shop, name="Haircut")
    foreign = make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)), name="Haircut")
    make_appointment(service=foreign, client=client_user, start_time=NOW + timedelta(hours=1))
    assert _rows(summaries.get_summary(user=owner_user, business_id=shop.id)) == {"Haircut": (0, Decimal("0.00"))}


def test_summary_runs_in_two_queries(summaries, owner_user, client_user, shop, django_assert_num_queries):
    for _ in range(3):
        service = make_service(business=shop)
        make_appointment(service=service, client=client_user, start_time=NOW + timedelta(hours=1))
    with django_assert_num_queries(2):
        summaries.get_summary(user=owner_user, business_id=shop.id)


def test_another_owner_is_forbidden(summaries, shop):
    with pytest.raises(PermissionDeniedError):
        summaries.get_summary(user=make_user(role=UserRole.BUSINESS_OWNER), business_id=shop.id)


def test_a_client_is_forbidden(summaries, client_user, shop):
    with pytest.raises(PermissionDeniedError):
        summaries.get_summary(user=client_user, business_id=shop.id)


def test_missing_business_is_not_found(summaries, client_user):
    with pytest.raises(NotFoundError):
        summaries.get_summary(user=client_user, business_id=999_999)
