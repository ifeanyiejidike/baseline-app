from rest_framework.permissions import BasePermission


class IsPlatformStaff(BasePermission):
    """Gates platform_admin endpoints on Django's `is_staff`, never on a
    tenant Membership role. This is the structural isolation called for in
    project context Section 4 — a tenant Owner/Admin role grants zero
    platform_admin access, and is_staff grants zero tenant-resource access
    (platform_admin views query via `.unscoped()` explicitly instead of
    relying on TenantScopedManager)."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
