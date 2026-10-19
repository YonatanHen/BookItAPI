from datetime import UTC, datetime

import pytest

from bookit.models import Appointment, Business, BusinessCategory, Service, User, UserRole
from bookit.services.auth_service import AuthService
from bookit.services.seed_service import SeedService

pytestmark = pytest.mark.django_db
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
PASSWORD = "Seed-Passw0rd!"


def _seed(**kwargs) -> SeedService:
    return SeedService(password=PASSWORD, clock=lambda: NOW, **kwargs)


def test_seed_creates_the_expected_volumes():
    result = _seed().run()
    assert (result.users, result.businesses, result.services, result.appointments) == (10, 20, 50, 200)
    assert User.objects.filter(role=UserRole.BUSINESS_OWNER).count() == 4
    assert User.objects.filter(role=UserRole.CLIENT).count() == 6
    assert set(Business.objects.values_list("category", flat=True)) == set(BusinessCategory.values)
    assert Service.objects.count() == 50


def test_seeded_users_log_in_with_the_configured_password():
    _seed().run()
    assert AuthService().login(email="owner1@bookit.dev", password=PASSWORD).access
    assert AuthService().login(email="client6@bookit.dev", password=PASSWORD).access


def test_seeded_appointments_never_overlap_on_a_service():
    _seed().run()
    for appointment in Appointment.objects.all():
        clash = Appointment.objects.filter(
            service_id=appointment.service_id,
            start_time__lt=appointment.end_time,
            end_time__gt=appointment.start_time,
        ).exclude(pk=appointment.pk)
        assert not clash.exists()


def test_second_run_is_skipped():
    _seed().run()
    assert _seed().run().skipped is True
    assert Appointment.objects.count() == 200


def test_reset_reseeds_the_same_data_for_the_same_seed():
    _seed(seed=7).run()
    names = sorted(Business.objects.values_list("name", flat=True))
    assert _seed(seed=7).run(reset=True).appointments == 200
    assert sorted(Business.objects.values_list("name", flat=True)) == names


def test_a_password_is_required():
    with pytest.raises(ValueError):
        SeedService(password="")
