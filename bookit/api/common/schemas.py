"""Base Pydantic classes shared by all API versions."""
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class _InputSchema(BaseModel):
    """Client input: text with a NUL byte is rejected, because PostgreSQL cannot store it."""

    @field_validator("*", mode="after")
    @classmethod
    def _reject_nul_bytes(cls, value: Any) -> Any:
        """Fail validation for any string field that contains a NUL byte."""
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("Text must not contain NUL bytes.")
        return value


class RequestSchema(_InputSchema):
    """JSON request body: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class QuerySchema(_InputSchema):
    """Query string: unknown parameters are ignored and text is trimmed."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ResponseSchema(BaseModel):
    """Response body built explicitly from domain objects."""

    model_config = ConfigDict(frozen=True)
