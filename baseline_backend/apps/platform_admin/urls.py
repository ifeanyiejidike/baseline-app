from django.urls import path

from apps.platform_admin.views import (
    OrganizationDetailView,
    OrganizationSearchView,
    OrganizationSuspendView,
)

app_name = "platform_admin"

urlpatterns = [
    path("organizations/", OrganizationSearchView.as_view(), name="organization_search"),
    path("organizations/<uuid:organization_id>/", OrganizationDetailView.as_view(), name="organization_detail"),
    path(
        "organizations/<uuid:organization_id>/<str:action>/",
        OrganizationSuspendView.as_view(),
        name="organization_suspend_action",
    ),
]
