"""Login rate limits built on django-ratelimit: per client IP and per email."""
import re

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

_RATE = re.compile(r"(\d+)/(\d*)([smhd])?")
_PERIOD_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
RATE_LIMITED_DETAIL = "Too many login attempts. Try again later."


def login_rate(group: str, request) -> str:
    """Read LOGIN_RATE_LIMIT per request, so tests and deployments can change it."""
    return settings.LOGIN_RATE_LIMIT


def login_email_rate(group: str, request) -> str:
    """Read LOGIN_EMAIL_RATE_LIMIT per request."""
    return settings.LOGIN_EMAIL_RATE_LIMIT


def login_email(group: str, request) -> str:
    """Rate-limit key: the trimmed, lower-cased email from the JSON body."""
    data = request.data
    return str(data.get("email", "")).strip().lower() if isinstance(data, dict) else ""


def rate_period_seconds(rate: str) -> int:
    """Return the window length of a rate such as '5/m' or '10/5m', used as Retry-After."""
    _, multiplier, period = _RATE.match(rate).groups()
    return _PERIOD_SECONDS[(period or "s").lower()] * int(multiplier or 1)


def login_retry_after() -> int:
    """Return the longest login window, so Retry-After is enough for either limit."""
    return max(rate_period_seconds(settings.LOGIN_RATE_LIMIT), rate_period_seconds(settings.LOGIN_EMAIL_RATE_LIMIT))


login_rate_limit = method_decorator(
    ratelimit(key="ip", rate=login_rate, method="POST", block=True), name="post"
)
login_email_rate_limit = method_decorator(
    ratelimit(key=login_email, rate=login_email_rate, method="POST", block=True), name="post"
)
