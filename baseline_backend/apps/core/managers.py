"""
Tenant-scoped manager and abstract base model.

Every tenant-scoped model in the codebase (Customer, Lead, Project, Task,
Invoice, Document, AuditLog, ...) inherits from TenantScopedModel instead of
models.Model directly. This is the ORM half of the two-layer isolation
described in the project context (Section 2/7): it injects a `tenant_id`
filter into every queryset automatically, sourced from the request-scoped
contextvar — never from client input. Postgres RLS (apps/core/db.py +
migration-level policies) is the backstop that catches anything that
bypasses this layer (raw SQL, the Django admin, a migration script, human
error in a one-off shell command).

Neither layer is sufficient alone. Do not treat this manager as "the" fix.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.core.context import get_current_tenant_id


class TenantScopedQuerySet(models.QuerySet):
    def unscoped(self):
        """Escape hatch for code paths that have already validated
        cross-tenant access is intentional and safe (platform_admin support
        tooling only). Named loudly and deliberately so it can't be reached
        for by accident or hidden inside an innocuous-looking helper."""
        return models.QuerySet(self.model, using=self._db)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):
    """Default manager for every tenant-scoped model.

    `Model.objects.all()` (and every other queryset entry point — `.filter()`,
    `.get()`, `.count()`, etc.) is automatically restricted to
    `tenant_id = get_current_tenant_id()`. Raises TenantContextError (via
    get_current_tenant_id) rather than silently returning an unscoped
    queryset if no tenant context is set — see apps/core/context.py.
    """

    def get_queryset(self):
        tenant_id = get_current_tenant_id()
        return super().get_queryset().filter(organization_id=tenant_id)

    def unscoped(self):
        """Override rather than inherit the `from_queryset`-generated proxy:
        that auto-generated version calls `self.get_queryset()` first (the
        tenant-filtered one) and only THEN calls `.unscoped()` on the
        result — which raises TenantContextError before it ever gets there
        if no tenant context is set. This builds a bare queryset directly,
        bypassing tenant filtering entirely, so it works with no context
        (the exact case it exists for: TenantContextMiddleware resolving
        Membership before any tenant is known, and platform_admin tooling).
        """
        return TenantScopedQuerySet(self.model, using=self._db)


class TenantScopedModel(models.Model):
    """Abstract base for every model that belongs to exactly one Organization.

    Fields:
        id: UUID primary key. UUIDs (not sequential integers) avoid leaking
            record-count/growth-rate information across tenants via
            enumerable IDs, and are safer to expose in URLs/APIs.
        organization: the tenant FK. Indexed — it's the first predicate in
            every query this manager issues.
        created_at / updated_at: standard audit timestamps. Kept here rather
            than duplicated per-model.

    `objects` is intentionally the ONLY manager. There is no
    `all_objects`/`unfiltered` manager on the class itself — cross-tenant
    access must go through `.objects.unscoped()` explicitly (see
    TenantScopedQuerySet.unscoped) so it's visible at every call site, not
    available as an easy-to-reach-for alternate manager name.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "core.Organization",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="%(app_label)s_%(class)s_set",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Defense in depth: if organization_id wasn't explicitly set, source
        # it from the current context rather than allowing a null/incorrect
        # value to reach the database. Explicit assignment (e.g. during
        # cross-org data migration under `.unscoped()`) always wins.
        if not self.organization_id:
            self.organization_id = get_current_tenant_id()
        super().save(*args, **kwargs)
