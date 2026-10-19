"""Management command: delete expired idempotency keys (for manual use or cron)."""
from django.core.management.base import BaseCommand

from bookit.services.idempotency_service import IdempotencyService


class Command(BaseCommand):
    """Bulk-delete idempotency keys whose TTL has passed."""

    help = "Delete expired idempotency keys."

    def handle(self, *args, **options):
        """Run the purge and print how many keys were removed."""
        deleted = IdempotencyService().purge_expired()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired idempotency key(s)."))
