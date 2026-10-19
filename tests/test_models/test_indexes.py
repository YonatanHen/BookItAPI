import pytest
from django.db import connection

from bookit.services.business_service import BusinessService

pytestmark = pytest.mark.django_db


def _indexes(table):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)
    return {name: c for name, c in constraints.items() if c["index"] and not c["primary_key"]}


def test_business_name_has_a_trigram_gin_index():
    assert _indexes("businesses")["businesses_name_trgm_idx"]["type"] == "gin"


@pytest.mark.parametrize("column", ["service_id", "client_id"])
def test_appointment_fks_have_no_single_column_index(column):
    assert [c["columns"] for c in _indexes("appointments").values() if c["columns"] == [column]] == []


def test_composite_indexes_still_cover_the_fks():
    columns = [c["columns"] for c in _indexes("appointments").values()]
    assert ["service_id", "start_time"] in columns and ["client_id", "start_time"] in columns


def test_business_search_query_can_use_the_trigram_index():
    queryset = BusinessService().list_businesses(search="cut")
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")  # tiny test table: force the planner to show index use
        plan = queryset.explain()
    assert "businesses_name_trgm_idx" in plan
