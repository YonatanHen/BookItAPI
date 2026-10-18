"""Reusable annotated Pydantic types for API schemas."""
from enum import Enum, StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator

from bookit.models import AppointmentStatus, BusinessCategory


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


CaseInsensitiveStatus = Annotated[AppointmentStatus, case_insensitive_enum(AppointmentStatus)]
CaseInsensitiveCategory = Annotated[BusinessCategory, case_insensitive_enum(BusinessCategory)]
CaseInsensitiveSortOrder = Annotated[SortOrder, case_insensitive_enum(SortOrder)]
