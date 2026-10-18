"""Base Pydantic classes shared by all API versions."""
from pydantic import BaseModel, ConfigDict


class RequestSchema(BaseModel):
    """JSON request body: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class QuerySchema(BaseModel):
    """Query string: unknown parameters are ignored and text is trimmed."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class ResponseSchema(BaseModel):
    """Response body built explicitly from domain objects."""

    model_config = ConfigDict(frozen=True)
