import pytest

pytestmark = pytest.mark.django_db


def test_v1_root_reports_the_resolved_version(api_client, client_user):
    api_client.force_authenticate(client_user)
    response = api_client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"version": "v1"}


def test_v1_root_requires_a_jwt(api_client):
    response = api_client.get("/api/v1/")
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


def test_unknown_version_returns_404(api_client, client_user):
    api_client.force_authenticate(client_user)
    assert api_client.get("/api/v2/").status_code == 404
