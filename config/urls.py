"""Root URL configuration: everything lives under /api/<version>/."""
from django.urls import include, path

urlpatterns = [
    path("api/", include("bookit.api.urls")),
]
