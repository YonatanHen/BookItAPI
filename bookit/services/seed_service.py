"""Reproducible random sample data for local development and the demo."""
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from faker import Faker

from bookit.models import Appointment, AppointmentStatus, Business, BusinessCategory, Service, User, UserRole

OWNER_COUNT, CLIENT_COUNT = 4, 6
BUSINESS_COUNT, APPOINTMENT_COUNT = 20, 200
SERVICES_BY_CATEGORY = {
    BusinessCategory.BARBER: ["Haircut", "Beard trim", "Hot towel shave"],
    BusinessCategory.BEAUTY: ["Manicure", "Facial", "Eyebrow shaping"],
    BusinessCategory.FITNESS: ["Personal training", "Group HIIT", "Mobility session"],
    BusinessCategory.MASSAGE: ["Swedish massage", "Deep tissue massage", "Foot reflexology"],
    BusinessCategory.PHYSIOTHERAPY: ["Initial assessment", "Sports rehab", "Back pain session"],
    BusinessCategory.TUTORING: ["Math lesson", "English lesson", "Exam preparation"],
}
NAME_SUFFIX = {
    BusinessCategory.BARBER: "Barbershop",
    BusinessCategory.BEAUTY: "Beauty Studio",
    BusinessCategory.FITNESS: "Fitness Club",
    BusinessCategory.MASSAGE: "Massage Spa",
    BusinessCategory.PHYSIOTHERAPY: "Physio Clinic",
    BusinessCategory.TUTORING: "Tutoring Center",
}


def seed_email(prefix: str, number: int) -> str:
    """Return the fixed login email of a seeded user, e.g. owner1@bookit.dev."""
    return f"{prefix}{number}@bookit.dev"


@dataclass(frozen=True)
class SeedResult:
    """How many rows the seed created; skipped=True when seed data already existed."""

    users: int = 0
    businesses: int = 0
    services: int = 0
    appointments: int = 0
    skipped: bool = False


class SeedService:
    """Creates owners, clients, businesses, services and non-overlapping appointments."""

    def __init__(self, *, password: str, seed: int = 42, clock: Callable[[], datetime] = timezone.now):
        """Inject the shared demo password, the random seed and the clock."""
        if not password:
            raise ValueError("A seed password is required (set SEED_USER_PASSWORD in .env).")
        self._password = password
        self._rng = random.Random(seed)
        self._faker = Faker()
        self._faker.seed_instance(seed)
        self._clock = clock

    def run(self, *, reset: bool = False) -> SeedResult:
        """Seed everything in one transaction; skip when seed users exist, unless reset is requested."""
        with transaction.atomic():
            if reset:
                User.objects.all().delete()
            elif User.objects.filter(email=seed_email("owner", 1)).exists():
                return SeedResult(skipped=True)
            owners = self._create_users(UserRole.BUSINESS_OWNER, "owner", OWNER_COUNT)
            clients = self._create_users(UserRole.CLIENT, "client", CLIENT_COUNT)
            businesses = self._create_businesses(owners)
            services = self._create_services(businesses)
            appointments = self._create_appointments(services, clients)
        return SeedResult(
            users=len(owners) + len(clients),
            businesses=len(businesses),
            services=len(services),
            appointments=len(appointments),
        )

    def _create_users(self, role: str, prefix: str, count: int) -> list[User]:
        """Create users that share one pre-hashed password (hashing once keeps seeding fast)."""
        password_hash = make_password(self._password)
        users = [
            User(email=seed_email(prefix, number), full_name=self._faker.name(), role=role, password=password_hash)
            for number in range(1, count + 1)
        ]
        return User.objects.bulk_create(users)

    def _create_businesses(self, owners: list[User]) -> list[Business]:
        """Create businesses spread evenly over owners and categories."""
        categories = list(BusinessCategory)
        businesses = []
        for index in range(BUSINESS_COUNT):
            category = categories[index % len(categories)]
            name = f"{self._faker.last_name()} {NAME_SUFFIX[category]}"
            businesses.append(Business(name=name, category=category, owner=owners[index % len(owners)]))
        return Business.objects.bulk_create(businesses)

    def _create_services(self, businesses: list[Business]) -> list[Service]:
        """Give the first half of the businesses 3 services and the rest 2 (50 in total)."""
        services = []
        for index, business in enumerate(businesses):
            count = 3 if index < len(businesses) // 2 else 2
            for name in SERVICES_BY_CATEGORY[business.category][:count]:
                services.append(
                    Service(
                        business=business,
                        name=name,
                        duration_minutes=self._rng.choice([30, 45, 60]),
                        price=Decimal(f"{self._rng.randrange(40, 400, 5)}.00"),
                    )
                )
        return Service.objects.bulk_create(services)

    def _create_appointments(self, services: list[Service], clients: list[User]) -> list[Appointment]:
        """Book hourly slots from -30 to +30 days; durations are at most 60 min, so slots never overlap."""
        now = self._clock()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        taken: set[tuple[int, datetime]] = set()
        appointments = []
        while len(appointments) < APPOINTMENT_COUNT:
            service = self._rng.choice(services)
            start = midnight + timedelta(days=self._rng.randint(-30, 30), hours=self._rng.randint(9, 17))
            if (service.id, start) in taken:
                continue
            taken.add((service.id, start))
            appointments.append(
                Appointment(
                    service=service,
                    client=self._rng.choice(clients),
                    start_time=start,
                    end_time=start + timedelta(minutes=service.duration_minutes),
                    status=self._status_for(start, now),
                )
            )
        return Appointment.objects.bulk_create(appointments)

    def _status_for(self, start: datetime, now: datetime) -> str:
        """Past slots are confirmed or cancelled; future slots may also still be pending."""
        if start < now:
            return self._rng.choices([AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED], weights=[4, 1])[0]
        return self._rng.choices(
            [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.CANCELLED], weights=[3, 5, 2]
        )[0]
