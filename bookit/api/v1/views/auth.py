"""Authentication endpoints: register, login and refresh."""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from bookit.api.common.parsing import parse_body

from ..dependencies import get_auth_service
from ..schemas.auth import AccessTokenOut, LoginRequest, RefreshRequest, RegisterRequest, TokenPairOut, UserOut


class PublicView(APIView):
    """Base for endpoints that must work without a token."""

    authentication_classes: list = []
    permission_classes = [AllowAny]


class RegisterView(PublicView):
    """POST /auth/register: create a Client or BusinessOwner account."""

    def post(self, request):
        """Validate the body and create the user."""
        payload = parse_body(RegisterRequest, request)
        user = get_auth_service().register(
            email=payload.email, password=payload.password, full_name=payload.full_name, role=payload.role
        )
        return Response(UserOut.from_model(user).model_dump(mode="json"), status=status.HTTP_201_CREATED)


class LoginView(PublicView):
    """POST /auth/login: exchange credentials for an access and a refresh token."""

    def post(self, request):
        """Validate the credentials and return a token pair."""
        payload = parse_body(LoginRequest, request)
        tokens = get_auth_service().login(email=payload.email, password=payload.password)
        return Response(TokenPairOut(access=tokens.access, refresh=tokens.refresh).model_dump(mode="json"))


class RefreshView(PublicView):
    """POST /auth/refresh: get a new access token while the refresh token is valid."""

    def post(self, request):
        """Return a new access token."""
        payload = parse_body(RefreshRequest, request)
        access = get_auth_service().refresh(payload.refresh)
        return Response(AccessTokenOut(access=access).model_dump(mode="json"))
