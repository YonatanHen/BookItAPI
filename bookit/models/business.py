"""Business listed by an owner."""
from django.conf import settings
from django.db import models

from .enums import BusinessCategory


class Business(models.Model):
    """A business (barber, clinic, tutor...) owned by a BusinessOwner user."""

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=BusinessCategory.choices, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses")

    class Meta:
        db_table = "businesses"
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=BusinessCategory.values), name="businesses_category_valid"
            ),
        ]

    def __str__(self) -> str:
        """Return the business name."""
        return self.name
