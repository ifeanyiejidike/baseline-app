from django.contrib import admin

from apps.core.models import AuditLog, Invitation, Membership, Organization, Permission, RolePermission


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_suspended", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_suspended",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "status", "joined_at")
    list_filter = ("role", "status")
    search_fields = ("user__email", "organization__name")
    readonly_fields = ("id", "created_at", "updated_at")
    # Uses the default (unscoped) admin manager intentionally — platform
    # staff reviewing memberships across tenants is a legitimate cross-tenant
    # operation, gated by is_staff/is_superuser rather than TenantScopedManager.

    def get_queryset(self, request):
        return Membership.objects.unscoped()


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "resource", "action", "description")
    search_fields = ("codename", "resource", "action")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission")
    list_filter = ("role",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "expires_at")
    list_filter = ("role", "status")
    search_fields = ("email",)
    readonly_fields = ("id", "token", "created_at", "updated_at")

    def get_queryset(self, request):
        return Invitation.objects.unscoped()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "resource_type", "resource_id", "actor", "organization", "created_at")
    list_filter = ("resource_type", "action")
    search_fields = ("resource_id", "actor__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]  # fully read-only: append-only model

    def get_queryset(self, request):
        return AuditLog.objects.unscoped()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
