"""Booking and listing appointments."""
from collections.abc import Callable
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from bookit.models import ACTIVE_APPOINTMENT_STATUSES, Appointment, AppointmentStatus, Service, User, UserRole

from .exceptions import BusinessRuleError, ConflictError, PermissionDeniedError


class AppointmentService:
    """Business rules for creating and reading appointments."""

    def __init__(self, clock: Callable[[], datetime] = timezone.now):
        """Inject the clock so 'in the future' checks are testable."""
        self._clock = clock

    def book(self, *, client: User, service_id: int, start_time: datetime) -> Appointment:
        """Book a free slot for a client; the service row lock stops two parallel bookings of one slot."""
        if client.role != UserRole.CLIENT:
            raise PermissionDeniedError("Only clients can book appointments.")
        if start_time <= self._clock():
            raise BusinessRuleError("Appointment start time must be in the future.")
        with transaction.atomic():
            service = (
                Service.objects.select_for_update(of=("self",)).select_related("business").filter(pk=service_id).first()
            )
            if service is None:
                raise BusinessRuleError(f"Service {service_id} does not exist.")
            end_time = start_time + timedelta(minutes=service.duration_minutes)
            if self._overlaps(service, start_time, end_time):
                raise ConflictError("The requested time slot is already booked.")
            return Appointment.objects.create(
                service=service,
                client=client,
                start_time=start_time,
                end_time=end_time,
                status=AppointmentStatus.PENDING,
            )

    def list_for_user(
        self,
        *,
        user: User,
        start_from: datetime | None = None,
        start_to: datetime | None = None,
        status: str | None = None,
    ) -> QuerySet[Appointment]:
        """Return the caller's appointments (as client or as owner), filtered, with display relations preloaded."""
        appointments = Appointment.objects.select_related("service__business", "client")
        if user.role == UserRole.BUSINESS_OWNER:
            appointments = appointments.filter(service__business__owner=user)
        else:
            appointments = appointments.filter(client=user)
        if start_from is not None:
            appointments = appointments.filter(start_time__gte=start_from)
        if start_to is not None:
            appointments = appointments.filter(start_time__lte=start_to)
        if status is not None:
            appointments = appointments.filter(status=status)
        return appointments.order_by("start_time", "id")

    @staticmethod
    def _overlaps(service: Service, start_time: datetime, end_time: datetime) -> bool:
        """Return True when an active appointment of the service intersects [start_time, end_time)."""
        return Appointment.objects.filter(
            service=service,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).exists()
