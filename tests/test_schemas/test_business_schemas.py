import pytest
from pydantic import ValidationError

from bookit.api.common.pagination import PageParams
from bookit.api.common.schema_types import SortOrder
from bookit.api.v1.schemas.businesses import BusinessListQuery, BusinessOut
from bookit.models import BusinessCategory
from tests.factories import make_business, make_service


def test_page_params_have_defaults():
    params = PageParams.model_validate({})
    assert (params.limit, params.offset) == (20, 0)


def test_page_params_parse_query_strings():
    params = PageParams.model_validate({"limit": "10", "offset": "30"})
    assert (params.limit, params.offset) == (10, 30)


@pytest.mark.parametrize(
    "params", [{"limit": "0"}, {"limit": "101"}, {"limit": "abc"}, {"offset": "-1"}, {"offset": "2147483648"}]
)
def test_invalid_page_params_are_rejected(params):
    with pytest.raises(ValidationError):
        PageParams.model_validate(params)


def test_business_query_matches_category_in_any_case_and_inherits_paging():
    query = BusinessListQuery.model_validate({"category": " barber ", "search": " cut ", "limit": "5", "x": "1"})
    assert (query.category, query.search, query.limit) == (BusinessCategory.BARBER, "cut", 5)


def test_unknown_category_is_rejected_with_the_allowed_values():
    with pytest.raises(ValidationError) as caught:
        BusinessListQuery.model_validate({"category": "Cooking"})
    assert "Barber" in caught.value.errors()[0]["msg"]


def test_order_defaults_to_asc_and_accepts_any_case():
    assert BusinessListQuery.model_validate({}).order is SortOrder.ASC
    assert BusinessListQuery.model_validate({"order": " DESC "}).order is SortOrder.DESC


def test_unknown_order_is_rejected():
    with pytest.raises(ValidationError):
        BusinessListQuery.model_validate({"order": "sideways"})


@pytest.mark.django_db
def test_business_out_includes_owner_and_services(owner_user):
    business = make_business(owner=owner_user, name="Cut", category="Barber")
    service = make_service(business=business, name="Haircut", duration_minutes=30, price="45.00")
    assert BusinessOut.from_model(business).model_dump(mode="json") == {
        "id": business.id,
        "name": "Cut",
        "category": "Barber",
        "owner_id": owner_user.id,
        "owner_name": "Oscar Owner",
        "services": [{"id": service.id, "name": "Haircut", "duration_minutes": 30, "price": "45.00"}],
    }


def test_nul_byte_in_a_query_string_is_rejected():
    with pytest.raises(ValidationError):
        BusinessListQuery.model_validate({"search": "\x00abc"})
