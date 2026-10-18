"""Mounts each supported API version under its own URL namespace."""
from django.urls import include, path

urlpatterns = [
    path("v1/", include(("bookit.api.v1.urls", "v1"), namespace="v1")),
]
