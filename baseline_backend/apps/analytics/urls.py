from django.urls import path

from apps.analytics.views import DashboardSummaryView

app_name = "analytics"

urlpatterns = [
    path("analytics/dashboard/", DashboardSummaryView.as_view(), name="dashboard_summary"),
]
