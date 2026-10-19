"""Management command: fill the database with reproducible sample data."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bookit.services.seed_service import SeedService


class Command(BaseCommand):
    """Seed ~10 users, 20 businesses, 50 services and 200 appointments."""

    help = "Seed the database with sample users, businesses, services and appointments."

    def add_arguments(self, parser):
        """Register --reset and --seed."""
        parser.add_argument("--reset", action="store_true", help="Delete existing data before seeding.")
        parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible data.")

    def handle(self, *args, reset: bool, seed: int, **options):
        """Run the seed service and print a summary."""
        if not settings.SEED_USER_PASSWORD:
            raise CommandError("SEED_USER_PASSWORD is not set. Add it to .env (see .env.example).")
        result = SeedService(password=settings.SEED_USER_PASSWORD, seed=seed).run(reset=reset)
        if result.skipped:
            self.stdout.write("Database already seeded; run with --reset to re-seed.")
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {result.users} users, {result.businesses} businesses, "
                f"{result.services} services, {result.appointments} appointments."
            )
        )
