"""URL routes of API v1: one included URLconf per resource."""
from django.urls import include, path

from .views import ApiRootView

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("auth/", include("bookit.api.v1.routes.auth")),
    path("businesses", include("bookit.api.v1.routes.businesses")),
    path("appointments", include("bookit.api.v1.routes.appointments")),
]
