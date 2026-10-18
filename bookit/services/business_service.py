"""Business queries: the filtered listing and (Task 10) the owner summary."""
from collections.abc import Callable
from datetime import datetime

from django.db.models import QuerySet
from django.utils import timezone

from bookit.models import Business, BusinessCategory


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
