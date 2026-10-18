import pytest

pytestmark = pytest.mark.urls("tests.error_urls")


def test_unhandled_error_returns_generic_500_with_correlation_id(client):
    client.raise_request_exception = False
    response = client.get("/boom")
    assert response.status_code == 500
    assert response.json()["correlation_id"] == response["X-Correlation-ID"]
    assert "secret internal detail" not in response.content.decode()


def test_domain_error_returns_problem_details(client):
    response = client.get("/conflict")
    assert response.status_code == 409
    assert response["Content-Type"] == "application/problem+json"
    assert response.json()["detail"] == "Slot taken."
