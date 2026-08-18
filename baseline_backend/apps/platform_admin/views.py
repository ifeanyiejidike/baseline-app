from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Membership, Organization
from apps.platform_admin.permissions import IsPlatformStaff
from apps.platform_admin.serializers import OrganizationAdminSerializer


class OrganizationSearchView(APIView):
    """GET /api/v1/platform-admin/organizations/?q=<name-or-slug>

    Deliberately uses `Organization.objects` directly (not a tenant-scoped
    model, so there's nothing to unscope) but every OTHER model this
    touches must go through `.unscoped()` explicitly — see
    OrganizationDetailView below for the pattern.
    """

    permission_classes = [IsAuthenticated, IsPlatformStaff]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        queryset = Organization.objects.all()
        if query:
            queryset = queryset.filter(name__icontains=query) | queryset.filter(slug__icontains=query)
        return Response(OrganizationAdminSerializer(queryset[:50], many=True).data)


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformStaff]

    def get(self, request, organization_id):
        organization = Organization.objects.filter(id=organization_id).first()
        if organization is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        member_count = Membership.objects.unscoped().filter(
            organization_id=organization_id, status=Membership.Status.ACTIVE
        ).count()

        data = OrganizationAdminSerializer(organization).data
        data["active_member_count"] = member_count
        return Response(data)


class OrganizationSuspendView(APIView):
    """POST /api/v1/platform-admin/organizations/{id}/suspend/
    POST /api/v1/platform-admin/organizations/{id}/unsuspend/

    Flips Organization.is_suspended, which TenantContextMiddleware checks on
    every tenant-facing request — this is the hard kill-switch referenced
    in core.models.Organization's docstring.
    """

    permission_classes = [IsAuthenticated, IsPlatformStaff]

    def post(self, request, organization_id, action):
        from apps.core.audit import record as audit_record

        organization = Organization.objects.filter(id=organization_id).first()
        if organization is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if action not in ("suspend", "unsuspend"):
            return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        organization.is_suspended = action == "suspend"
        organization.save(update_fields=["is_suspended", "updated_at"])

        # Audit logging normally requires tenant context (AuditLog is
        # tenant-scoped); a platform-staff action against a tenant is
        # exactly the case apps.core.db.tenant_scoped_connection exists for.
        from apps.core.db import tenant_scoped_connection

        with tenant_scoped_connection(organization.id):
            audit_record(
                action=f"organization.{action}ed",
                resource_type="Organization",
                resource_id=organization.id,
            )

        return Response(OrganizationAdminSerializer(organization).data)
