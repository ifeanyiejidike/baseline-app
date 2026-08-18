"""
Core platform models — the tenant boundary every other module depends on.

Organization is the tenant root. Every tenant-scoped model elsewhere in the
codebase (Customer, Lead, Project, Task, Invoice, Document) FKs to it via
TenantScopedModel (apps/core/managers.py). Membership, Role/Permission,
Invitation, and AuditLog live here because they ARE the tenant-boundary
machinery, not because they're arbitrarily grouped with it.

Organization and AuditLog are the only models here with non-standard
managers: Organization IS the tenant (it can't be scoped to itself, so it
uses the default Django manager), and AuditLog uses TenantScopedManager but
blocks .update()/.delete() at the ORM layer for defense in depth on top of
the append-only DB permission grant applied in the RLS migration.
"""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.managers import TenantScopedManager, TenantScopedModel, TenantScopedQuerySet


class Organization(models.Model):
    """The tenant root. Every other tenant-scoped record traces back to one
    of these via `organization_id`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    is_suspended = models.BooleanField(
        default=False,
        help_text="Hard kill-switch independent of billing status — e.g. for "
        "abuse/ToS enforcement. Checked in TenantContextMiddleware on every "
        "request.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_organization"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(TenantScopedModel):
    """User <-> Organization, many-to-many through this model.

    Roles are per-organization (a user can be Owner in one org and Viewer in
    another), which is why role lives here rather than on User directly.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"], name="uniq_membership_org_user"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "user", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"

    def activate(self) -> None:
        self.status = self.Status.ACTIVE
        self.joined_at = timezone.now()
        self.save(update_fields=["status", "joined_at", "updated_at"])

    def is_last_owner(self) -> bool:
        """Guards the 'last Owner attempting to leave an org' edge case
        flagged in the project context (Section 4 known edge cases)."""
        return (
            self.role == self.Role.OWNER
            and Membership.objects.filter(
                organization=self.organization, role=self.Role.OWNER, status=self.Status.ACTIVE
            ).count()
            <= 1
        )


class Permission(models.Model):
    """A single resource:action pair, e.g. `invoices:create`, `customers:delete`.

    Global (not tenant-scoped) — the catalog of possible permissions is the
    same across every tenant. What varies is which Roles grant which
    Permissions, captured in RolePermission below, seeded identically per
    role at migration time rather than customized per-tenant, since
    per-tenant custom RBAC was not something the project scoped. If
    per-tenant custom roles become a requirement later, RolePermission is
    where that would need to become tenant-scoped.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    codename = models.CharField(max_length=160, unique=True, editable=False)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "core_permission"
        constraints = [
            models.UniqueConstraint(fields=["resource", "action"], name="uniq_permission_resource_action")
        ]

    def save(self, *args, **kwargs):
        self.codename = f"{self.resource}:{self.action}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.codename


class RolePermission(models.Model):
    """Which Permissions a given Role grants. Seeded at migration time, not
    edited via the application at runtime in v1 (see Permission docstring)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Membership.Role.choices)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_grants")

    class Meta:
        db_table = "core_role_permission"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uniq_role_permission")
        ]

    def __str__(self) -> str:
        return f"{self.role} -> {self.permission.codename}"


def _generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def _default_invitation_expiry():
    return timezone.now() + timedelta(days=settings.INVITATION_TOKEN_TTL_DAYS)


class Invitation(TenantScopedModel):
    """A pending invite for an email address to join an Organization at a
    given Role. Token is signed/random (not a bare sequential UUID) with a
    confirmed 7-day expiry per project context Section 4."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    email = models.EmailField()
    role = models.CharField(max_length=20, choices=Membership.Role.choices, default=Membership.Role.MEMBER)
    token = models.CharField(max_length=64, unique=True, default=_generate_invitation_token, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_invitations"
    )
    expires_at = models.DateTimeField(default=_default_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_invitation"
        indexes = [models.Index(fields=["organization", "email", "status"])]

    def __str__(self) -> str:
        return f"Invite<{self.email} -> {self.organization}, {self.status}>"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class AuditLogQuerySet(TenantScopedQuerySet):
    def update(self, *args, **kwargs):
        raise NotImplementedError(
            "AuditLog is append-only. This is enforced at the ORM layer here "
            "AND at the database layer (REVOKE UPDATE, DELETE granted in the "
            "RLS migration) — do not add an update path for this model."
        )

    def delete(self, *args, **kwargs):
        raise NotImplementedError("AuditLog is append-only; see update().")


class AuditLogManager(TenantScopedManager.from_queryset(AuditLogQuerySet)):
    pass


class AuditLog(TenantScopedModel):
    """Append-only record of every meaningful mutation in the system.
    Written exclusively through `apps.core.audit.record()`, never
    `.objects.create()` directly from view/service code — see that module's
    docstring. Explicitly prioritized for day-one build per project context
    Section 4 (mid-market buyers raise it during procurement evaluation).
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_log_entries",
    )
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=64, db_index=True)
    diff = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    objects = AuditLogManager()

    class Meta:
        db_table = "core_audit_log"
        indexes = [
            models.Index(fields=["organization", "resource_type", "resource_id"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.resource_type}:{self.resource_id}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise NotImplementedError("AuditLog rows are immutable once created.")
        super().save(*args, **kwargs)
