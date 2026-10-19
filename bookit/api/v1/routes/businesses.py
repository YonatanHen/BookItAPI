"""Business routes, mounted at /businesses."""
from django.urls import path

from ..views import BusinessListView, BusinessSummaryView

urlpatterns = [
    path("", BusinessListView.as_view(), name="business-list"),
    path("/<int:business_id>/summary", BusinessSummaryView.as_view(), name="business-summary"),
]
