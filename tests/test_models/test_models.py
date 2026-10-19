from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from bookit.models import Appointment, AppointmentStatus, BusinessCategory, User, UserRole
from tests.factories import DEFAULT_PASSWORD, make_appointment, make_business, make_service, make_user

pytestmark = pytest.mark.django_db


def test_enum_values_match_the_assignment():
    assert UserRole.values == ["Client", "BusinessOwner"]
    assert AppointmentStatus.values == ["Pending", "Confirmed", "Cancelled"]
    assert BusinessCategory.values == ["Barber", "Beauty", "Fitness", "Massage", "Physiotherapy", "Tutoring"]


def test_unknown_business_category_is_rejected_by_the_database():
    with pytest.raises(IntegrityError):
        make_business(owner=make_user(role=UserRole.BUSINESS_OWNER), category="Cooking")


def test_create_user_hashes_password_and_lowercases_email():
    user = User.objects.create_user(email="Jane.Doe@Example.COM", password=DEFAULT_PASSWORD, full_name="Jane Doe")
    assert user.email == "jane.doe@example.com"
    assert user.password != DEFAULT_PASSWORD
    assert user.check_password(DEFAULT_PASSWORD)
    assert user.role == UserRole.CLIENT


def test_email_is_unique():
    make_user(email="dup@example.com")
    with pytest.raises(IntegrityError):
        make_user(email="dup@example.com")


def test_unknown_role_is_rejected_by_the_database():
    with pytest.raises(IntegrityError):
        make_user(role="Admin")


def test_appointment_defaults_to_pending_and_links_to_business_owner():
    owner = make_user(role=UserRole.BUSINESS_OWNER)
    service = make_service(business=make_business(owner=owner), duration_minutes=45)
    start = timezone.now() + timedelta(days=1)
    appointment = make_appointment(service=service, client=make_user(), start_time=start)
    assert appointment.status == AppointmentStatus.PENDING
    assert appointment.end_time - appointment.start_time == timedelta(minutes=45)
    assert appointment.service.business.owner == owner


@pytest.mark.parametrize("minutes", [0, -30])
def test_db_rejects_a_non_positive_service_duration(owner_user, minutes):
    with pytest.raises(IntegrityError):
        make_service(business=make_business(owner=owner_user), duration_minutes=minutes)


def test_db_rejects_a_negative_service_price(owner_user):
    with pytest.raises(IntegrityError):
        make_service(business=make_business(owner=owner_user), price="-1.00")


def test_appointment_end_must_be_after_start():
    service = make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)))
    start = timezone.now()
    with pytest.raises(IntegrityError):
        Appointment.objects.create(service=service, client=make_user(), start_time=start, end_time=start)


def test_unknown_appointment_status_is_rejected_by_the_database():
    service = make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)))
    with pytest.raises(IntegrityError):
        make_appointment(service=service, client=make_user(), start_time=timezone.now(), status="Done")
