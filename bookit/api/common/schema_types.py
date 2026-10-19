"""Reusable annotated Pydantic types for API schemas."""
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator, PlainSerializer

from bookit.models import AppointmentStatus, BusinessCategory

_TIMESTAMP_ERROR = "must be a unix timestamp in seconds"


class SortOrder(StrEnum):
    """Sort direction of a list endpoint."""

    ASC = "asc"
    DESC = "desc"


def case_insensitive_enum(enum_cls: type[Enum]) -> BeforeValidator:
    """Return a validator that maps a value to the enum member, ignoring case and surrounding spaces."""

    def _match(value: Any) -> Any:
        """Return the matching member, or the raw value so Pydantic reports the allowed values."""
        if isinstance(value, str):
            for member in enum_cls:
                if member.value.lower() == value.strip().lower():
                    return member
        return value

    return BeforeValidator(_match)


def _to_utc_datetime(value: Any) -> datetime:
    """Accept integer seconds (int or digit string) and return an aware UTC datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(_TIMESTAMP_ERROR)
    if isinstance(value, str) and not value.strip().isdigit():
        raise ValueError(_TIMESTAMP_ERROR)
    if int(value) <= 0:
        raise ValueError("unix timestamp must be positive")
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("unix timestamp is out of range") from exc


def _to_unix_seconds(value: datetime) -> int:
    """Serialize a datetime as integer unix seconds."""
    return int(value.timestamp())


UnixTimestamp = Annotated[
    datetime, BeforeValidator(_to_utc_datetime), PlainSerializer(_to_unix_seconds, return_type=int)
]
CaseInsensitiveStatus = Annotated[AppointmentStatus, case_insensitive_enum(AppointmentStatus)]
CaseInsensitiveCategory = Annotated[BusinessCategory, case_insensitive_enum(BusinessCategory)]
CaseInsensitiveSortOrder = Annotated[SortOrder, case_insensitive_enum(SortOrder)]
