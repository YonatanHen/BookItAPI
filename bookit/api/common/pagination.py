"""Limit/offset pagination with a Pydantic page envelope."""
from typing import Generic, TypeVar

from django.db.models import QuerySet
from pydantic import BaseModel, Field
from rest_framework.request import Request

from .schemas import QuerySchema

ItemT = TypeVar("ItemT", bound=BaseModel)
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_OFFSET = 2**31 - 1  # far below Postgres bigint, so a huge offset is a 400, not a DB error


class PageParams(QuerySchema):
    """Shared `limit` and `offset` query parameters."""

    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0, le=MAX_OFFSET)


class Page(BaseModel, Generic[ItemT]):
    """Paginated response envelope with the total number of matching rows."""

    count: int
    limit: int
    offset: int
    next: str | None
    previous: str | None
    results: list[ItemT]


def paginate(queryset: QuerySet, params: PageParams, request: Request, item_schema: type[ItemT]) -> Page[ItemT]:
    """Return one page of the queryset; `item_schema.from_model` builds each result."""
    count = queryset.count()
    rows = queryset[params.offset : params.offset + params.limit]
    next_offset = params.offset + params.limit
    return Page[item_schema](
        count=count,
        limit=params.limit,
        offset=params.offset,
        next=_page_link(request, params.limit, next_offset) if next_offset < count else None,
        previous=_page_link(request, params.limit, max(params.offset - params.limit, 0)) if params.offset else None,
        results=[item_schema.from_model(row) for row in rows],
    )


def _page_link(request: Request, limit: int, offset: int) -> str:
    """Return the current absolute URL with `limit` and `offset` replaced."""
    query = request.query_params.copy()
    query["limit"], query["offset"] = str(limit), str(offset)
    return request.build_absolute_uri(f"{request.path}?{query.urlencode()}")
