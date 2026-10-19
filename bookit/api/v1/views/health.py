"""Health endpoint for container healthchecks."""
from django.db import DatabaseError, connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """GET /health: OK when the API runs and the database answers (no auth)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Return 200 OK when `SELECT 1` succeeds, else 503."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except DatabaseError:
            return Response({"status": "UNAVAILABLE"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "OK"})
