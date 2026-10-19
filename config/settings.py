"""Django settings for the BookIt API; values come from the environment and the local .env file."""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str | None = None) -> str:
    """Return an environment variable; a missing or empty one without a default is a configuration error."""
    value = os.environ.get(name) or default
    if not value:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}. Copy .env.example to .env.")
    return value


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "rest_framework",
    "django_ratelimit",
    "bookit",
]

AUTH_USER_MODEL = "bookit.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

MIDDLEWARE = [
    "bookit.middleware.correlation.CorrelationIdMiddleware",
    "bookit.middleware.request_logging.RequestLoggingMiddleware",
    "bookit.middleware.exception_handling.ExceptionHandlingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
APPEND_SLASH = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "bookit"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "EXCEPTION_HANDLER": "bookit.api.common.exception_handler.problem_details_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "SIGNING_KEY": SECRET_KEY,
}

# Docker sets REDIS_URL so all gunicorn workers share one rate-limit counter; local dev/tests use LocMem.
REDIS_URL = os.environ.get("REDIS_URL", "")
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
    if REDIS_URL
    else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}
# E003: LocMem is per process (fine for one dev process). W001: Django's built-in RedisCache is not on the library's list.
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]
LOGIN_RATE_LIMIT = env("LOGIN_RATE_LIMIT", "5/m")
# Higher than the IP limit: anyone who knows an email can use up its budget and lock the owner out.
LOGIN_EMAIL_RATE_LIMIT = env("LOGIN_EMAIL_RATE_LIMIT", "10/m")

IDEMPOTENCY_TTL_SECONDS = int(env("IDEMPOTENCY_TTL_SECONDS", "600"))
IDEMPOTENCY_PURGE_INTERVAL_SECONDS = int(env("IDEMPOTENCY_PURGE_INTERVAL_SECONDS", "300"))

# Only the seed command needs it; the command fails with a clear message when it is empty.
SEED_USER_PASSWORD = os.environ.get("SEED_USER_PASSWORD", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"correlation_id": {"()": "bookit.middleware.correlation.CorrelationIdFilter"}},
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default", "filters": ["correlation_id"]},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
