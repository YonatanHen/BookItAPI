"""Bookable service offered by a business."""
from django.db import models

from .business import Business


class Service(models.Model):
    """A service with a fixed duration and price."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=200)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "services"
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0), name="services_duration_positive"),
            models.CheckConstraint(condition=models.Q(price__gte=0), name="services_price_non_negative"),
        ]

    def __str__(self) -> str:
        """Return the service name."""
        return self.name
