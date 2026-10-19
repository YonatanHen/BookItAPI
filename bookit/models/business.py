"""Business listed by an owner."""
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.db import models
from django.db.models.functions import Upper

from .enums import BusinessCategory


class Business(models.Model):
    """A business (barber, clinic, tutor...) owned by a BusinessOwner user."""

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=BusinessCategory.choices, db_index=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="businesses")

    class Meta:
        db_table = "businesses"
        ordering = ["name", "id"]
        indexes = [
            # Serves name__icontains (UPPER(name) LIKE '%x%'); a B-tree cannot serve a leading '%'.
            GinIndex(OpClass(Upper("name"), name="gin_trgm_ops"), name="businesses_name_trgm_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=BusinessCategory.values), name="businesses_category_valid"
            ),
        ]

    def __str__(self) -> str:
        """Return the business name."""
        return self.name
