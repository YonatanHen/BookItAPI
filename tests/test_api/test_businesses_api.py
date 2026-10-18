import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from bookit.models import UserRole
from tests.factories import make_business, make_service, make_user

pytestmark = pytest.mark.django_db
URL = "/api/v1/businesses"


def test_requires_authentication(api_client):
    assert api_client.get(URL).status_code == 401


def test_returns_a_page_with_total_count_and_links(auth_client, client_user, owner_user):
    for i in range(25):
        make_business(owner=owner_user, name=f"Shop {i:02d}")
    response = auth_client(client_user).get(URL, {"limit": 10, "offset": 10})
    body = response.json()
    assert response.status_code == 200
    assert (body["count"], body["limit"], body["offset"]) == (25, 10, 10)
    assert [item["name"] for item in body["results"]] == [f"Shop {i:02d}" for i in range(10, 20)]
    assert "offset=20" in body["next"]
    assert "offset=0" in body["previous"]


def test_filters_reduce_the_total_count(auth_client, client_user, owner_user):
    make_business(owner=owner_user, name="Cut", category="Barber")
    make_business(owner=owner_user, name="Heal", category="Physiotherapy")
    body = auth_client(client_user).get(URL, {"category": "barber"}).json()
    assert body["count"] == 1
    assert body["results"][0]["name"] == "Cut"


def test_order_desc_sorts_by_name_descending(auth_client, client_user, owner_user):
    for name in ["A", "C", "B"]:
        make_business(owner=owner_user, name=name)
    body = auth_client(client_user).get(URL, {"order": "desc"}).json()
    assert [item["name"] for item in body["results"]] == ["C", "B", "A"]


def test_invalid_pagination_returns_400(auth_client, client_user):
    response = auth_client(client_user).get(URL, {"limit": 0})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "limit"


def test_offset_beyond_count_returns_empty_page(auth_client, client_user, owner_user):
    for i in range(3):
        make_business(owner=owner_user, name=f"Shop {i}")
    body = auth_client(client_user).get(URL, {"offset": 50}).json()
    assert (body["count"], body["results"], body["next"]) == (3, [], None)


def test_query_count_does_not_grow_with_rows(auth_client, client_user):
    client = auth_client(client_user)

    def count_queries():
        with CaptureQueriesContext(connection) as queries:
            assert client.get(URL).status_code == 200
        return len(queries)

    make_service(business=make_business(owner=make_user(role=UserRole.BUSINESS_OWNER)))
    baseline = count_queries()
    for _ in range(5):
        business = make_business(owner=make_user(role=UserRole.BUSINESS_OWNER))
        make_service(business=business)
        make_service(business=business)
    assert count_queries() == baseline
