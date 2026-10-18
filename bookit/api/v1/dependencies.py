"""Builds the service objects used by v1 views (one place to swap implementations)."""
from bookit.services.auth_service import AuthService


def get_auth_service() -> AuthService:
    """Return the auth service."""
    return AuthService()
