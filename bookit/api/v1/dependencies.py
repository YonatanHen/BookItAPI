"""Builds the service objects used by v1 views (one place to swap implementations)."""
from bookit.services.auth_service import AuthService
from bookit.services.business_service import BusinessService


def get_auth_service() -> AuthService:
    """Return the auth service."""
    return AuthService()


def get_business_service() -> BusinessService:
    """Return the business service."""
    return BusinessService()
