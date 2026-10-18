"""Root URL configuration: everything lives under /api/<version>/."""
from django.urls import include, path

urlpatterns = [
    path("api/", include("bookit.api.urls")),
]

handler404 = "bookit.api.common.error_views.not_found"
handler500 = "bookit.api.common.error_views.server_error"
