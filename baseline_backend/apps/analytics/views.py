from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import AnalyticsService
from apps.core.permissions import RequirePermission


class DashboardSummaryView(APIView):
    """GET /api/v1/analytics/dashboard/

    Gated by RBAC (unlike Notifications, which are inherently personal):
    pipeline/revenue figures are organization-sensitive, not something every
    role should see by default — a Viewer or Member arguably shouldn't see
    aggregate revenue. Uses the same `analytics:view` permission for the
    whole dashboard rather than per-widget grants; splitting this into
    per-section endpoints with separate permissions is a reasonable v2 if a
    concrete need for that granularity shows up.
    """

    permission_classes = [IsAuthenticated, RequirePermission("analytics:view")]

    def get(self, request):
        return Response(AnalyticsService.dashboard_summary())
