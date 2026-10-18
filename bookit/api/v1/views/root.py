"""Version discovery endpoint."""
from rest_framework.response import Response
from rest_framework.views import APIView


class ApiRootView(APIView):
    """GET /api/v1/: report the API version resolved for this request."""

    def get(self, request):
        """Return the active API version."""
        return Response({"version": request.version})
