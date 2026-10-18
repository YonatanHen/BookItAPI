"""Appointment booked by a client for a service."""
from django.conf import settings
from django.db import models

from .enums import AppointmentStatus
from .service import Service


class Appointment(models.Model):
    """A booked time slot; end_time is stored to make overlap checks a range query."""

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="appointments")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "appointments"
        ordering = ["start_time", "id"]
        indexes = [
            models.Index(fields=["service", "start_time"], name="appt_service_start_idx"),
            models.Index(fields=["client", "start_time"], name="appt_client_start_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="appt_end_after_start"),
            models.CheckConstraint(condition=models.Q(status__in=AppointmentStatus.values), name="appt_status_valid"),
        ]

    def __str__(self) -> str:
        """Return a short description of the booking."""
        return f"{self.service_id}@{self.start_time:%Y-%m-%d %H:%M}"
