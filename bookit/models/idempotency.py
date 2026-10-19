"""Stored request hashes that stop a user from creating the same appointment twice."""
from django.conf import settings
from django.db import models

from .appointment import Appointment


class IdempotencyRecord(models.Model):
    """One `hash → expires_at` entry guarding appointment creation; the unique key makes the claim atomic."""

    key = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="idempotency_records")
    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name="idempotency_record"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "idempotency_records"

    def __str__(self) -> str:
        """Return a short description of the record."""
        return f"{self.key[:12]}… until {self.expires_at:%Y-%m-%d %H:%M}"
