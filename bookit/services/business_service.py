"""Business queries: the filtered listing and the owner summary."""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, QuerySet, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from bookit.models import ACTIVE_APPOINTMENT_STATUSES, Business, BusinessCategory, Service, User

from .exceptions import NotFoundError, PermissionDeniedError


@dataclass(frozen=True)
class BusinessSummary:
    """A business with its services annotated with upcoming count and expected revenue."""

    business: Business
    services: list[Service]


class BusinessService:
    """Read-side business rules for businesses."""

    def __init__(self, clock: Callable[[], datetime] = timezone.now):
        """Inject the clock so time-based rules are testable."""
        self._clock = clock

    def list_businesses(
        self, *, category: BusinessCategory | None = None, search: str | None = None, descending: bool = False
    ) -> QuerySet[Business]:
        """Filter by category and name substring (any case), sorted by name; owner and services are preloaded."""
        businesses = Business.objects.select_related("owner").prefetch_related("services")
        if category:
            businesses = businesses.filter(category=category)
        if search:
            businesses = businesses.filter(name__icontains=search.strip())
        return businesses.order_by("-name", "-id") if descending else businesses.order_by("name", "id")

    def get_summary(self, *, user: User, business_id: int) -> BusinessSummary:
        """Aggregate upcoming active appointments per service in one SQL query (owner only)."""
        business = Business.objects.filter(pk=business_id).first()
        if business is None:
            raise NotFoundError("Business not found.")
        if business.owner_id != user.pk:
            raise PermissionDeniedError("Only the owner of this business can view its summary.")
        upcoming = Q(
            appointments__start_time__gt=self._clock(),
            appointments__status__in=ACTIVE_APPOINTMENT_STATUSES,
        )
        services = (
            Service.objects.filter(business=business)
            .annotate(
                upcoming_appointments=Count("appointments", filter=upcoming),
                expected_revenue=Coalesce(
                    Sum("price", filter=upcoming),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .order_by("name", "id")
        )
        return BusinessSummary(business=business, services=list(services))
