from unittest import mock

import pytest
from django.db import OperationalError

pytestmark = pytest.mark.django_db
URL = "/api/v1/health"


def test_health_returns_ok_without_a_token(api_client):
    response = api_client.get(URL)
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


def test_health_returns_503_when_the_database_is_down(api_client):
    with mock.patch("bookit.api.v1.views.health.connection.cursor", side_effect=OperationalError("down")):
        response = api_client.get(URL)
    assert response.status_code == 503
    assert response.json() == {"status": "UNAVAILABLE"}
