"""Pydantic request and response schemas for the auth endpoints."""
from typing import Literal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from pydantic import EmailStr, Field, field_validator

from bookit.api.common.schemas import RequestSchema, ResponseSchema
from bookit.models import User, UserRole


class RegisterRequest(RequestSchema):
    """Body of POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    full_name: str = Field(min_length=1, max_length=150)
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_meets_policy(cls, value: str) -> str:
        """Apply Django's configured password validators."""
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise ValueError(" ".join(exc.messages)) from exc
        return value

    @field_validator("full_name")
    @classmethod
    def full_name_is_not_blank(cls, value: str) -> str:
        """Reject names that contain only whitespace."""
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class LoginRequest(RequestSchema):
    """Body of POST /auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(RequestSchema):
    """Body of POST /auth/refresh."""

    refresh: str = Field(min_length=1)


class UserOut(ResponseSchema):
    """Public view of a user (never includes the password)."""

    id: int
    email: str
    full_name: str
    role: UserRole

    @classmethod
    def from_model(cls, user: User) -> "UserOut":
        """Build the response from a User."""
        return cls(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


class TokenPairOut(ResponseSchema):
    """Login response."""

    access: str
    refresh: str
    token_type: Literal["Bearer"] = "Bearer"


class AccessTokenOut(ResponseSchema):
    """Refresh response."""

    access: str
    token_type: Literal["Bearer"] = "Bearer"
