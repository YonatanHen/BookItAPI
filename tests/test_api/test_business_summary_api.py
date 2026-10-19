from datetime import timedelta

import pytest
from django.utils import timezone

from bookit.models import UserRole
from tests.factories import make_appointment, make_business, make_service, make_user

pytestmark = pytest.mark.django_db


def url(business_id: int) -> str:
    return f"/api/v1/businesses/{business_id}/summary"


@pytest.fixture
def shop(owner_user, client_user):
    business = make_business(owner=owner_user, name="Cut Shop")
    haircut = make_service(business=business, name="Haircut", price="50.00", duration_minutes=30)
    make_appointment(service=haircut, client=client_user, start_time=timezone.now() + timedelta(days=1))
    return business


def test_owner_gets_200_and_the_summary(auth_client, owner_user, shop):
    response = auth_client(owner_user).get(url(shop.id))
    assert response.status_code == 200
    body = response.json()
    assert (body["business_id"], body["business_name"]) == (shop.id, "Cut Shop")
    service = body["services"][0]
    assert (service["service_name"], service["upcoming_appointments"]) == ("Haircut", 1)
    assert service["expected_revenue"] == "50.00"


def test_other_owner_gets_403(auth_client, shop):
    assert auth_client(make_user(role=UserRole.BUSINESS_OWNER)).get(url(shop.id)).status_code == 403


def test_missing_business_gets_404(auth_client, owner_user):
    assert auth_client(owner_user).get(url(999_999)).status_code == 404


def test_requires_authentication(api_client, shop):
    assert api_client.get(url(shop.id)).status_code == 401
