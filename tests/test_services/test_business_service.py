import pytest

from bookit.models import BusinessCategory, UserRole
from bookit.services.business_service import BusinessService
from tests.factories import make_business, make_service, make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def businesses():
    return BusinessService()


def _names(queryset):
    return [business.name for business in queryset]


def test_list_returns_all_businesses_ordered_by_name(businesses, owner_user):
    for name in ["Zeta Spa", "Alpha Cuts", "Mid Clinic"]:
        make_business(owner=owner_user, name=name)
    assert _names(businesses.list_businesses()) == ["Alpha Cuts", "Mid Clinic", "Zeta Spa"]


def test_descending_reverses_the_name_order(businesses, owner_user):
    for name in ["Zeta Spa", "Alpha Cuts", "Mid Clinic"]:
        make_business(owner=owner_user, name=name)
    assert _names(businesses.list_businesses(descending=True)) == ["Zeta Spa", "Mid Clinic", "Alpha Cuts"]


def test_category_filter_matches_the_enum_value(businesses, owner_user):
    make_business(owner=owner_user, name="Cut", category=BusinessCategory.BARBER)
    make_business(owner=owner_user, name="Barberella", category=BusinessCategory.BEAUTY)
    make_business(owner=owner_user, name="Heal", category=BusinessCategory.PHYSIOTHERAPY)
    assert _names(businesses.list_businesses(category=BusinessCategory.BARBER)) == ["Cut"]


def test_search_matches_a_name_substring_in_any_case(businesses, owner_user):
    for name in ["Sharp Cuts", "Blunt", "CUTE Nails"]:
        make_business(owner=owner_user, name=name)
    assert _names(businesses.list_businesses(search="cut")) == ["CUTE Nails", "Sharp Cuts"]


def test_filters_combine(businesses, owner_user):
    make_business(owner=owner_user, name="Sharp Cuts", category=BusinessCategory.BARBER)
    make_business(owner=owner_user, name="Cut Clinic", category=BusinessCategory.PHYSIOTHERAPY)
    assert _names(businesses.list_businesses(category=BusinessCategory.BARBER, search="cut")) == ["Sharp Cuts"]


def test_missing_filters_are_ignored(businesses, owner_user):
    make_business(owner=owner_user, name="A")
    make_business(owner=owner_user, name="B")
    assert _names(businesses.list_businesses(category=None, search="")) == ["A", "B"]


def test_owner_and_services_load_in_two_queries(businesses, django_assert_num_queries):
    for _ in range(3):
        business = make_business(owner=make_user(role=UserRole.BUSINESS_OWNER))
        make_service(business=business)
        make_service(business=business)
    with django_assert_num_queries(2):
        rows = list(businesses.list_businesses())
        assert [len(row.services.all()) for row in rows] == [2, 2, 2]
        assert all(row.owner.full_name for row in rows)
