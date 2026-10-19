"""DRF handler decorator that rejects a repeated create request (same user + same payload) within the TTL."""
import functools
import hashlib
import json

from bookit.services.exceptions import ConflictError
from bookit.services.idempotency_service import IdempotencyService

CLIENT_KEY_HEADER = "Idempotency-Key"
DUPLICATE_DETAIL = "Duplicate booking request. The same booking was already submitted."


def build_idempotency_key(user_id: int, request) -> str:
    """Hash user, method, path and the Idempotency-Key header, or the canonical JSON body if no header."""
    material = request.headers.get(CLIENT_KEY_HEADER, "").strip() or _canonical_body(request.body)
    raw = f"{user_id}:{request.method}:{request.path}:{material}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def idempotent(handler):
    """Claim the request hash before the handler; link it on success, release it on any failure."""

    @functools.wraps(handler)
    def wrapper(view, request, *args, **kwargs):
        """Run the handler once per unique request; a duplicate within the TTL raises a 409 conflict."""
        service = IdempotencyService()
        record = service.claim(key=build_idempotency_key(request.user.pk, request), user=request.user)
        if record is None:
            raise ConflictError(DUPLICATE_DETAIL)
        try:
            response = handler(view, request, *args, **kwargs)
        except Exception:
            service.release(record)
            raise
        if 200 <= response.status_code < 300:
            service.complete(record, appointment_id=response.data.get("id"))
        else:
            service.release(record)
        return response

    return wrapper


def _canonical_body(body: bytes) -> str:
    """Serialize JSON with sorted keys so key order and spacing do not change the hash."""
    try:
        return json.dumps(json.loads(body or b"null"), sort_keys=True, separators=(",", ":"))
    except ValueError:
        return body.decode("utf-8", errors="replace")
