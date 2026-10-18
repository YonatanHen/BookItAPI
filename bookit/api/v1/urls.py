"""URL routes of API v1."""
from django.urls import path

from .views import ApiRootView, BusinessListView, LoginView, RefreshView, RegisterView

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("businesses", BusinessListView.as_view(), name="business-list"),
]
