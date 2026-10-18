"""Turns DRF request data into validated Pydantic models."""
from typing import TypeVar

from pydantic import BaseModel
from rest_framework.request import Request

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def parse_body(schema: type[SchemaT], request: Request) -> SchemaT:
    """Validate the JSON body; a Pydantic error becomes a 400 Problem Details response."""
    return schema.model_validate(request.data)


def parse_query(schema: type[SchemaT], request: Request) -> SchemaT:
    """Validate query parameters; for repeated keys the last value wins."""
    return schema.model_validate(request.query_params.dict())
