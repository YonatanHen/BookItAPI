"""User registration, login and JWT issuing."""
from dataclasses import dataclass

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from bookit.models import User

from .exceptions import ConflictError, InvalidCredentialsError

DUPLICATE_EMAIL = "A user with this email already exists."


@dataclass(frozen=True)
class TokenPair:
    """Access and refresh JWTs returned after login."""

    access: str
    refresh: str


class AuthService:
    """Registers users and issues JWTs that carry the user id and role claims."""

    def register(self, *, email: str, password: str, full_name: str, role: str) -> User:
        """Create a user; raise ConflictError when the email is already registered (any case)."""
        normalized = email.strip().lower()
        if User.objects.filter(email=normalized).exists():
            raise ConflictError(DUPLICATE_EMAIL)
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=normalized, password=password, full_name=full_name.strip(), role=role
                )
        except IntegrityError as exc:
            raise ConflictError(DUPLICATE_EMAIL) from exc

    def login(self, *, email: str, password: str) -> TokenPair:
        """Check the credentials and return a new token pair."""
        user = authenticate(email=email.strip().lower(), password=password)
        if user is None:
            raise InvalidCredentialsError("Invalid email or password.")
        return self.issue_tokens(user)

    def refresh(self, refresh_token: str) -> str:
        """Return a new access token; the refresh token is never extended, so expiry forces a new login."""
        try:
            return str(RefreshToken(refresh_token).access_token)
        except TokenError as exc:
            raise InvalidCredentialsError("Refresh token is invalid or expired.") from exc

    def issue_tokens(self, user: User) -> TokenPair:
        """Create a refresh token with a role claim; its access token copies the claims."""
        refresh = RefreshToken.for_user(user)
        refresh["role"] = str(user.role)
        return TokenPair(access=str(refresh.access_token), refresh=str(refresh))
