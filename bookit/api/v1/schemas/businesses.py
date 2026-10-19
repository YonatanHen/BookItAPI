"""Pydantic schemas for the business endpoints."""
from decimal import Decimal

from pydantic import Field

from bookit.api.common.pagination import PageParams
from bookit.api.common.schema_types import CaseInsensitiveCategory, CaseInsensitiveSortOrder, SortOrder
from bookit.api.common.schemas import ResponseSchema
from bookit.models import Business, BusinessCategory, Service
from bookit.services.business_service import BusinessSummary


class BusinessListQuery(PageParams):
    """Query parameters of GET /businesses."""

    category: CaseInsensitiveCategory | None = None
    search: str | None = Field(default=None, max_length=200)
    order: CaseInsensitiveSortOrder = SortOrder.ASC


class ServiceOut(ResponseSchema):
    """A bookable service inside a business item."""

    id: int
    name: str
    duration_minutes: int
    price: Decimal

    @classmethod
    def from_model(cls, service: Service) -> "ServiceOut":
        """Build the response from a Service."""
        return cls(id=service.id, name=service.name, duration_minutes=service.duration_minutes, price=service.price)


class BusinessOut(ResponseSchema):
    """One business with its owner name and services."""

    id: int
    name: str
    category: BusinessCategory
    owner_id: int
    owner_name: str
    services: list[ServiceOut]

    @classmethod
    def from_model(cls, business: Business) -> "BusinessOut":
        """Build the response; expects owner and services to be preloaded."""
        return cls(
            id=business.id,
            name=business.name,
            category=business.category,
            owner_id=business.owner_id,
            owner_name=business.owner.full_name,
            services=[ServiceOut.from_model(service) for service in business.services.all()],
        )


class ServiceSummaryOut(ResponseSchema):
    """Upcoming-appointment totals for one service."""

    service_id: int
    service_name: str
    price: Decimal
    duration_minutes: int
    upcoming_appointments: int
    expected_revenue: Decimal


class BusinessSummaryOut(ResponseSchema):
    """Owner summary of a business."""

    business_id: int
    business_name: str
    services: list[ServiceSummaryOut]

    @classmethod
    def from_model(cls, summary: BusinessSummary) -> "BusinessSummaryOut":
        """Build the response from the annotated services."""
        return cls(
            business_id=summary.business.id,
            business_name=summary.business.name,
            services=[
                ServiceSummaryOut(
                    service_id=service.id,
                    service_name=service.name,
                    price=service.price,
                    duration_minutes=service.duration_minutes,
                    upcoming_appointments=service.upcoming_appointments,
                    expected_revenue=service.expected_revenue,
                )
                for service in summary.services
            ],
        )
