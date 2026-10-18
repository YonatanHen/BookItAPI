"""Test-only routes that raise errors to exercise the full error-handling chain."""
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from bookit.services.exceptions import ConflictError


class _OpenView(APIView):
    """Base for test views that need no authentication."""

    authentication_classes: list = []
    permission_classes = [AllowAny]


class BoomView(_OpenView):
    """Raises an unexpected error."""

    def get(self, request):
        """Fail with an internal message that must never reach the client."""
        raise RuntimeError("secret internal detail")


class ConflictView(_OpenView):
    """Raises a domain conflict."""

    def get(self, request):
        """Fail with a domain conflict."""
        raise ConflictError("Slot taken.")


urlpatterns = [
    path("boom", BoomView.as_view()),
    path("conflict", ConflictView.as_view()),
]
