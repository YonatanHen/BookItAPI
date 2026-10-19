"""Short-lived request hashes that reject a duplicate appointment (in theory, a double charge)."""
from collections.abc import Callable
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from bookit.models import IdempotencyRecord, User


class IdempotencyService:
    """Claims request hashes with a TTL; purges expired ones at most once per interval per process."""

    _last_purge_at: datetime | None = None

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = timezone.now,
        ttl_seconds: int | None = None,
        purge_interval_seconds: int | None = None,
    ):
        """Inject the clock and timings; defaults come from Django settings."""
        self._clock = clock
        self._ttl = timedelta(seconds=settings.IDEMPOTENCY_TTL_SECONDS if ttl_seconds is None else ttl_seconds)
        self._purge_interval = timedelta(
            seconds=settings.IDEMPOTENCY_PURGE_INTERVAL_SECONDS
            if purge_interval_seconds is None
            else purge_interval_seconds
        )

    def claim(self, *, key: str, user: User) -> IdempotencyRecord | None:
        """Store the key and return its record, or None when an unexpired duplicate exists."""
        now = self._clock()
        self._purge_if_due(now)
        IdempotencyRecord.objects.filter(key=key, expires_at__lte=now).delete()
        try:
            with transaction.atomic():
                return IdempotencyRecord.objects.create(key=key, user=user, expires_at=now + self._ttl)
        except IntegrityError:
            return None

    def complete(self, record: IdempotencyRecord, *, appointment_id: int | None) -> None:
        """Link the key to the appointment the request created."""
        if appointment_id is not None:
            IdempotencyRecord.objects.filter(pk=record.pk).update(appointment_id=appointment_id)

    def release(self, record: IdempotencyRecord) -> None:
        """Delete the key so a corrected retry is processed normally."""
        IdempotencyRecord.objects.filter(pk=record.pk).delete()

    def purge_expired(self) -> int:
        """Delete every expired key and return how many were removed."""
        return self._delete_expired(self._clock())

    def _purge_if_due(self, now: datetime) -> None:
        """Purge expired keys when this process has not purged within the interval."""
        last = IdempotencyService._last_purge_at
        if last is None or now - last >= self._purge_interval:
            IdempotencyService._last_purge_at = now
            self._delete_expired(now)

    @staticmethod
    def _delete_expired(now: datetime) -> int:
        """Delete keys whose TTL has passed."""
        deleted, _ = IdempotencyRecord.objects.filter(expires_at__lte=now).delete()
        return deleted
