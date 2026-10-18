"""Plain factory helpers that build valid test data."""
import itertools
from datetime import datetime, timedelta
from decimal import Decimal

from bookit.models import Appointment, AppointmentStatus, Business, BusinessCategory, Service, User, UserRole

DEFAULT_PASSWORD = "Str0ng-Passw0rd!"
_sequence = itertools.count(1)


def make_user(
    *,
    role: str = UserRole.CLIENT,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Test User",
) -> User:
    """Create a user with a unique email."""
    return User.objects.create_user(
        email=email or f"user{next(_sequence)}@bookit-test.io",
        password=password,
        full_name=full_name,
        role=role,
    )


def make_business(
    *, owner: User, name: str | None = None, category: str = BusinessCategory.BARBER
) -> Business:
    """Create a business owned by the given user."""
    return Business.objects.create(owner=owner, name=name or f"Business {next(_sequence)}", category=category)


def make_service(
    *, business: Business, name: str | None = None, duration_minutes: int = 60, price: str = "100.00"
) -> Service:
    """Create a service for the given business."""
    return Service.objects.create(
        business=business,
        name=name or f"Service {next(_sequence)}",
        duration_minutes=duration_minutes,
        price=Decimal(price),
    )


def make_appointment(
    *, service: Service, client: User, start_time: datetime, status: str = AppointmentStatus.PENDING
) -> Appointment:
    """Create an appointment whose end time follows the service duration."""
    return Appointment.objects.create(
        service=service,
        client=client,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=service.duration_minutes),
        status=status,
    )
