"""Business endpoints."""
from rest_framework.response import Response
from rest_framework.views import APIView

from bookit.api.common.pagination import paginate
from bookit.api.common.parsing import parse_query
from bookit.api.common.schema_types import SortOrder

from ..dependencies import get_business_service
from ..schemas.businesses import BusinessListQuery, BusinessOut


class BusinessListView(APIView):
    """GET /businesses: paginated list filtered by category and name search, sorted by name."""

    def get(self, request):
        """Return one page of businesses with the total match count."""
        query = parse_query(BusinessListQuery, request)
        businesses = get_business_service().list_businesses(
            category=query.category, search=query.search, descending=query.order is SortOrder.DESC
        )
        return Response(paginate(businesses, query, request, BusinessOut).model_dump(mode="json"))
