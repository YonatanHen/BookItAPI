"""URL routes of API v1."""
from django.urls import path

from .views import (
    AppointmentListCreateView,
    ApiRootView,
    BusinessListView,
    BusinessSummaryView,
    LoginView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("businesses", BusinessListView.as_view(), name="business-list"),
    path("businesses/<int:business_id>/summary", BusinessSummaryView.as_view(), name="business-summary"),
    path("appointments", AppointmentListCreateView.as_view(), name="appointment-list"),
]
